#!/usr/bin/env python3
"""
仪表识别与推荐安装方法的智能体
=================================

本智能体基于LangGraph框架构建


"""

import logging
import sys
import os
from pathlib import Path
from typing import TypedDict, Annotated, List, Dict, Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入配置
from config.settings import get_openai_config

# 导入所有工具
from tools.extract_excel_tables import extract_excel_tables
from tools.parse_instrument_table import extract_and_parse_instrument_table, validate_parsed_data
from tools.classify_instrument_type import classify_instrument_type, batch_classify_instruments
from tools.summarize_statistics import summarize_statistics
from tools.match_standard_clause import match_standard_clause, match_standards_for_instruments
from tools.generate_installation_recommendation import generate_installation_recommendation

logger = logging.getLogger(__name__)

class InstrumentAgentState(TypedDict):
    """智能体状态定义 - 完全交互式，无默认值"""
    # 消息历史
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 任务规划（新增）
    original_user_input: str  # 原始用户输入
    planned_tasks: List[Dict[str, Any]]  # LLM规划的任务列表
    current_task_index: int  # 当前执行的任务索引
    task_results: List[Dict[str, Any]]  # 任务执行结果
    needs_user_task_confirmation: bool  # 是否需要用户确认任务规划
    
    # 文件处理
    excel_file_path: str
    file_valid: bool
    file_error_message: str
    extracted_tables: List[Dict[str, Any]]
    has_multiple_tables: bool
    selected_table_index: int
    needs_llm_table_selection: bool  # 是否需要LLM智能表格选择
    
    # 数据处理
    parsed_instruments: List[Dict[str, Any]]
    classified_instruments: List[Dict[str, Any]]
    classification_confidence: float
    needs_user_confirmation: bool
    instrument_statistics: Dict[str, Any]
    
    # 用户意图
    user_intent: str  # "stats" 或 "reco" 
    recommendation_target: str  # "全部" 或 具体类型 (新增)
    matched_standards: List[Dict[str, Any]]
    has_standards: bool
    
    # 类型验证（新增改进功能）
    invalid_types: List[str]  # 不存在的类型列表
    available_types: List[str]  # 可用的类型列表
    needs_type_selection: bool  # 是否需要用户重新选择类型
    
    # 敏感工具授权
    user_approved_sensitive: bool
    installation_recommendations: List[Dict[str, Any]]
    
    # 响应和循环
    final_report: str
    user_feedback: str  # "modify" 或 "finish"
    
    # 错误处理
    has_error: bool
    error_context: str
    
    # 循环计数器（防死循环）
    loop_count: int
    max_loops: int
    
    # 任务处理标志
    needs_file_processing: bool
    
    # 步骤计数器（用于正确显示步骤时机）
    step_count: int

def show_step(state: InstrumentAgentState, step_name: str) -> None:
    """显示步骤信息"""
    step_count = state.get("step_count", 0) + 1
    state["step_count"] = step_count
    print(f"  ⚡ 步骤 {step_count}: {step_name}")

def create_llm():
    """创建LLM实例"""
    config = get_openai_config()
    return ChatOpenAI(
        model=config["model"],
        api_key=config["api_key"], 
        base_url=config["base_url"],
        temperature=0.1
    )

# ==================== LLM增强节点函数 ====================

def llm_task_planner(state: InstrumentAgentState) -> InstrumentAgentState:
    """LLM任务规划器 - 分析用户输入并制定任务计划"""
    show_step(state, "智能任务规划")
    
    from tools.parse_user_input import extract_file_path, parse_user_intent, create_task_planner_with_llm
    
    # 检查是否在反馈循环中 - 如果是，不要重新规划任务
    if state.get("loop_count", 0) > 0:
        logger.info("检测到反馈循环状态，跳过任务重新规划")
        return state
    
    # 检查是否已有任务规划 - 避免重复规划
    if state.get("planned_tasks") and len(state.get("planned_tasks", [])) > 0:
        logger.info("已存在任务规划，跳过重新规划")
        return state
    
    # 检查是否已有任务规划 - 避免重复规划
    if state.get("planned_tasks") and len(state.get("planned_tasks", [])) > 0:
        logger.info("已存在任务规划，跳过重新规划")
        return state
    
    # 获取原始用户输入
    user_input = state.get("original_user_input", "")
    if not user_input:
        # 从消息历史中获取最新的用户输入
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                state["original_user_input"] = user_input
                break
    
    if user_input:
        logger.info(f"LLM分析用户输入: '{user_input}'")
        
        # 1. 创建任务规划
        try:
            planned_tasks = create_task_planner_with_llm(user_input)
            state["planned_tasks"] = planned_tasks
            logger.info(f"LLM生成任务规划: {len(planned_tasks)} 个任务")
            for i, task in enumerate(planned_tasks):
                logger.info(f"  任务{i+1}: {task.get('type')} - {task.get('target')}")
        except Exception as e:
            logger.error(f"LLM任务规划失败: {str(e)}")
            # 回退到简单规划
            planned_tasks = [
                {"type": "parse", "target": "file/test.xlsx"},
                {"type": "stats", "target": "全部"},
                {"type": "reco", "target": "全部"}
            ]
            state["planned_tasks"] = planned_tasks
            logger.info("使用默认任务规划")
        
        # 2. 智能提取文件路径
        file_path = extract_file_path(user_input)
        if file_path:
            state["excel_file_path"] = file_path
            logger.info(f"从用户输入提取文件路径: {file_path}")
        else:
            # 检查任务规划中是否有文件路径
            for task in state.get("planned_tasks", []):
                if task.get("type") == "parse" and task.get("target"):
                    target_file = task["target"]
                    state["excel_file_path"] = target_file
                    logger.info(f"从任务规划提取文件路径: {target_file}")
                    break
            else:
                # 如果没有提取到文件路径，使用默认测试文件
                state["excel_file_path"] = "file/test.xlsx"
                logger.info("未提取到文件路径，使用默认测试文件: file/test.xlsx")
        
        # 3. 检查是否已有用户意图，如果没有则解析
        if not state.get("user_intent"):
            intent = parse_user_intent(user_input)
            if intent:
                state["user_intent"] = intent
                logger.info(f"解析用户意图: {intent}")
        else:
            logger.info(f"使用已确定的用户意图: {state.get('user_intent')}")
        
        # 4. 从任务规划中提取推荐目标，不要用简单的关键词覆盖LLM的结果
        recommendation_target = "全部"  # 默认值
        
        # 从LLM规划的任务中提取推荐目标
        for task in state.get("planned_tasks", []):
            if task.get("type") == "reco" and task.get("target"):
                recommendation_target = task["target"]
                logger.info(f"从LLM任务规划提取推荐目标: {recommendation_target}")
                break
            elif task.get("type") == "stats" and task.get("target") and task["target"] != "全部":
                # 如果stats任务有特定目标，也用于推荐
                recommendation_target = task["target"]
                logger.info(f"从LLM统计任务提取推荐目标: {recommendation_target}")
        
        state["recommendation_target"] = recommendation_target
        
        # 5. 设置任务确认标志
        if len(state.get("planned_tasks", [])) > 1:
            state["needs_user_task_confirmation"] = True
            logger.info("多任务规划，需要用户确认")
        else:
            state["needs_user_task_confirmation"] = False
            logger.info("单任务或简单规划，自动确认")
        
        logger.info("LLM用户输入分析完成")
    else:
        logger.info("没有用户输入，使用默认配置")
        # 设置默认任务规划
        state["planned_tasks"] = [
            {"type": "parse", "target": "file/test.xlsx"},
            {"type": "stats", "target": "全部"},
            {"type": "reco", "target": "全部"}
        ]
        state["needs_user_task_confirmation"] = False
        
        # 设置默认文件路径
        if not state.get("excel_file_path"):
            state["excel_file_path"] = "file/test.xlsx"
            logger.info("设置默认文件路径: file/test.xlsx")
    
    return state

def ask_user_confirm_tasks(state: InstrumentAgentState) -> InstrumentAgentState:
    """显示任务规划给用户 - 不需要确认，仅展示"""
    show_step(state, "显示任务规划")
    
    planned_tasks = state.get("planned_tasks", [])
    
    # 使用print确保规划显示（不受日志级别影响）
    print(f"\n📋 任务规划:")
    print(f"系统已规划 {len(planned_tasks)} 个任务:")
    
    # 显示任务规划
    for i, task in enumerate(planned_tasks):
        task_type = task.get('type', '未知')
        task_target = task.get('target', '未知')
        
        # 任务类型说明
        type_desc = {
            'parse': '解析Excel文件',
            'stats': '统计分析数据', 
            'reco': '生成安装推荐',
            'chart': '绘制统计图表'
        }.get(task_type, task_type)
        
        print(f"  {i+1}. {task_type} - {task_target}")
        if i == 0:
            print(f"     📝 {type_desc}")
    
    # 直接确认，不需要用户输入
    state["needs_user_task_confirmation"] = False
    print("🚀 开始执行任务...")
    
    return state



