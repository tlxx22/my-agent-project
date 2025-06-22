"""
用户输入解析工具 - 使用LLM理解自然语言输入
支持上下文理解和意图识别，不限制于预设选项
"""

import re
from typing import Optional, Dict, Any, List
import logging
import json
from config.settings import get_settings

# 配置日志
logger = logging.getLogger(__name__)

def create_llm():
    """创建LLM实例"""
    settings = get_settings()
    
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings["llm_model"],
        api_key=settings["openai_api_key"],
        base_url=settings["openai_base_url"],
        temperature=0.1
    )

def parse_table_selection(user_input: str, available_tables: List[Dict[str, Any]]) -> Optional[int]:
    """
    解析用户对表格选择的输入
    
    Args:
        user_input: 用户输入的自然语言
        available_tables: 可用的表格列表
    
    Returns:
        选择的表格索引，如果无法解析则返回None
    """
    if not user_input or not available_tables:
        return None
    
    user_input = user_input.strip()
    
    # 直接数字匹配
    if user_input.isdigit():
        idx = int(user_input) - 1  # 用户输入从1开始
        if 0 <= idx < len(available_tables):
            return idx
    
    # 使用LLM理解用户意图
    llm = create_llm()
    
    # 构建表格信息提示
    table_info = []
    for i, table in enumerate(available_tables):
        table_info.append(f"{i+1}. {table.get('name', f'表格{i+1}')} - {table.get('description', '无描述')}")
    
    prompt = f"""
用户需要从以下表格中选择一个：

{chr(10).join(table_info)}

用户的输入是："{user_input}"

请分析用户想要选择哪个表格。只需要返回表格的编号（1、2、3等），如果无法确定则返回"无法确定"。

不要解释，只返回编号或"无法确定"。
"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        
        # 提取数字
        numbers = re.findall(r'\d+', response)
        if numbers:
            idx = int(numbers[0]) - 1  # 转换为0开始的索引
            if 0 <= idx < len(available_tables):
                logger.info(f"LLM解析表格选择: '{user_input}' -> 表格{idx+1}")
                return idx
        
        logger.warning(f"无法解析表格选择: '{user_input}' -> '{response}'")
        return None
        
    except Exception as e:
        logger.error(f"LLM解析表格选择失败: {str(e)}")
        return None

def parse_user_intent(user_input: str) -> Optional[str]:
    """
    解析用户意图：统计 vs 推荐
    
    Args:
        user_input: 用户输入的自然语言
    
    Returns:
        "stats" 或 "reco"，如果无法解析则返回None
    """
    if not user_input:
        return None
    
    user_input = user_input.strip().lower()
    
    # 关键词匹配
    stats_keywords = ['统计', '数量', '汇总', 'stats', 'statistics', '总结', '计数']
    reco_keywords = ['推荐', '安装', '建议', 'recommendation', 'install', '方法', '指导']
    
    if any(keyword in user_input for keyword in stats_keywords):
        return "stats"
    elif any(keyword in user_input for keyword in reco_keywords):
        return "reco"
    
    # 使用LLM理解复杂意图
    llm = create_llm()
    
    prompt = f"""
用户说："{user_input}"

请判断用户想要什么：
1. 统计信息（stats）- 用户想了解仪表的数量、类型等统计数据
2. 安装推荐（reco）- 用户想得到仪表的安装建议和方法