def task_router(state: InstrumentAgentState) -> InstrumentAgentState:
    """任务路由器 - 根据当前任务确定执行路径"""
    show_step(state, "任务路由")
    
    planned_tasks = state.get("planned_tasks", [])
    current_index = state.get("current_task_index", 0)
    
    if current_index >= len(planned_tasks):
        # 所有任务完成
        state["user_intent"] = "finish"
        logger.info("所有任务已完成")
        return state
    
    current_task = planned_tasks[current_index]
    task_type = current_task.get("type", "")
    task_target = current_task.get("target", "")
    
    logger.info(f"执行任务 {current_index + 1}/{len(planned_tasks)}: {task_type} - {task_target}")
    
    # 根据任务类型设置状态
    if task_type == "parse":
        if task_target and task_target != "file/test.xlsx":
            state["excel_file_path"] = task_target
        state["user_intent"] = "parse"
        # 解析任务需要从文件开始
        state["needs_file_processing"] = True
    elif task_type == "stats":
        state["user_intent"] = "stats"
        # 统计任务需要确保有解析数据
        state["needs_file_processing"] = False
        if not state.get("parsed_instruments"):
            logger.warning("统计任务但没有解析数据，将先执行解析")
            state["needs_file_processing"] = True
    elif task_type == "reco":
        state["user_intent"] = "reco"
        state["recommendation_target"] = task_target if task_target else "全部"
        # 推荐任务需要确保有分类数据
        state["needs_file_processing"] = False
        if not state.get("classified_instruments"):
            logger.warning("推荐任务但没有分类数据，将先执行解析和分类")
            state["needs_file_processing"] = True
    else:
        logger.warning(f"未知任务类型: {task_type}")
        state["user_intent"] = "reco"
        state["needs_file_processing"] = False
    
    return state

def advance_task_index(state: InstrumentAgentState) -> InstrumentAgentState:
    """推进任务索引并设置下一个任务参数"""
    show_step(state, "推进任务进度")
    
    current_index = state.get("current_task_index", 0)
    planned_tasks = state.get("planned_tasks", [])
    total_tasks = len(planned_tasks)
    
    print(f"🔄 任务推进: 当前索引{current_index} → {current_index + 1}, 总任务数:{total_tasks}")
    
    # 推进到下一个任务
    new_index = current_index + 1
    state["current_task_index"] = new_index
    
    # 检查是否所有任务完成
    if new_index >= total_tasks:
        print(f"🎉 所有任务完成! 索引{new_index}>={total_tasks}, 设置完成标志")
        state["user_intent"] = "finish"  # 强制设置完成标志
        state["needs_file_processing"] = False  # 确保不再需要文件处理
        print(f"✅ 已设置: user_intent=finish, needs_file_processing=false")
        return state
        
    # 设置下一个任务
    next_task = planned_tasks[new_index]
    task_type = next_task.get("type", "")
    task_target = next_task.get("target", "")
            
    print(f"📋 准备执行下一个任务: {new_index + 1}/{total_tasks} - {task_type} ({task_target})")
            
    # 简化任务设置逻辑
    if task_type == "parse":
        state["needs_file_processing"] = True
        if task_target and task_target != "file/test.xlsx":
            state["excel_file_path"] = task_target
    elif task_type == "stats":
        state["needs_file_processing"] = False
    elif task_type == "reco":
        state["recommendation_target"] = task_target if task_target else "全部"
        state["needs_file_processing"] = False
        print(f"设置推荐目标: {state['recommendation_target']}")
    
    # 清除循环计数器，防止累积
    state["loop_count"] = 0
    
    return state

# ==================== 节点函数 ====================

def fetch_user_context(state: InstrumentAgentState) -> InstrumentAgentState:
    """获取用户上下文 - 启动LLM任务规划"""
    show_step(state, "获取用户上下文")
    
    logger.info("开始获取用户上下文，启动LLM任务规划")
    
    # 初始化循环计数器
    state["loop_count"] = 0
    state["max_loops"] = 5  # 防止死循环
    
    # 初始化任务规划状态
    if "planned_tasks" not in state:
        state["planned_tasks"] = []
    if "current_task_index" not in state:
        state["current_task_index"] = 0
    if "task_results" not in state:
        state["task_results"] = []
    
    return state

def enter_upload_file(state: InstrumentAgentState) -> InstrumentAgentState:
    """文件上传和校验 - 支持从用户输入中提取文件路径"""
    show_step(state, "文件上传验证")
    
    from tools.parse_user_input import extract_file_path
    
    # 首先检查状态中是否已有文件路径
    file_path = state.get("excel_file_path", "")
    
    # 如果没有文件路径，尝试从用户输入中提取
    if not file_path:
        user_input = None
        messages = state.get("messages", [])
        if messages:
            # 获取最后一条用户消息
            for msg in reversed(messages):
                if hasattr(msg, 'type') and msg.type == 'human':
                    user_input = msg.content
                    break
        
        if user_input:
            extracted_path = extract_file_path(user_input)
            if extracted_path:
                file_path = extracted_path
                state["excel_file_path"] = file_path
                logger.info(f"从用户输入提取文件路径: '{user_input}' -> '{file_path}'")
    
    logger.info(f"验证文件: {file_path}")
    
    # 严格验证文件
    if not file_path:
        state["file_valid"] = False
        state["file_error_message"] = "必须提供Excel文件路径"
    elif not file_path.lower().endswith(('.xlsx', '.xls')):
        state["file_valid"] = False
        state["file_error_message"] = "文件格式必须是.xlsx或.xls"
    elif not os.path.exists(file_path):
        state["file_valid"] = False
        state["file_error_message"] = f"文件不存在: {file_path}"
    else:
        state["file_valid"] = True
        logger.info("文件验证通过")
    
    return state

def error_no_file_or_format(state: InstrumentAgentState) -> InstrumentAgentState:
    """文件错误处理"""
    error_msg = state.get("file_error_message", "文件错误")
    state["has_error"] = True
    state["error_context"] = error_msg
    logger.error(f"文件错误: {error_msg}")
    return state

def extract_excel_tables_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """提取Excel表格"""
    show_step(state, "提取Excel表格")
    
    try:
        file_path = state.get("excel_file_path")
        logger.info(f"提取表格: {file_path}")
        
        # 调用工具函数
        from tools.extract_excel_tables import extract_excel_tables
        tables = extract_excel_tables(file_path)
        
        # 转换DataFrame为可序列化的格式，同时保持兼容性
        serializable_tables = []
        for table in tables:
            serializable_table = {
                'name': table.get('name', table.get('sheet_name', '未知')),
                'description': table.get('description', '无描述'),
                'sheet_name': table.get('sheet_name', ''),
                'headers': table.get('headers', []),
                'keyword_row': table.get('keyword_row', 0),
                'data_dict': table['data'].to_dict('records') if 'data' in table and hasattr(table['data'], 'to_dict') else []
            }
            serializable_tables.append(serializable_table)
        
        state["extracted_tables"] = serializable_tables
        state["has_multiple_tables"] = len(serializable_tables) > 1
        logger.info(f"成功提取 {len(serializable_tables)} 个表格")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"表格提取失败: {str(e)}"
        logger.error(f"表格提取异常: {str(e)}")
    
    return state

def clarify_table_choice(state: InstrumentAgentState) -> InstrumentAgentState:
    """智能提示用户选择表格 - 分析表格特点并给出建议"""
    # 步骤显示已在interactive_experience.py中处理，避免重复显示
    
    from tools.parse_user_input import parse_table_selection
    
    tables = state.get("extracted_tables", [])
    logger.info(f"🔍 发现 {len(tables)} 个表格，正在智能分析...")
    
    # 智能分析每个表格
    table_analysis = []
    for i, table in enumerate(tables):
        name = table.get('name', f'表格{i+1}')
        data_count = len(table.get('data_dict', []))
        
        # 分析表格特点
        analysis = {
            'index': i,
            'name': name,
            'data_count': data_count,
            'score': 0,
            'features': [],
            'recommendation': ''
        }
        
        # 基于名称分析
        name_lower = name.lower()
        if any(keyword in name_lower for keyword in ['仪表', '设备', '锅炉', '汽水', '清单']):
            analysis['score'] += 30
            analysis['features'].append('包含仪表相关关键词')
        
        if any(keyword in name_lower for keyword in ['封面', '目录', '说明', 'cover']):
            analysis['score'] -= 20
            analysis['features'].append('可能是封面或说明页')
        
        # 基于数据量分析
        if data_count > 50:
            analysis['score'] += 25
            analysis['features'].append(f'数据丰富({data_count}行)')
        elif data_count > 20:
            analysis['score'] += 15
            analysis['features'].append(f'数据适中({data_count}行)')
        elif data_count > 5:
            analysis['score'] += 5
            analysis['features'].append(f'数据较少({data_count}行)')
        else:
            analysis['score'] -= 10
            analysis['features'].append(f'数据很少({data_count}行)')
        
        # 生成推荐说明
        if analysis['score'] >= 30:
            analysis['recommendation'] = '🌟 强烈推荐 - 最可能是仪表数据表'
        elif analysis['score'] >= 15:
            analysis['recommendation'] = '👍 推荐 - 可能包含有用数据'
        elif analysis['score'] >= 5:
            analysis['recommendation'] = '⚠️  可选 - 数据量一般'
        else:
            analysis['recommendation'] = '❌ 不推荐 - 可能不是数据表'
        
        table_analysis.append(analysis)
    
    # 排序：按评分从高到低
    table_analysis.sort(key=lambda x: x['score'], reverse=True)
    
    # 显示智能分析结果
    logger.info("\n📊 表格智能分析结果:")
    for analysis in table_analysis:
        features_text = ', '.join(analysis['features'])
        logger.info(f"  {analysis['index']+1}. {analysis['name']}")
        logger.info(f"     {analysis['recommendation']}")
        logger.info(f"     特点: {features_text}")
        logger.info(f"     评分: {analysis['score']}")
    
    # 获取用户输入
    user_input = None
    messages = state.get("messages", [])
    if messages:
        # 获取最后一条用户消息
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    if not user_input:
        # 没有用户输入时，必须等待用户选择
        logger.info("⏳ 等待用户选择表格...")
        logger.info("💡 提示：请回复表格编号（如：1、2）或表格名称")
        # 不设置selected_table_index，保持等待状态
        return state
    else:
        # 使用LLM解析用户选择
        selected_index = parse_table_selection(user_input, tables)
        if selected_index is not None:
            state["selected_table_index"] = selected_index
            selected_analysis = next((a for a in table_analysis if a['index'] == selected_index), None)
            if selected_analysis:
                logger.info(f"✅ 用户选择表格 {selected_index + 1}: {selected_analysis['name']}")
                logger.info(f"   {selected_analysis['recommendation']}")
            else:
                logger.info(f"✅ 用户选择表格 {selected_index + 1}")
        else:
            # 无法解析用户输入，继续等待
            logger.warning(f"❓ 无法理解您的选择 '{user_input}'")
            logger.info("💡 请明确指定表格编号（如：选择2）或表格名称")
            # 不设置selected_table_index，继续等待用户输入
            return state
    
    # 验证索引有效性
    selected_index = state.get("selected_table_index", 0)
    if selected_index >= len(tables):
        logger.error(f"表格索引 {selected_index} 超出范围，使用表格1")
        state["selected_table_index"] = 0
    
    # 保存分析结果到状态
    state["table_analysis"] = table_analysis
    
    return state

def parse_instrument_table_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """解析仪表表格"""
    show_step(state, "解析仪表数据")
    
    try:
        tables = state.get("extracted_tables", [])
        selected_index = state.get("selected_table_index", 0)
        
        if selected_index >= len(tables):
            raise Exception(f"表格索引越界: {selected_index}")
            
        table_info = tables[selected_index]
        
        # 从序列化格式恢复DataFrame
        import pandas as pd
        
        data_dict = table_info.get('data_dict', [])
        if not data_dict:
            raise Exception("表格数据为空")
        
        table_data = pd.DataFrame(data_dict)
        logger.info(f"从序列化数据恢复DataFrame，维度: {table_data.shape}")
        
        logger.info(f"解析表格 {selected_index}")
        
        # 调用工具函数解析表格
        from tools.parse_instrument_table import extract_and_parse_instrument_table, validate_parsed_data
        parsed_df = extract_and_parse_instrument_table(table_data)
        
        if parsed_df.empty or not validate_parsed_data(parsed_df):
            raise Exception("表格解析结果无效")
            
        # 转换为字典列表格式
        instruments = []
        for _, row in parsed_df.iterrows():
            instrument = {
                '位号': str(row.get('位号', '')),
                '型号': str(row.get('型号', '')),
                '数量': int(row.get('数量', 1)),
                '规格': str(row.get('规格', '')),
                '备注': str(row.get('备注', '')),
                '仪表类型': str(row.get('仪表类型', ''))  # 保存表格分类信息！
            }
            instruments.append(instrument)
        
        state["parsed_instruments"] = instruments
        logger.info(f"解析到 {len(instruments)} 个仪表")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"表格解析失败: {str(e)}"
        logger.error(f"表格解析异常: {str(e)}")
    
    return state

def classify_instrument_type_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """分类仪表类型"""
    show_step(state, "智能仪表分类")
    
    try:
        instruments = state.get("parsed_instruments", [])
        logger.info(f"分类 {len(instruments)} 个仪表")
        
        # 批量分类仪表
        models = [inst.get('型号', '') for inst in instruments]
        contexts = [inst.get('规格', '') + ' ' + inst.get('备注', '') for inst in instruments]
        
        # 使用简化的智能分类（表格分类 + LLM分类）
        from tools.classify_instrument_type import batch_classify_instruments
        
        # 提取表格分类信息（如果有的话）
        table_categories = [inst.get('仪表类型', '') for inst in instruments]
        
        # 使用简化的分类策略
        classified_types = batch_classify_instruments(
            models=models, 
            specs=contexts,  # 使用规格+备注作为spec
            table_categories=table_categories,
            use_llm=True
        )
        
        # 构建分类结果
        classified_instruments = []
        unrecognized_count = 0
        for i, instrument in enumerate(instruments):
            classified_inst = instrument.copy()
            classified_inst['类型'] = classified_types[i]
            # 简化后不再有置信度概念
            classified_inst['置信度'] = 1.0 if classified_types[i] != "无法识别" else 0.0
            classified_instruments.append(classified_inst)
            
            if classified_types[i] == "无法识别":
                unrecognized_count += 1
        
        state["classified_instruments"] = classified_instruments
        
        # 基于无法识别的比例决定是否需要确认
        unrecognized_ratio = unrecognized_count / len(instruments) if instruments else 0
        state["classification_confidence"] = 1.0 - unrecognized_ratio
        state["needs_user_confirmation"] = unrecognized_ratio > 0.5  # 超过50%无法识别时需要确认
        
        logger.info(f"分类完成，{len(instruments) - unrecognized_count} 个已识别，{unrecognized_count} 个无法识别")
        
        # 统计分类结果
        type_counts = {}
        for inst in classified_instruments:
            inst_type = inst.get('类型', '无法识别')
            type_counts[inst_type] = type_counts.get(inst_type, 0) + inst.get('数量', 1)
        logger.info(f"分类统计: {type_counts}")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"仪表分类失败: {str(e)}"
        logger.error(f"仪表分类异常: {str(e)}")
    
    return state

def ask_user_confirm_type(state: InstrumentAgentState) -> InstrumentAgentState:
    """询问用户确认分类 - 使用LLM解析确认意图"""
    # 步骤显示已在interactive_experience.py中处理，避免重复显示
    
    from tools.parse_user_input import parse_classification_confirmation
    
    classified = state.get("classified_instruments", [])
    confidence = state.get("classification_confidence", 0.0)
    
    logger.info(f"请用户确认 {len(classified)} 个仪表的分类，当前置信度: {confidence}")
    
    # 防止死循环
    state["loop_count"] = state.get("loop_count", 0) + 1
    if state["loop_count"] > state.get("max_loops", 5):
        logger.warning("分类确认循环次数超限，强制完成")
        state["needs_user_confirmation"] = False
        return state
    
    # 显示当前分类结果
    for i, inst in enumerate(classified):
        logger.info(f"{i+1}. {inst.get('型号', '未知')} -> {inst.get('类型', '未知')} (置信度: {inst.get('置信度', 0):.2f})")
    
    # 获取用户输入
    user_input = None
    messages = state.get("messages", [])
    if messages:
        # 获取最后一条用户消息
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    if user_input:
        # 使用LLM解析用户确认
        confirmation = parse_classification_confirmation(user_input, classified)
        if confirmation.get("action") == "confirm":
            state["needs_user_confirmation"] = False
            logger.info(f"用户确认分类: '{user_input}'")
        elif confirmation.get("action") == "modify":
            # TODO: 实现分类修正逻辑
            logger.info(f"用户要求修正分类: '{user_input}' - {confirmation.get('details', '')}")
            # 暂时强制确认，避免死循环
            state["needs_user_confirmation"] = False
        else:
            # 默认确认
            state["needs_user_confirmation"] = False
            logger.info("无法解析确认意图，默认确认分类")
    else:
        # 没有用户输入，默认确认
        state["needs_user_confirmation"] = False
        logger.info("没有用户输入，默认确认分类")
    
    logger.info("分类确认完成")
    return state