只返回"stats"或"reco"，如果无法确定则返回"reco"（默认推荐）。
"""
    
    try:
        response = llm.invoke(prompt).content.strip().lower()
        
        if "stats" in response:
            logger.info(f"LLM解析用户意图: '{user_input}' -> stats")
            return "stats"
        else:
            logger.info(f"LLM解析用户意图: '{user_input}' -> reco（默认）")
            return "reco"
            
    except Exception as e:
        logger.error(f"LLM解析用户意图失败: {str(e)}")
        return "reco"  # 默认推荐

def parse_approval_decision(user_input: str) -> Optional[bool]:
    """
    解析用户对敏感工具的授权决定
    
    Args:
        user_input: 用户输入的自然语言
    
    Returns:
        True表示同意，False表示拒绝，None表示无法解析
    """
    if not user_input:
        return None
    
    user_input = user_input.strip().lower()
    
    # 明确的关键词
    approve_keywords = ['是', '好', '同意', '允许', 'yes', 'ok', 'approve', '确定', '可以']
    reject_keywords = ['不', '否', '拒绝', '不行', 'no', 'reject', '禁止', '不可以']
    
    if any(keyword in user_input for keyword in approve_keywords):
        return True
    elif any(keyword in user_input for keyword in reject_keywords):
        return False
    
    # 使用LLM理解复杂表达
    llm = create_llm()
    
    prompt = f"""
用户被询问是否授权使用敏感工具（可能访问外部资源或执行高级操作）。

用户的回复是："{user_input}"

请判断用户的态度：
- 如果用户同意/授权，返回"yes"
- 如果用户拒绝/不同意，返回"no"
- 如果无法确定，返回"no"（默认拒绝，安全第一）

只返回"yes"或"no"。
"""
    
    try:
        response = llm.invoke(prompt).content.strip().lower()
        
        result = "yes" in response
        logger.info(f"LLM解析授权决定: '{user_input}' -> {'同意' if result else '拒绝'}")
        return result
        
    except Exception as e:
        logger.error(f"LLM解析授权决定失败: {str(e)}")
        return False  # 默认拒绝

def parse_feedback_intent(user_input: str) -> Optional[str]:
    """
    解析用户反馈意图：modify（修改）或finish（完成）
    
    Args:
        user_input: 用户输入的自然语言
    
    Returns:
        "modify" 或 "finish"
    """
    if not user_input:
        return None
    
    user_input = user_input.strip().lower()
    
    # 关键词匹配 - 优先使用关键词匹配，更准确
    modify_keywords = ['修改', '更改', '重新', '再来', 'modify', 'change', 'redo', '调整', '不对', '错了']
    finish_keywords = ['完成', '结束', '好了', 'finish', 'done', 'ok', '满意', '可以', '行了', '够了', '结束了', '完了']
    
    # 精确匹配完成关键词
    if any(user_input == keyword for keyword in finish_keywords):
        logger.info(f"关键词精确匹配: '{user_input}' -> finish")
        return "finish"
    
    # 模糊匹配
    if any(keyword in user_input for keyword in modify_keywords):
        logger.info(f"关键词匹配: '{user_input}' -> modify")
        return "modify"
    elif any(keyword in user_input for keyword in finish_keywords):
        logger.info(f"关键词匹配: '{user_input}' -> finish")
        return "finish"
    
    # 使用LLM理解复杂意图
    llm = create_llm()
    
    prompt = f"""
用户看到了分析结果后的反馈："{user_input}"

请判断用户想要：
1. 修改（modify）- 用户不满意当前结果，想要重新分析或调整
2. 完成（finish）- 用户满意当前结果，想要结束流程