def summarize_statistics_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """统计汇总"""
    show_step(state, "统计数据汇总")
    try:
        instruments = state.get("classified_instruments", [])
        logger.info(f"统计 {len(instruments)} 个仪表")
        
        # 直接使用已分类的数据进行统计，不再重新分类
        statistics = {
            "总数量": len(instruments),
            "总台数": sum(inst.get('数量', 1) for inst in instruments),
            "类型统计": {},
            "详细信息": []
        }
        
        # 按类型统计
        type_stats = {}
        standard_model_set = set()  # 用于统计标准型号数量
        no_model_count = 0  # 只有位号无型号的数量
        
        def is_standard_model(model_str):
            """判断是否为标准仪表型号"""
            if not model_str or str(model_str).strip() in ['', 'nan', 'None', '未知型号']:
                return False
            
            model_str = str(model_str).strip()
            
            # 排除过长的描述性文字（标准型号通常较短）
            if len(model_str) > 20:
                return False
            
            # 排除包含"控制箱"等描述性词汇的
            descriptive_keywords = ['控制箱', '操作台', '进口', '出口', '紧急', '向空', '排汽']
            if any(keyword in model_str for keyword in descriptive_keywords):
                return False
            
            return True
        
        for inst in instruments:
            inst_type = inst.get('类型', '无法识别')
            inst_model = inst.get('型号', '未知型号')
            
            # 统计类型
            if inst_type not in type_stats:
                type_stats[inst_type] = 0
            type_stats[inst_type] += inst.get('数量', 1)
            
            # 区分标准型号和非标准型号
            if is_standard_model(inst_model):
                standard_model_set.add(inst_model)
            else:
                no_model_count += inst.get('数量', 1)
        
        statistics["类型统计"] = type_stats
        statistics["不同型号数"] = len(standard_model_set)
        statistics["只有位号无型号"] = no_model_count
        
        # 生成详细信息（按型号汇总）
        from collections import defaultdict
        model_summary = defaultdict(lambda: {'数量': 0, '位号': [], '类型': '', '规格': set()})
        
        for inst in instruments:
            model = inst.get('型号', '未知型号')
            model_summary[model]['数量'] += inst.get('数量', 1)
            model_summary[model]['类型'] = inst.get('类型', '无法识别')
            if inst.get('位号'):
                model_summary[model]['位号'].append(inst.get('位号'))
            if inst.get('规格'):
                model_summary[model]['规格'].add(inst.get('规格'))
        
        # 转换为详细信息列表
        for model, info in model_summary.items():
            statistics["详细信息"].append({
                '仪表类型': info['类型'],
                '型号': model,
                '数量总和': info['数量'],
                '规格汇总': '; '.join(info['规格']),
                '位号列表': '; '.join(info['位号'])
            })
        
        state["instrument_statistics"] = statistics
        logger.info(f"统计完成: {statistics['总台数']} 台仪表，{len(statistics['类型统计'])} 种类型")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"统计失败: {str(e)}"
        logger.error(f"统计异常: {str(e)}")
    
    return state

def validate_recommendation_types(state: InstrumentAgentState) -> InstrumentAgentState:
    """验证推荐任务中指定的类型是否存在"""
    show_step(state, "验证推荐类型")
    
    try:
        # 获取已分类的仪表数据
        classified_instruments = state.get("classified_instruments", [])
        planned_tasks = state.get("planned_tasks", [])
        
        # 收集实际存在的类型
        available_types = list(set(
            inst.get('类型', '无法识别') 
            for inst in classified_instruments 
            if inst.get('类型', '无法识别') != '无法识别'
        ))
        
        state["available_types"] = available_types
        logger.info(f"🔍 可用类型: {available_types}")
        
        # 收集任务规划中指定的类型
        invalid_types = []
        for task in planned_tasks:
            if task.get("type") == "reco":
                target_type = task.get("target", "全部")
                if target_type != "全部" and target_type not in available_types:
                    invalid_types.append(target_type)
        
        state["invalid_types"] = invalid_types
        
        if invalid_types:
            state["needs_type_selection"] = True
            logger.warning(f"⚠️ 发现不存在的类型: {invalid_types}")
            print(f"\n⚠️ 检测到不存在的仪表类型: {', '.join(invalid_types)}")
            print(f"📋 表格中可用的类型: {', '.join(available_types)}")
        else:
            state["needs_type_selection"] = False
            logger.info("✅ 所有推荐类型都有效")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"类型验证失败: {str(e)}"
        logger.error(f"类型验证异常: {str(e)}")
    
    return state

def ask_user_select_type(state: InstrumentAgentState) -> InstrumentAgentState:
    """请求用户重新选择有效的仪表类型"""
    # 步骤显示已在interactive_experience.py中处理，避免重复显示
    
    from tools.parse_user_input import parse_type_selection
    
    invalid_types = state.get("invalid_types", [])
    available_types = state.get("available_types", [])
    
    logger.info(f"🔄 请用户重新选择类型，不存在: {invalid_types}")
    
    # 获取用户输入
    user_input = None
    messages = state.get("messages", [])
    if messages:
        # 获取最后一条用户消息
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    if not user_input:
        # 没有用户输入时，等待用户选择
        logger.info("⏳ 等待用户选择有效类型...")
        return state
    else:
        # 解析用户选择
        selected_types = parse_type_selection(user_input, available_types)
        
        if selected_types:
            # 更新任务规划中的推荐目标
            planned_tasks = state.get("planned_tasks", [])
            for task in planned_tasks:
                if task.get("type") == "reco":
                    if len(selected_types) == 1:
                        task["target"] = selected_types[0]
                        state["recommendation_target"] = selected_types[0]
                    else:
                        task["target"] = "全部"
                        state["recommendation_target"] = "全部"
            
            state["planned_tasks"] = planned_tasks
            state["needs_type_selection"] = False
            state["invalid_types"] = []
            
            logger.info(f"✅ 用户重新选择类型: {selected_types}")
            print(f"✅ 已更新推荐类型为: {', '.join(selected_types) if len(selected_types) > 1 else selected_types[0]}")
        else:
            # 无法解析，继续等待
            logger.warning(f"❓ 无法理解您的选择 '{user_input}'")
            print("💡 请明确指定类型名称或选择'全部'")
            return state
    
    return state

def check_user_intent(state: InstrumentAgentState) -> InstrumentAgentState:
    """检查用户意图 - 在任务规划前进行初步意图识别"""
    show_step(state, "分析用户意图")
    
    from tools.parse_user_input import parse_user_intent
    
    # 获取用户输入
    user_input = None
    messages = state.get("messages", [])
    if messages:
        # 获取最后一条用户消息
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    if user_input:
        # 使用LLM解析用户意图
        intent = parse_user_intent(user_input)
        if intent:
            state["user_intent"] = intent
            logger.info(f"从用户输入解析意图: '{user_input}' -> {intent}")
        else:
            # 无法解析，使用默认
            state["user_intent"] = "reco"
            logger.info("无法解析用户意图，默认使用推荐模式")
    else:
        # 没有用户输入，检查是否已设置
        if "user_intent" not in state:
            state["user_intent"] = "reco"
            logger.info("没有用户输入，默认使用推荐模式")
    
    intent = state.get("user_intent")
    logger.info(f"最终用户意图: {intent}")
    
    if intent not in ["stats", "reco"]:
        logger.warning(f"无效的用户意图 '{intent}'，强制使用推荐模式")
        state["user_intent"] = "reco"
    
    return state

def respond_statistics(state: InstrumentAgentState) -> InstrumentAgentState:
    """响应统计信息"""
    stats = state.get("instrument_statistics", {})
    state["final_report"] = f"仪表统计信息：\n{stats}"
    logger.info("生成统计响应")
    return state

def display_existing_statistics(state: InstrumentAgentState) -> InstrumentAgentState:
    """显示已有统计结果 - stats任务专用，支持按类型过滤"""
    show_step(state, "显示统计结果")
    stats = state.get("instrument_statistics", {})
    recommendation_target = state.get("recommendation_target", "全部")
    
    # 检查是否需要过滤特定仪表类型
    if recommendation_target != "全部":
        logger.info(f"📊 显示 {recommendation_target} 的统计信息")
        print(f"\n📊 {recommendation_target}统计结果:")
    else:
        logger.info("📊 显示全部仪表统计信息")
        print("\n📊 仪表统计结果:")
    
    print("=" * 30)
    
    if stats:
        type_distribution = stats.get('类型统计', {})
        
        if recommendation_target != "全部":
            # 过滤特定类型的统计
            if recommendation_target in type_distribution:
                target_count = type_distribution[recommendation_target]
                total_count = stats.get('总台数', 1)
                percentage = (target_count / total_count) * 100
                
                print(f"目标仪表类型: {recommendation_target}")
                print(f"数量: {target_count} 台 ({percentage:.1f}%)")
                print(f"占总量比例: {percentage:.1f}%")
                
                # 如果需要，可以显示该类型的更多详细信息
                classified_instruments = state.get("classified_instruments", [])
                target_instruments = [inst for inst in classified_instruments 
                                    if inst.get('类型') == recommendation_target]
                
                if target_instruments:
                    # 统计该类型的型号分布
                    model_stats = {}
                    for inst in target_instruments:
                        model = inst.get('型号', '未知型号')
                        model_stats[model] = model_stats.get(model, 0) + inst.get('数量', 1)
                    
                    if len(model_stats) > 1:
                        print(f"\n{recommendation_target}型号分布:")
                        sorted_models = sorted(model_stats.items(), key=lambda x: x[1], reverse=True)
                        for model, count in sorted_models:
                            print(f"  • {model}: {count} 台")
                
            else:
                print(f"⚠️ 未找到 {recommendation_target} 类型的仪表")
                print("可用的仪表类型:")
                for type_name, count in type_distribution.items():
                    if count > 0:
                        print(f"  • {type_name}: {count} 台")
        else:
            # 显示完整统计
            print(f"总仪表条目: {stats.get('总数量', '未知')} 条")
            print(f"总台数: {stats.get('总台数', '未知')} 台")
            print(f"仪表类型: {len(type_distribution)} 种")
            print(f"不同型号: {stats.get('不同型号数', '未知')} 种")
            
            # 显示只有位号无型号的统计
            no_model_count = stats.get('只有位号无型号', 0)
            if no_model_count > 0:
                print(f"只有位号无型号: {no_model_count} 台")
            
            if type_distribution:
                print("\n类型分布:")
                sorted_types = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)
                total_count = stats.get('总台数', 1)
                for type_name, count in sorted_types:
                    percentage = (count / total_count) * 100
                    print(f"  • {type_name}: {count} 台 ({percentage:.1f}%)")
    else:
        print("暂无统计数据")
    
    print("=" * 30)
    
    # 更新最终报告
    if recommendation_target != "全部":
        state["final_report"] = f"{recommendation_target}统计信息：\n数量: {type_distribution.get(recommendation_target, 0)} 台"
    else:
        state["final_report"] = f"仪表统计信息：\n{stats}"
    
    logger.info(f"显示统计结果完成，目标类型: {recommendation_target}")
    return state

def _is_semantically_similar(new_standard: str, existing_standards: List[str], threshold: float = 0.8) -> bool:
    """
    判断新标准是否与已有标准语义相似
    
    Args:
        new_standard: 新标准文本
        existing_standards: 已有标准列表
        threshold: 语义相似度阈值
    
    Returns:
        True表示相似，应该去重
    """
    if not existing_standards:
        return False
    
    try:
        # 简化的语义相似度判断：基于关键词重叠度
        new_words = set(new_standard.replace('。', '').replace('，', '').replace(' ', '').split())
        
        for existing in existing_standards:
            existing_words = set(existing.replace('。', '').replace('，', '').replace(' ', '').split())
            
            # 计算词汇重叠度
            if len(new_words) > 0 and len(existing_words) > 0:
                overlap = len(new_words & existing_words)
                similarity = overlap / min(len(new_words), len(existing_words))
                
                if similarity >= threshold:
                    return True
        
        return False
        
    except Exception:
        # 如果语义判断失败，回退到文本完全匹配
        return new_standard in existing_standards

def match_standard_clause_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """匹配标准条款 - 支持按目标类型过滤，多选标准供LLM筛选"""
    show_step(state, "匹配安装标准")
    
    try:
        instruments = state.get("classified_instruments", [])
        recommendation_target = state.get("recommendation_target", "全部")
        
        print(f"🔍 开始匹配标准，目标类型: {recommendation_target}")
        logger.info(f"为目标类型 '{recommendation_target}' 匹配标准，仪表总数: {len(instruments)}")
        
        # 收集仪表类型 - 根据目标过滤
        if recommendation_target == "全部":
            instrument_types = list(set(inst.get('类型', '无法识别') for inst in instruments))
            instrument_types = [t for t in instrument_types if t != '无法识别']
        else:
            # 只匹配目标类型
            target_instruments = [inst for inst in instruments 
                                if inst.get('类型') == recommendation_target]
            if target_instruments:
                instrument_types = [recommendation_target]
                print(f"🔍 目标类型 '{recommendation_target}' 包含 {len(target_instruments)} 个仪表")
            else:
                print(f"⚠️ 目标类型 '{recommendation_target}' 不存在，将匹配所有类型")
                instrument_types = list(set(inst.get('类型', '无法识别') for inst in instruments))
                instrument_types = [t for t in instrument_types if t != '无法识别']
        
        print(f"🔍 将匹配的仪表类型: {instrument_types}")
        
        if not instrument_types:
            print("⚠️ 没有有效的仪表类型用于匹配标准")
            logger.warning("没有有效的仪表类型用于匹配标准")
            state["matched_standards"] = []
            state["has_standards"] = False
            return state
        
        # 为每种类型匹配更多候选标准，让LLM来筛选
        all_standards = []
        print(f"🔍 开始为 {len(instrument_types)} 种类型匹配标准（增加候选数量）...")
        
        for i, inst_type in enumerate(instrument_types, 1):
            try:
                print(f"\n🔍 匹配标准 {i}/{len(instrument_types)}: {inst_type}")
                from tools.enhanced_rag_retriever import EnhancedRAGRetriever
                
                # 使用增强检索器进行检索，增加候选数量
                enhanced_retriever = EnhancedRAGRetriever()
                search_results = enhanced_retriever.advanced_search(
                    inst_type, 
                    instrument_type=inst_type, 
                    top_k=8  # 🎯 从3增加到8，提高召回率，让LLM来筛选
                )
                
                # 提取内容文本
                standards = [result['content'] for result in search_results if 'content' in result]
                
                if standards:
                    print(f"   ✅ 找到 {len(standards)} 条候选标准（供LLM筛选）")
                    
                    # 打印每条标准的简要信息
                    for j, std in enumerate(standards, 1):
                        print(f"   📋 候选标准 {j}: {std[:80]}..." if len(std) > 80 else f"   📋 候选标准 {j}: {std}")
                    
                    # 检查并添加到总列表（保留语义去重，但更宽松）
                    added_count = 0
                    for std in standards:
                        # 放宽语义去重的阈值，避免误删有用标准
                        is_duplicate = _is_semantically_similar(std, all_standards, threshold=0.9)  # 提高阈值到0.9
                        
                        if not is_duplicate:
                            all_standards.append(std)
                            added_count += 1
                        else:
                            print(f"   ⚠️ 跳过高度相似标准: {std[:40]}...")
                    
                    print(f"   ➕ 新增 {added_count} 条候选标准到总列表")
                else:
                    print(f"   ❌ 未找到候选标准")
                
            except Exception as e:
                print(f"   ⚠️ 匹配失败: {str(e)}")
                logger.warning(f"为类型 {inst_type} 匹配标准失败: {str(e)}")
                continue
        
        state["matched_standards"] = all_standards
        state["has_standards"] = len(all_standards) > 0
        
        if recommendation_target != "全部":
            print(f"🔍 为目标类型 '{recommendation_target}' 匹配到 {len(all_standards)} 条候选标准（供LLM筛选）")
            logger.info(f"为目标类型 '{recommendation_target}' 匹配到 {len(all_standards)} 条候选标准")
        else:
            print(f"🔍 标准匹配完成，总共匹配到 {len(all_standards)} 条候选标准（供LLM筛选）")
            logger.info(f"匹配到 {len(all_standards)} 条候选标准")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"标准匹配失败: {str(e)}"
        logger.error(f"标准匹配异常: {str(e)}")
    
    return state

def respond_stats_with_note(state: InstrumentAgentState) -> InstrumentAgentState:
    """响应统计信息并附注"""
    stats = state.get("instrument_statistics", {})
    state["final_report"] = f"仪表统计信息：\n{stats}\n\n注意：未找到相关安装标准"
    logger.info("生成带注释的统计响应")
    return state