只返回"modify"或"finish"，如果无法确定则返回"finish"（默认完成）。
"""
    
    try:
        response = llm.invoke(prompt).content.strip().lower()
        
        if "modify" in response:
            logger.info(f"LLM解析反馈意图: '{user_input}' -> modify")
            return "modify"
        else:
            logger.info(f"LLM解析反馈意图: '{user_input}' -> finish")
            return "finish"
            
    except Exception as e:
        logger.error(f"LLM解析反馈意图失败: {str(e)}")
        return "finish"  # 默认完成

def parse_classification_confirmation(user_input: str, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    解析用户对分类结果的确认或修正
    
    Args:
        user_input: 用户输入的自然语言
        classifications: 当前的分类结果
    
    Returns:
        修正后的分类结果或确认信息
    """
    if not user_input or not classifications:
        return {"action": "confirm", "modifications": []}
    
    user_input = user_input.strip()
    
    # 简单确认
    confirm_keywords = ['对', '正确', '是的', 'yes', 'correct', '确认', '没问题']
    if any(keyword in user_input.lower() for keyword in confirm_keywords):
        return {"action": "confirm", "modifications": []}
    
    # 使用LLM解析修正意图
    llm = create_llm()
    
    # 构建当前分类信息
    current_info = []
    for i, cls in enumerate(classifications):
        current_info.append(f"{i+1}. {cls.get('型号', '未知')} -> {cls.get('类型', '未知')}")
    
    prompt = f"""
当前仪表分类结果：
{chr(10).join(current_info)}

用户的反馈："{user_input}"

请分析用户是：
1. 确认分类正确，返回：{{"action": "confirm"}}
2. 要求修正某些分类，返回：{{"action": "modify", "details": "具体修正内容"}}

只返回JSON格式，不要解释。
"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        
        # 尝试解析JSON
        try:
            result = json.loads(response)
            logger.info(f"LLM解析分类确认: '{user_input}' -> {result}")
            return result
        except json.JSONDecodeError:
            # 如果不是JSON，默认确认
            logger.warning(f"无法解析为JSON，默认确认: '{response}'")
            return {"action": "confirm", "modifications": []}
            
    except Exception as e:
        logger.error(f"LLM解析分类确认失败: {str(e)}")
        return {"action": "confirm", "modifications": []}

def extract_file_path(user_input: str) -> Optional[str]:
    """
    从用户输入中提取文件路径
    
    Args:
        user_input: 用户输入的自然语言
    
    Returns:
        提取的文件路径，如果没有则返回None
    """
    if not user_input:
        return None
    
    # 常见文件路径模式（修复版本）
    path_patterns = [
        r'([A-Za-z]:[\\\/][^\\\/\*\?\"\<\>\|]*\.xlsx?)',  # 绝对路径
        r'([^\\\/\*\?\"\<\>\|\s]*[\\\/][^\\\/\*\?\"\<\>\|\s]*\.xlsx?)',  # 包含目录的相对路径
        r'"([^"]*\.xlsx?)"',  # 引号包围的路径
        r"'([^']*\.xlsx?)'",  # 单引号包围的路径
        r'([^\s]*\.xlsx?)',  # 简单文件名（最后匹配）
    ]
    
    for pattern in path_patterns:
        matches = re.findall(pattern, user_input, re.IGNORECASE)
        if matches:
            file_path = matches[0].strip()
            # 如果找到包含目录的路径，立即返回
            if '/' in file_path or '\\' in file_path:
                logger.info(f"提取文件路径（含目录）: {file_path}")
                return file_path
    
    # 如果没找到目录路径，再次寻找简单文件名
    simple_pattern = r'([^\s]*\.xlsx?)'
    matches = re.findall(simple_pattern, user_input, re.IGNORECASE)
    if matches:
        file_path = matches[0].strip()
        logger.info(f"提取文件路径（文件名）: {file_path}")
        return file_path
    
    # 使用LLM提取文件路径
    llm = create_llm()
    
    prompt = f"""
用户说："{user_input}"

请从中提取Excel文件路径（.xlsx或.xls文件）。如果没有明确的文件路径，返回"无"。

只返回文件路径或"无"，不要解释。
"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        
        if response and response != "无" and ('.xlsx' in response.lower() or '.xls' in response.lower()):
            logger.info(f"LLM提取文件路径: '{user_input}' -> '{response}'")
            return response
            
        return None
        
    except Exception as e:
        logger.error(f"LLM提取文件路径失败: {str(e)}")
        return None