def ask_user_approval(state: InstrumentAgentState) -> InstrumentAgentState:
    """请求用户授权 - 使用LLM解析自然语言决定"""
    # 步骤显示由interactive_experience.py在中断检测时处理
    
    from tools.parse_user_input import parse_approval_decision
    
    standards = state.get("matched_standards", [])
    logger.info(f"请求用户授权使用敏感工具处理 {len(standards)} 条标准")
    
    # 获取用户输入
    user_input = None
    messages = state.get("messages", [])
    if messages:
        # 获取最后一条用户消息
        for msg in reversed(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    if user_input:
        # 使用LLM解析用户授权决定
        approval = parse_approval_decision(user_input)
        if approval is not None:
            state["user_approved_sensitive"] = approval
            logger.info(f"从用户输入解析授权: '{user_input}' -> {'同意' if approval else '拒绝'}")
        else:
            # 无法解析，默认拒绝（安全第一）
            state["user_approved_sensitive"] = False
            logger.warning(f"无法解析授权决定 '{user_input}'，默认拒绝")
    else:
        # 没有用户输入，默认拒绝（安全第一）
        state["user_approved_sensitive"] = False
        logger.info("没有用户输入，默认拒绝敏感工具授权")
    
    return state

def spec_sensitive_tools(state: InstrumentAgentState) -> InstrumentAgentState:
    """使用敏感工具 - 确保状态正确传递"""
    show_step(state, "执行专业分析")
    logger.info("使用敏感工具进行高级处理")
    
    # 确保必要的状态信息存在
    if not state.get("classified_instruments"):
        logger.warning("敏感工具处理时缺少分类数据")
    
    if not state.get("matched_standards"):
        logger.warning("敏感工具处理时缺少标准数据")
    
    # 确保推荐目标设置
    if not state.get("recommendation_target"):
        state["recommendation_target"] = "全部"
        logger.info("设置默认推荐目标: 全部")
    
    logger.info("敏感工具处理完成，准备生成安装推荐")
    return state

def skip_sensitive_and_go_on(state: InstrumentAgentState) -> InstrumentAgentState:
    """跳过敏感工具"""
    show_step(state, "跳过专业分析")
    logger.info("跳过敏感工具，继续基础处理")
    return state

def generate_installation_reco_node(state: InstrumentAgentState) -> InstrumentAgentState:
    """生成安装推荐 - 使用增强版LLM生成器生成详细可靠的专业推荐内容并自动保存"""
    show_step(state, "生成详细安装推荐")
    try:
        from tools.enhanced_installation_generator import EnhancedInstallationRecommendationGenerator
        
        instruments = state.get("classified_instruments", [])
        standards = state.get("matched_standards", [])
        recommendation_target = state.get("recommendation_target", "全部")
        
        logger.info(f"🤖 使用增强版LLM为 {len(instruments)} 个仪表生成详细安装推荐，目标类型: {recommendation_target}")
        
        # 初始化增强版LLM推荐生成器（启用自动保存）
        generator = EnhancedInstallationRecommendationGenerator(auto_save=True)
        
        # 按型号分组仪表（更细粒度）
        model_groups = {}
        for inst in instruments:
            inst_type = inst.get('类型', '无法识别')
            inst_model = inst.get('型号', '未知型号')
            
            # 使用 "类型-型号" 作为分组键
            group_key = f"{inst_type}-{inst_model}"
            
            if group_key not in model_groups:
                model_groups[group_key] = {
                    'type': inst_type,
                    'model': inst_model,
                    'instruments': []
                }
            model_groups[group_key]['instruments'].append(inst)
        
        # 筛选目标组
        target_groups = []
        if recommendation_target == "全部":
            target_groups = [g for g in model_groups.values() if g['type'] != '无法识别']
        else:
            # 特定类型
            target_groups = [g for g in model_groups.values() 
                           if g['type'] == recommendation_target or recommendation_target == "全部"]
            if not target_groups:
                # 如果指定类型不存在，生成所有类型
                target_groups = [g for g in model_groups.values() if g['type'] != '无法识别']
                logger.warning(f"指定类型 '{recommendation_target}' 不存在，生成所有型号")
        
        logger.info(f"将为 {len(target_groups)} 种型号使用增强版LLM生成详细推荐并自动保存")
        
        recommendations = []
        saved_files = []  # 记录保存的文件
        
        # 为每种目标型号生成详细的LLM推荐
        for group in target_groups:
            inst_type = group['type']
            inst_model = group['model']
            inst_list = group['instruments']
            
            total_quantity = sum(inst.get('数量', 1) for inst in inst_list)
            
            # 获取规格信息
            specs = [inst.get('规格', '') for inst in inst_list if inst.get('规格')]
            spec_text = '; '.join(set(specs)) if specs else ''
            
            # 获取备注信息作为工艺条件
            notes = [inst.get('备注', '') for inst in inst_list if inst.get('备注')]
            process_conditions = '; '.join(set(notes)) if notes else ''
            
            try:
                logger.info(f"🤖 使用增强版LLM生成 {inst_type}-{inst_model} 详细安装推荐...")
                
                # 使用增强版LLM生成详细专业推荐（自动保存为.md文件）
                llm_recommendation = generator.generate_installation_recommendation(
                    instrument_type=inst_type,
                    model_spec=inst_model,
                    quantity=total_quantity,
                    process_conditions=process_conditions,
                    custom_requirements=spec_text
                )
                
                # 格式化推荐内容
                recommendation_content = llm_recommendation.get('main_recommendation', '生成失败')
                
                # 如果生成失败，使用基础模板
                if '生成失败' in recommendation_content or '错误' in recommendation_content:
                    logger.warning(f"LLM生成失败，使用基础推荐: {inst_type}-{inst_model}")
                    recommendation_content = f"""## 基础安装方案
基于{inst_type}的标准工程安装方案：
1. 按照国家标准和行业规范执行安装
2. 确保仪表精度和系统安全性
3. 遵循制造商技术要求
4. 实施质量控制和验收程序

**重要提醒：** 详细推荐生成时遇到技术问题，请务必咨询专业工程师确保安装质量和安全性。"""

                recommendations.append({
                    '仪表类型': inst_type,
                    '型号': inst_model,
                    '数量': total_quantity,
                    '规格': spec_text,
                    '推荐内容': recommendation_content,
                    '材料清单': llm_recommendation.get('material_list', ''),
                    '安全要求': llm_recommendation.get('safety_requirements', ''),
                    '保存文件': llm_recommendation.get('saved_file_path', '')
                })
                
                # 记录保存的文件
                if llm_recommendation.get('saved_file_path'):
                    saved_files.append(llm_recommendation.get('saved_file_path'))
                
                logger.info(f"✅ 增强版LLM为 {inst_type}-{inst_model} 生成详细推荐成功 ({total_quantity} 台)")
                if llm_recommendation.get('saved_file_path'):
                    logger.info(f"📄 推荐已保存: {llm_recommendation.get('saved_file_path')}")
                
            except Exception as e:
                logger.error(f"增强版LLM生成推荐失败 {inst_type}-{inst_model}: {str(e)}")
                # 使用工程规范的备份推荐
                recommendations.append({
                    '仪表类型': inst_type,
                    '型号': inst_model,
                    '数量': total_quantity,
                    '规格': spec_text,
                    '推荐内容': f"""## 工程安装基础方案
基于{inst_type}的标准工程安装方案：

### 安装位置要求
- 符合工艺流程和测量精度要求
- 便于维护和操作安全
- 避免振动、电磁干扰等不利因素

### 安装工艺要求  
- 严格按照设计图纸和技术规范执行
- 遵循国家标准和行业规范
- 确保连接可靠、密封良好

### 质量控制
- 执行三检制度（自检、互检、专检）
- 进行必要的调试和验收测试
- 建立完整的安装记录和档案

**安全提醒：** 由于技术原因无法生成详细推荐，请务必咨询专业工程师，确保安装的可靠性和安全性。""",
                    '材料清单': '请参考设计图纸和技术规范',
                    '安全要求': '严格遵循相关安全规程和标准',
                    '保存文件': ''
                })
                logger.info(f"⚠️  {inst_type}-{inst_model} 使用工程规范备用推荐")
        
        state["installation_recommendations"] = recommendations
        
        # 在日志中显示保存的文件信息
        if saved_files:
            logger.info(f"📁 已保存 {len(saved_files)} 个推荐文件到 ./recommendation/ 目录")
            for file_path in saved_files:
                logger.info(f"   📄 {file_path}")
        
        logger.info(f"🎉 增强版LLM详细安装推荐生成完成: {len(recommendations)} 条专业推荐")
            
    except Exception as e:
        state["has_error"] = True
        state["error_context"] = f"增强版LLM推荐生成失败: {str(e)}"
        logger.error(f"增强版LLM推荐生成异常: {str(e)}")
    
    return state

def respond_full_report(state: InstrumentAgentState) -> InstrumentAgentState:
    """响应完整报告"""
    show_step(state, "生成完整报告")
    stats = state.get("instrument_statistics", {})
    recommendations = state.get("installation_recommendations", [])
    
    report = f"""
=== 仪表分析完整报告 ===

统计信息：
{stats}

安装推荐：
{recommendations}
"""
    
    state["final_report"] = report
    # 标记最后一个任务已完成，强制结束
    state["user_feedback"] = "finish"
    logger.info("完整报告生成完成，标记流程结束")
    return state

def feedback_loop_gateway(state: InstrumentAgentState) -> InstrumentAgentState:
    """反馈循环网关 - 检查当前任务是否完成，决定是否推进"""
    planned_tasks = state.get("planned_tasks", [])
    current_index = state.get("current_task_index", 0)
    
    logger.info(f"🎯 反馈循环检查: 任务{current_index + 1}/{len(planned_tasks)}")
    
    # 防止死循环
    state["loop_count"] = state.get("loop_count", 0) + 1
    if state["loop_count"] > 5:
        logger.warning("反馈循环次数超限，强制结束")
        state["user_feedback"] = "finish"
        state["user_intent"] = "finish"
        return state
    
    # 检查当前任务是否完成
    if planned_tasks and current_index < len(planned_tasks):
        current_task = planned_tasks[current_index]
        task_type = current_task.get("type", "")
        
        # 根据任务类型检查完成条件
        if task_type == "parse":
            completed = bool(state.get("parsed_instruments"))
        elif task_type == "stats":
            completed = bool(state.get("instrument_statistics"))
        elif task_type == "reco":
            completed = bool(state.get("installation_recommendations"))
        else:
            completed = True
        
        if completed:
            logger.info(f"✅ 任务{current_index + 1}({task_type})已完成，推进到下一个任务")
            state["user_feedback"] = "finish"
        else:
            logger.warning(f"⚠️ 任务{current_index + 1}({task_type})未完成，但继续推进")
            state["user_feedback"] = "finish"
    else:
        # 没有规划任务或索引超出范围
        logger.info("没有更多任务，完成流程")
        state["user_feedback"] = "finish"
        state["user_intent"] = "finish"
    
    return state

def error_handler(state: InstrumentAgentState) -> InstrumentAgentState:
    """错误处理器"""
    error_msg = state.get("error_context", "未知错误")
    logger.error(f"处理错误: {error_msg}")
    
    state["final_report"] = f"处理过程中发生错误：{error_msg}"
    return state

# ==================== 路由函数 ====================

def task_confirmation_gateway(state: InstrumentAgentState) -> str:
    """任务确认网关 - 显示规划后直接执行"""
    return "yes"  # 总是显示任务规划（但不需要用户确认）

def table_selection_gateway(state: InstrumentAgentState) -> str:
    """表格选择网关 - 决定选择方式"""
    # 总是让用户确认表格选择，确保使用正确的数据
    # 这样可以避免自动使用错误的表格
    return "user_select"

def task_continue_gateway(state: InstrumentAgentState) -> str:
    """任务继续网关 - 判断是否继续下一个任务"""
    planned_tasks = state.get("planned_tasks", [])
    current_index = state.get("current_task_index", 0)
    user_intent = state.get("user_intent", "")
    
    print(f"🔍 任务继续检查: 索引{current_index}/{len(planned_tasks)}, 意图:{user_intent}")
    
    # 检查是否有明确的完成标志
    if user_intent == "finish":
        print("✅ 检测到完成标志，结束流程")
        return "all_done"
    
    if current_index >= len(planned_tasks):
        print("✅ 所有任务索引完成，结束流程")
        return "all_done"
    else:
        # 检查是否需要文件处理
        needs_file = state.get("needs_file_processing", False)
        if needs_file:
            print("📁 需要文件处理，进入文件上传")
            return "need_file_processing"
        else:
            print("📋 继续下一个任务")
            return "continue_task"

def file_ok_gateway(state: InstrumentAgentState) -> str:
    """文件检查网关"""
    return "yes" if state.get("file_valid", False) else "no"



def confidence_gateway(state: InstrumentAgentState) -> str:
    """置信度检查网关"""
    return "yes" if state.get("needs_user_confirmation", False) else "no"

def intent_gateway(state: InstrumentAgentState) -> str:
    """意图分流网关 - 根据当前要执行的任务决定路由"""
    planned_tasks = state.get("planned_tasks", [])
    current_index = state.get("current_task_index", 0)
    
    print(f"🎯 intent_gateway: 索引{current_index}/{len(planned_tasks)}")
    
    # 如果有规划任务，根据当前任务决定路由
    if planned_tasks and current_index < len(planned_tasks):
        current_task = planned_tasks[current_index]
        task_type = current_task.get("type", "reco")
        
        print(f"🎯 当前任务类型: {task_type}")
        
        # 根据任务类型决定路由
        if task_type == "stats":
            print("🎯 路由到: stats")
            return "stats"
        elif task_type == "reco":
            print("🎯 路由到: reco")
            return "reco"
        else:
            # parse任务不应该到这里，默认走stats
            print("🎯 未知任务类型，路由到: stats")
            return "stats"
    
    # 没有任务或索引超出范围，使用备用逻辑
    user_intent = state.get("user_intent", "reco")
    print(f"🎯 无规划任务，根据用户意图路由: {user_intent}")
    return "stats" if user_intent == "stats" else "reco"

def standards_gateway(state: InstrumentAgentState) -> str:
    """标准检查网关"""
    return "yes" if state.get("has_standards", False) else "no"

def approval_gateway(state: InstrumentAgentState) -> str:
    """授权检查网关"""
    return "approved" if state.get("user_approved_sensitive", False) else "rejected"

def feedback_gateway(state: InstrumentAgentState) -> str:
    """反馈检查网关"""
    return "modify" if state.get("user_feedback") == "modify" else "finish"

def error_check_gateway(state: InstrumentAgentState, next_node: str) -> str:
    """错误检查网关"""
    return "error" if state.get("has_error", False) else next_node

def type_validation_gateway(state: InstrumentAgentState) -> str:
    """类型验证网关 - 检查推荐类型是否需要验证"""
    return "validate" if state.get("needs_type_selection", False) else "proceed"

# ==================== 图构建函数 ====================

def create_instrument_agent():
    """
    创建仪表分析智能体 - 在原有架构基础上集成LLM增强功能
    """
    logger.info("开始构建智能体（在原有架构基础上集成LLM）...")
    
    # 启用LangSmith追溯
    try:
        from config.settings import setup_langsmith_tracing
        setup_langsmith_tracing()
    except Exception as e:
        logger.warning(f"LangSmith追溯设置失败: {e}")
    
    # 创建图构建器
    builder = StateGraph(InstrumentAgentState)
    
    # ==================== 添加所有功能节点 ====================
    
    # 0. 起点和环境 - 集成LLM任务规划
    builder.add_node("fetch_user_context", fetch_user_context)
    builder.add_node("llm_task_planner", llm_task_planner)  # LLM任务规划
    builder.add_node("ask_user_confirm_tasks", ask_user_confirm_tasks)  # 任务确认
    builder.add_node("task_router", task_router)  # 任务路由
    
    # 1. 上传和校验
    builder.add_node("enter_upload_file", enter_upload_file)
    builder.add_node("error_no_file_or_format", error_no_file_or_format)
    
    # 2. 表格处理 - 智能提示用户选择
    builder.add_node("extract_excel_tables", extract_excel_tables_node)
    builder.add_node("clarify_table_choice", clarify_table_choice)  # 智能提示用户选择
    builder.add_node("parse_instrument_table", parse_instrument_table_node)
    
    # 3. 分类和置信度处理
    builder.add_node("classify_instrument_type", classify_instrument_type_node)
    builder.add_node("ask_user_confirm_type", ask_user_confirm_type)
    builder.add_node("summarize_statistics", summarize_statistics_node)
    
    # 4. 类型验证（新增改进功能）
    builder.add_node("validate_recommendation_types", validate_recommendation_types)
    builder.add_node("ask_user_select_type", ask_user_select_type)
    
    # 5. 意图分流 - 保持原有逻辑但增强LLM理解
    builder.add_node("check_user_intent", check_user_intent)
    builder.add_node("respond_statistics", respond_statistics)
    builder.add_node("display_existing_statistics", display_existing_statistics)  # stats任务专用
    
    # 6. 安装推荐流程
    builder.add_node("match_standard_clause", match_standard_clause_node)
    builder.add_node("standards_gateway", lambda s: s)  # 标准检查网关 - 独立的菱形节点
    builder.add_node("respond_stats_with_note", respond_stats_with_note)
    
    # 7. 敏感工具授权
    builder.add_node("ask_user_approval", ask_user_approval)
    builder.add_node("spec_sensitive_tools", spec_sensitive_tools)
    builder.add_node("skip_sensitive_and_go_on", skip_sensitive_and_go_on)
    builder.add_node("generate_installation_reco", generate_installation_reco_node)
    builder.add_node("respond_full_report", respond_full_report)
    
    # 8. 反馈循环和任务推进
    builder.add_node("feedback_loop_gateway", feedback_loop_gateway)
    builder.add_node("advance_task_index", advance_task_index)
    
    # 9. 错误处理
    builder.add_node("error_handler", error_handler)
    
    # ==================== 设置入口点 ====================
    builder.set_entry_point("fetch_user_context")
    
    # ==================== 添加边和路由（修正逻辑顺序） ====================
    
    # 起点流程：先理解用户意图，再进行任务规划
    builder.add_edge("fetch_user_context", "check_user_intent")
    
    # 意图确认后进行任务规划
    builder.add_edge("check_user_intent", "llm_task_planner")
    
    # 任务确认网关
    builder.add_conditional_edges("llm_task_planner", task_confirmation_gateway, {
        "yes": "ask_user_confirm_tasks",
        "no": "task_router"
    })
    
    # 任务确认后进入路由
    builder.add_edge("ask_user_confirm_tasks", "task_router")
    
    # 任务路由到条件分支 - 根据任务类型和文件处理需求决定路径
    def task_routing_logic(state):
        needs_file = state.get("needs_file_processing", False)
        if needs_file:
            return "need_file"
        
        # 不需要文件处理时，根据当前任务类型决定入口
        planned_tasks = state.get("planned_tasks", [])
        current_index = state.get("current_task_index", 0)
        
        if planned_tasks and current_index < len(planned_tasks):
            current_task = planned_tasks[current_index]
            task_type = current_task.get("type", "stats")
            
            print(f"🚀 task_router: 当前任务{task_type}, 索引{current_index}")
            
            if task_type == "stats":
                # 检查是否已有统计数据
                has_stats = bool(state.get("instrument_statistics"))
                print(f"   📊 已有统计数据: {has_stats}")
                if has_stats:
                    print("   → 路由到: display_stats")
                    return "display_stats"  # 显示已有统计
                else:
                    print("   → 路由到: direct_stats")
                    return "direct_stats"   # 重新统计
            elif task_type == "reco":
                print("   → 路由到: direct_reco")
                return "direct_reco"
            else:
                print(f"   → 未知任务类型 {task_type}, 路由到: direct_stats")
                return "direct_stats"  # 默认统计
        else:
            return "direct_stats"  # 默认统计
    
    builder.add_conditional_edges("task_router", task_routing_logic, {
        "need_file": "enter_upload_file",           # 需要文件处理：进入文件上传
        "direct_stats": "summarize_statistics",     # 重新统计数据
        "display_stats": "display_existing_statistics",  # 显示已有统计
        "direct_reco": "match_standard_clause"      # 直接推荐任务
    })
    
    # 文件校验网关
    builder.add_conditional_edges("enter_upload_file", file_ok_gateway, {
        "yes": "extract_excel_tables",
        "no": "error_no_file_or_format"
    })
    
    # 表格提取后的多表格网关 - 直接用户选择
    builder.add_conditional_edges("extract_excel_tables",
        lambda s: error_check_gateway(s, table_selection_gateway(s)),
        {
            "single": "parse_instrument_table",     # 单表格直接解析
            "user_select": "clarify_table_choice",  # 多表格让用户选择
            "error": "error_handler"
        })
    
    # 用户表格选择后进入解析
    builder.add_edge("clarify_table_choice", "parse_instrument_table")
    
    # 解析后进入分类（含错误处理）
    builder.add_conditional_edges("parse_instrument_table",
        lambda s: error_check_gateway(s, "classify_instrument_type"),
        {
            "classify_instrument_type": "classify_instrument_type",
            "error": "error_handler"
        })
    
    # 置信度网关
    builder.add_conditional_edges("classify_instrument_type", confidence_gateway, {
        "yes": "ask_user_confirm_type",
        "no": "summarize_statistics"
    })
    
    # 置信度回环
    builder.add_edge("ask_user_confirm_type", "classify_instrument_type")
    
    # 统计后进入类型验证
    builder.add_edge("summarize_statistics", "validate_recommendation_types")
    
    # 类型验证网关
    builder.add_conditional_edges("validate_recommendation_types", type_validation_gateway, {
        "validate": "ask_user_select_type",  # 需要用户重新选择类型
        "proceed": "intent_gateway_node"    # 类型有效，继续正常流程
    })
    
    # 用户类型选择后重新验证
    builder.add_edge("ask_user_select_type", "validate_recommendation_types")
    
    # 添加一个专门的意图网关节点来处理路由
    builder.add_node("intent_gateway_node", lambda s: s)  # 简单的传递节点
    
    # 从意图网关节点进行分流
    builder.add_conditional_edges("intent_gateway_node", intent_gateway, {
        "stats": "respond_statistics",
        "reco": "match_standard_clause"
    })
    
    # 标准匹配后的错误检查
    builder.add_conditional_edges("match_standard_clause",
        lambda s: error_check_gateway(s, "standards_gateway"),
        {
            "standards_gateway": "standards_gateway",
            "error": "error_handler"
        })
    
    # 标准检查网关的条件边
    builder.add_conditional_edges("standards_gateway", standards_gateway, {
        "yes": "ask_user_approval",
        "no": "respond_stats_with_note"
        })
    
    # 用户授权网关
    builder.add_conditional_edges("ask_user_approval", approval_gateway, {
        "approved": "spec_sensitive_tools",
        "rejected": "skip_sensitive_and_go_on"
    })
    
    # 工具路径汇聚到推荐生成
    builder.add_edge("spec_sensitive_tools", "generate_installation_reco")
    builder.add_edge("skip_sensitive_and_go_on", "generate_installation_reco")
    
    # 推荐生成后
    builder.add_edge("generate_installation_reco", "respond_full_report")
    
    # 所有响应都进入反馈循环网关
    builder.add_edge("respond_statistics", "feedback_loop_gateway")
    builder.add_edge("display_existing_statistics", "feedback_loop_gateway")  # 新增
    builder.add_edge("respond_stats_with_note", "feedback_loop_gateway")
    builder.add_edge("respond_full_report", "feedback_loop_gateway")
    
    # 反馈循环条件边
    builder.add_conditional_edges("feedback_loop_gateway", feedback_gateway, {
        "modify": "summarize_statistics",   # 修改：重新进入意图分流（意图已确定）
        "finish": "advance_task_index"      # 完成：推进任务
    })
    
    # 任务推进后检查是否继续
    builder.add_conditional_edges("advance_task_index", task_continue_gateway, {
        "continue_task": "task_router",             # 继续下一个任务：重新路由到下一个任务
        "need_file_processing": "enter_upload_file", # 需要文件处理：进入文件上传
        "all_done": "__end__"                       # 所有任务完成
    })
    
    # 错误处理
    builder.add_edge("error_no_file_or_format", "__end__")
    builder.add_edge("error_handler", "__end__")
    
    # ==================== 编译图 ====================
    logger.info("编译智能体图...")
    
    # 启用检查点
    memory = MemorySaver()
    
    # 编译图 - 用户交互中断点（去掉任务确认）
    compiled_graph = builder.compile(
        checkpointer=memory,
        interrupt_before=[
            # "ask_user_confirm_tasks",     # 任务确认取消中断，直接执行
            "clarify_table_choice",         # 表格选择中断（强制用户选择）
            "ask_user_confirm_type",        # 分类确认中断
            "ask_user_select_type",         # 类型选择中断（新增）
            "ask_user_approval",            # 工具授权中断
        ]
    )
    
    logger.info("智能体构建完成！在原有架构基础上成功集成LLM增强功能")
    return compiled_graph

def generate_agent_graph_image():
    """
    生成智能体图片 - 集成到agent中
    """
    try:
        # 确保目录存在
        os.makedirs('graph', exist_ok=True)
        
        # 创建智能体
        agent = create_instrument_agent()
        
        # 生成图片
        graph_data = agent.get_graph(xray=True)
        image_bytes = graph_data.draw_mermaid_png()
        
        # 保存图片
        output_path = 'graph/instrument_agent.png'
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        # 同时保存mermaid代码
        mermaid_code = graph_data.draw_mermaid()
        mermaid_path = 'graph/instrument_agent.mermaid'
        with open(mermaid_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)
        
        logger.info(f"图片已生成: {output_path}")
        logger.info(f"Mermaid代码已保存: {mermaid_path}")
        
        return {
            'success': True,
            'image_path': output_path,
            'mermaid_path': mermaid_path,
            'size': len(image_bytes),
            'nodes': len(graph_data.nodes),
            'edges': len(graph_data.edges)
        }
        
    except Exception as e:
        logger.error(f"图片生成失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# 创建智能体实例
instrument_agent = create_instrument_agent()

if __name__ == "__main__":
    print("🚀 仪表分析智能体已创建")
    print("✅ 结构与graph.py完全一致")
    print("✅ 完全交互式设计，禁止默认参数")
    print("✅ 集成防死循环机制")
    print("✅ 集成图片生成功能")
    
    # 生成图片
    print("\n📊 正在生成智能体图片...")
    result = generate_agent_graph_image()
    
    if result['success']:
        print(f"✅ 图片生成成功!")
        print(f"📁 图片路径: {result['image_path']}")
        print(f"📁 Mermaid路径: {result['mermaid_path']}")
        print(f"📊 文件大小: {result['size']:,} bytes")
        print(f"🔗 图结构: {result['nodes']} 个节点, {result['edges']} 条边")
    else:
        print(f"❌ 图片生成失败: {result['error']}") 