def parse_table_selection_with_llm(user_input: str, available_tables: List[str]) -> Optional[int]:
    """
    使用LLM解析用户的表格选择意图
    
    Args:
        user_input: 用户输入的自然语言
        available_tables: 可用表格列表
    
    Returns:
        选中的表格索引，如果无法确定返回None
    """
    try:
        settings = get_settings()
        
        if not settings.get("openai_api_key"):
            logger.warning("未配置OpenAI API Key，使用关键词匹配")
            return parse_table_selection_fallback(user_input, available_tables)
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings["llm_model"],
            api_key=settings["openai_api_key"], 
            base_url=settings["openai_base_url"],
            temperature=0.1
        )
        
        # 构建提示
        tables_info = "\n".join([f"{i+1}. {table}" for i, table in enumerate(available_tables)])
        
        prompt = f"""
请分析用户输入，确定他们想要选择哪个表格。

可用表格：
{tables_info}

用户输入："{user_input}"

请返回一个JSON格式的回答：
{{
  "selected_index": 表格索引(1-based, 1表示第一个表格),
  "confidence": 置信度(0-1),
  "reasoning": "选择理由"
}}

如果用户没有明确指定，请根据常识选择最相关的表格。
如果表格名称包含"仪表"、"设备"等关键词，优先选择。
"""
        
        response = llm.invoke(prompt)
        result_text = response.content.strip()
        
        # 尝试解析JSON
        try:
            result = json.loads(result_text)
            selected_index = result.get("selected_index", 1)
            confidence = result.get("confidence", 0.5)
            reasoning = result.get("reasoning", "")
            
            logger.info(f"LLM表格选择: 索引{selected_index}, 置信度{confidence:.2f}, 理由: {reasoning}")
            
            # 转换为0-based索引
            if 1 <= selected_index <= len(available_tables):
                return selected_index - 1
            else:
                logger.warning(f"LLM返回的索引{selected_index}超出范围，使用默认值")
                return 0
                
        except json.JSONDecodeError:
            logger.warning(f"LLM返回的不是有效JSON: {result_text}")
            return parse_table_selection_fallback(user_input, available_tables)
            
    except Exception as e:
        logger.error(f"LLM表格选择失败: {str(e)}")
        return parse_table_selection_fallback(user_input, available_tables)

def parse_table_selection_fallback(user_input: str, available_tables: List[str]) -> int:
    """
    基于关键词的表格选择备用方案
    
    Args:
        user_input: 用户输入
        available_tables: 可用表格列表
    
    Returns:
        选中的表格索引
    """
    user_input_lower = user_input.lower()
    
    # 检查数字
    numbers = re.findall(r'第?(\d+)', user_input)
    if numbers:
        try:
            index = int(numbers[0]) - 1  # 转换为0-based
            if 0 <= index < len(available_tables):
                return index
        except ValueError:
            pass
    
    # 检查关键词匹配
    keywords = ["仪表", "设备", "锅炉", "汽水", "清单"]
    for i, table_name in enumerate(available_tables):
        table_name_lower = table_name.lower()
        if any(keyword in table_name_lower for keyword in keywords):
            return i
    
    # 默认选择第2个（通常是数据表格）
    return 1 if len(available_tables) > 1 else 0

def parse_task_confirmation(user_input: str, planned_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    解析用户对任务规划的确认
    
    Args:
        user_input: 用户输入
        planned_tasks: 规划的任务列表
    
    Returns:
        包含action字段的字典，action可能是"confirm"或"modify"
    """
    if not user_input:
        return {"action": "confirm"}  # 默认确认
    
    user_input_lower = user_input.lower()
    
    # 确认关键词
    confirm_keywords = ["好", "是", "对", "确定", "同意", "按计划", "执行", "ok", "yes", "confirm"]
    if any(keyword in user_input_lower for keyword in confirm_keywords):
        return {"action": "confirm"}
    
    # 修改关键词
    modify_keywords = ["不", "否", "修改", "改", "重新", "no", "modify", "change"]
    if any(keyword in user_input_lower for keyword in modify_keywords):
        return {"action": "modify"}
    
    # 默认确认
    return {"action": "confirm"}

def create_task_planner_with_llm(user_input: str) -> List[Dict[str, Any]]:
    """
    使用LLM创建任务规划
    
    Args:
        user_input: 用户的复杂指令
    
    Returns:
        任务列表，每个任务包含type和target字段
    """
    try:
        settings = get_settings()
        
        if not settings.get("openai_api_key"):
            logger.warning("未配置OpenAI API Key，使用简单规划")
            return create_simple_task_plan(user_input)
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings["llm_model"], 
            api_key=settings["openai_api_key"],
            base_url=settings["openai_base_url"],
            temperature=0.0
        )
        
        system_prompt = """你是一个专业的仪表分析智能体规划器。
你的任务是将用户的复杂指令分解为有序的原子任务。

可用的工具类型：
1. "parse" - 解析Excel文件和表格数据
2. "stats" - 统计仪表型号与数量 
3. "reco" - 根据规范生成安装方法建议
4. "chart" - 绘制数量分布图表

请返回严格的JSON格式：
[
  {"type": "parse", "target": "file/test.xlsx"},
  {"type": "stats", "target": "全部"},
  {"type": "reco", "target": "全部"}
]

重要规则：
- **核心依赖关系**：任何stats或reco任务都必须先有parse任务获取数据
- **安装推荐依赖**：reco任务必须依赖stats任务的统计结果，完整流程是parse → stats → reco
- 如果用户要分析数据，先要有parse任务
- 如果要统计，需要先parse，再stats任务，默认target是"全部"
- 如果要安装建议，需要完整流程：先parse，再stats，最后reco任务
  * 当用户说"安装建议"而没有指定类型时，target设为"全部"
  * 只有明确提到特定类型时才使用具体类型，如"温度仪表安装建议"
- 如果要图表，需要chart任务
- 按逻辑顺序排列任务：parse → stats → reco → chart

示例：
用户："分析数据，给我统计和安装建议" 
→ [{"type":"parse","target":"file/test.xlsx"},{"type":"stats","target":"全部"},{"type":"reco","target":"全部"}]

用户："给我安装推荐"
→ [{"type":"parse","target":"file/test.xlsx"},{"type":"stats","target":"全部"},{"type":"reco","target":"全部"}]

用户："我要温度仪表的安装建议"
→ [{"type":"parse","target":"file/test.xlsx"},{"type":"stats","target":"全部"},{"type":"reco","target":"温度仪表"}]

用户："统计仪表数据"
→ [{"type":"parse","target":"file/test.xlsx"},{"type":"stats","target":"全部"}]

只返回JSON数组，不要其他解释。"""
        
        user_prompt = f'用户指令："{user_input}"'
        
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        result_text = response.content.strip()
        
        # 清理可能的markdown标记
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        try:
            tasks = json.loads(result_text)
            # 日志输出由调用方(llm_task_planner节点)负责，避免重复
            return tasks
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM返回的不是有效JSON: {result_text}")
            return create_simple_task_plan(user_input)
            
    except Exception as e:
        logger.error(f"LLM任务规划失败: {str(e)}")
        return create_simple_task_plan(user_input)

def create_simple_task_plan(user_input: str) -> List[Dict[str, Any]]:
    """
    创建简单的任务规划（备用方案）
    
    Args:
        user_input: 用户输入
    
    Returns:
        简单的任务列表
    """
    user_input_lower = user_input.lower()
    tasks = []
    
    # 检查是否需要解析文件
    if any(keyword in user_input_lower for keyword in ['分析', '解析', '文件', 'analyze', 'parse']):
        tasks.append({"type": "parse", "target": "file/test.xlsx"})
    
    # 检查是否需要统计
    if any(keyword in user_input_lower for keyword in ['统计', '数据', 'stats', 'statistics']):
        tasks.append({"type": "stats", "target": "全部"})
    
    # 检查是否需要安装建议
    if any(keyword in user_input_lower for keyword in ['安装', '建议', 'reco', 'installation']):
        # 检查是否指定了特定类型
        instrument_types = ['温度仪表', '压力仪表', '流量仪表', '液位仪表', '两位式电动门控制箱', '气动调节阀']
        specified_type = None
        
        for itype in instrument_types:
            if itype.replace('仪表', '') in user_input_lower or itype in user_input_lower:
                specified_type = itype
                break
        
        tasks.append({"type": "reco", "target": specified_type or "全部"})
    
    # 检查是否需要图表
    if any(keyword in user_input_lower for keyword in ['图表', '图', 'chart', 'plot']):
        tasks.append({"type": "chart", "target": "数量分布"})
    
    # 日志输出由调用方负责，避免重复
    return tasks

def parse_user_input(user_input: str) -> Dict[str, Any]:
    """
    解析用户输入的主函数
    
    Args:
        user_input: 用户的自然语言输入
    
    Returns:
        解析结果字典
    """
    return {
        "original_input": user_input,
        "intent": "complex_analysis",  # 默认为复杂分析意图
        "confidence": 0.8,
        "tasks": create_task_planner_with_llm(user_input)
    }

def parse_task_confirmation(user_input: str, planned_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    解析用户对任务规划的确认或修正
    
    Args:
        user_input: 用户输入的自然语言
        planned_tasks: 当前的任务规划
    
    Returns:
        确认结果或修正信息
    """
    if not user_input or not planned_tasks:
        return {"action": "confirm", "modifications": []}
    
    user_input = user_input.strip()
    
    # 简单确认
    confirm_keywords = ['对', '正确', '是的', 'yes', 'correct', '确认', '没问题', '好的', '可以']
    if any(keyword in user_input.lower() for keyword in confirm_keywords):
        return {"action": "confirm", "modifications": []}
    
    # 使用LLM解析修正意图
    llm = create_llm()
    
    # 构建当前任务信息
    tasks_info = []
    for i, task in enumerate(planned_tasks):
        tasks_info.append(f"{i+1}. {task.get('type', '未知')} - {task.get('target', '未知')}")
    
    prompt = f"""
当前任务规划：
{chr(10).join(tasks_info)}

用户的反馈："{user_input}"

请分析用户是：
1. 确认任务规划正确，返回：{{"action": "confirm"}}
2. 要求修正某些任务，返回：{{"action": "modify", "details": "具体修正内容"}}

只返回JSON格式，不要解释。
"""
    
    try:
        response = llm.invoke(prompt).content.strip()
        
        # 尝试解析JSON
        try:
            result = json.loads(response)
            logger.info(f"LLM解析任务确认: '{user_input}' -> {result}")
            return result
        except json.JSONDecodeError:
            # 如果不是JSON，默认确认
            logger.warning(f"无法解析为JSON，默认确认: '{response}'")
            return {"action": "confirm", "modifications": []}
            
    except Exception as e:
        logger.error(f"LLM解析任务确认失败: {str(e)}")
        return {"action": "confirm", "modifications": []}

def parse_type_selection(user_input: str, available_types: List[str]) -> List[str]:
    """
    解析用户对仪表类型的选择
    
    Args:
        user_input: 用户输入的自然语言
        available_types: 可用的仪表类型列表
    
    Returns:
        选中的类型列表，如果选择"全部"则返回所有类型
    """
    if not user_input or not available_types:
        return []
    
    user_input = user_input.strip()
    user_input_lower = user_input.lower()
    
    # 检查是否选择全部
    all_keywords = ['全部', '所有', '都要', '全选', 'all', 'everything']
    if any(keyword in user_input_lower for keyword in all_keywords):
        logger.info(f"用户选择全部类型: {available_types}")
        return available_types
    
    # 直接匹配类型名称
    selected_types = []
    for atype in available_types:
        # 完整匹配
        if atype in user_input:
            selected_types.append(atype)
            continue
        
        # 部分匹配（去掉"仪表"后缀）
        type_base = atype.replace('仪表', '')
        if type_base and type_base in user_input_lower:
            selected_types.append(atype)
            continue
        
        # 关键词匹配
        if atype == '温度仪表' and any(kw in user_input_lower for kw in ['温度', 'temperature', '热电偶', '温度计']):
            selected_types.append(atype)
        elif atype == '压力仪表' and any(kw in user_input_lower for kw in ['压力', 'pressure', '压表']):
            selected_types.append(atype)
        elif atype == '液位仪表' and any(kw in user_input_lower for kw in ['液位', 'level', '液面']):
            selected_types.append(atype)
        elif atype == '流量仪表' and any(kw in user_input_lower for kw in ['流量', 'flow', '流速']):
            selected_types.append(atype)
        elif atype == '两位式电动门控制箱' and any(kw in user_input_lower for kw in ['电动门', '控制箱', '阀门']):
            selected_types.append(atype)
        elif atype == '气动调节阀' and any(kw in user_input_lower for kw in ['气动', '调节阀', '阀']):
            selected_types.append(atype)
        elif atype == '显示仪表' and any(kw in user_input_lower for kw in ['显示', 'display', '指示']):
            selected_types.append(atype)
    
    if selected_types:
        logger.info(f"直接匹配选中类型: {selected_types}")
        return selected_types
    
    # 使用LLM解析复杂的选择意图
    try:
        settings = get_settings()
        
        if not settings.get("openai_api_key"):
            logger.warning("未配置OpenAI API Key，无法使用LLM解析")
            return []
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings["llm_model"],
            api_key=settings["openai_api_key"],
            base_url=settings["openai_base_url"],
            temperature=0.1
        )
        
        # 构建可用类型列表
        types_list = "\n".join([f"- {atype}" for atype in available_types])
        
        prompt = f"""
用户需要从以下仪表类型中选择：
{types_list}

用户的选择："{user_input}"

请分析用户想选择哪些类型，返回JSON格式：
{{
  "selected_types": ["类型1", "类型2"],  // 选中的类型名称（完整匹配）
  "select_all": false,  // 是否选择全部
  "reasoning": "选择理由"
}}

注意：
- 如果用户说"全部"、"所有"，设置select_all为true
- 否则根据用户描述匹配具体的类型名称
- 类型名称必须完全匹配可用列表中的名称
- 如果用户输入的类型不在列表中（如"冰箱"、"空调"等），返回空数组
- 只有确实相关的仪表类型才匹配，不要强行匹配不相关的类型
- 如果无法确定或不匹配，返回空数组

只返回JSON，不要解释。
"""
        
        response = llm.invoke(prompt).content.strip()
        
        # 清理可能的markdown标记
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            result = json.loads(response)
            
            if result.get("select_all", False):
                logger.info("LLM解析：用户选择全部类型")
                return available_types
            
            selected = result.get("selected_types", [])
            # 验证选中的类型是否在可用列表中
            valid_selected = [t for t in selected if t in available_types]
            
            if valid_selected:
                logger.info(f"LLM解析选中类型: {valid_selected}")
                return valid_selected
                
        except json.JSONDecodeError:
            logger.warning(f"LLM返回无效JSON: {response}")
            
    except Exception as e:
        logger.error(f"LLM解析类型选择失败: {str(e)}")
    
    # 无法解析时返回空列表
    logger.warning(f"无法解析用户类型选择: '{user_input}'")
    return []

# 示例使用函数
def test_parser():
    """测试解析器功能"""
    print("🧪 测试用户输入解析器")
    
    # 测试表格选择
    tables = ["仪表清单", "华辰锅炉汽水系统", "设备统计"]
    result1 = parse_table_selection("选择第二个", tables)
    print(f"表格选择: {result1}")
    
    # 测试用户意图
    result2 = parse_user_intent("给我统计数据和安装建议")
    print(f"用户意图: {result2}")
    
    # 测试授权决定
    result3 = parse_approval_decision("同意使用")
    print(f"授权决定: {result3}")

if __name__ == "__main__":
    test_parser() 