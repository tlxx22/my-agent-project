#!/usr/bin/env python3
"""
错误反思测试 4: 数据解析错误
=====================================
测试场景：Excel表格存在但数据格式不符合预期
错误节点：parse_instrument_table
预期决策：skip（尝试其他表格）或 terminate（数据格式完全错误）
"""

import sys
import os
from pathlib import Path
import pandas as pd

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def create_malformed_excel_file():
    """创建一个格式错误的Excel文件"""
    test_file = "test_malformed_data.xlsx"
    
    # 创建一个包含格式错误数据的Excel文件
    df = pd.DataFrame({
        '随机列1': ['这不是', '仪表数据', '完全错误'],
        '随机列2': ['格式', '不对', '无法解析'],
        '随机列3': [1, 2, 3],
        '空列': [None, None, None]
    })
    
    df.to_excel(test_file, index=False)
    return test_file

def test_data_parsing_error():
    """测试数据解析错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 4: 数据解析错误")
    print("=" * 50)
    
    # 创建格式错误的测试文件
    test_file = create_malformed_excel_file()
    print(f"📊 已创建格式错误的Excel文件: {test_file}")
    
    try:
        # 构造智能体状态 - 模拟数据解析失败的情况
        state = InstrumentAgentState(
            # 基础消息
            messages=[HumanMessage(content=f"请分析 {test_file} 文件")],
            
            # 错误相关状态
            has_error=True,
            error_context="数据解析失败: 无法在表格中找到有效的仪表数据列，表格格式可能不符合要求",
            error_source_node="parse_instrument_table",
            
            # 文件相关状态
            excel_file_path=test_file,
            file_valid=True,
            file_error_message="",
            
            # 表格相关状态 - 表格存在但内容错误
            extracted_tables=[{
                'name': 'Sheet1',
                'description': '包含格式错误数据的表格',
                'sheet_name': 'Sheet1',
                'headers': ['随机列1', '随机列2', '随机列3', '空列'],
                'keyword_row': 0,
                'data_dict': [
                    {'随机列1': '这不是', '随机列2': '格式', '随机列3': 1, '空列': None},
                    {'随机列1': '仪表数据', '随机列2': '不对', '随机列3': 2, '空列': None},
                    {'随机列1': '完全错误', '随机列2': '无法解析', '随机列3': 3, '空列': None}
                ]
            }],
            has_multiple_tables=False,
            selected_table_index=0,
            needs_llm_table_selection=False,
            
            # 解析相关状态 - 解析失败
            parsed_instruments=[],  # 解析失败，没有仪表数据
            
            # 任务规划状态
            original_user_input=f"请分析 {test_file} 文件",
            planned_tasks=[
                {"type": "parse", "target": test_file},
                {"type": "stats", "target": "全部"},
                {"type": "reco", "target": "全部"}
            ],
            current_task_index=0,
            task_results=[],
            needs_user_task_confirmation=False,
            
            # 初始化其他必要字段
            classified_instruments=[],
            classification_confidence=0.0,
            needs_user_confirmation=False,
            instrument_statistics={},
            user_intent="parse",
            recommendation_target="全部",
            matched_standards=[],
            has_standards=False,
            invalid_types=[],
            available_types=[],
            needs_type_selection=False,
            user_approved_sensitive=False,
            installation_recommendations=[],
            final_report="",
            user_feedback="",
            error_reflection="",
            error_decision="",
            error_retry_count={},
            max_retries=2,
            retry_target_node="",
            skip_current_step=False,
            loop_count=0,
            max_loops=5,
            needs_file_processing=True,
            step_count=3
        )
        
        print(f"📁 测试文件路径: {state['excel_file_path']}")
        print(f"❌ 错误来源节点: {state['error_source_node']}")
        print(f"💬 错误信息: {state['error_context']}")
        print(f"📊 提取的表格数: {len(state['extracted_tables'])}")
        print(f"📋 解析的仪表数: {len(state['parsed_instruments'])}")
        print(f"🔢 当前重试次数: {state['error_retry_count'].get('parse_instrument_table', 0)}")
        
        print("\n🤖 启动LLM错误反思分析...")
        print("-" * 30)
        
        # 调用错误处理器进行LLM反思
        result_state = enhanced_error_handler(state)
        
        print("\n📊 LLM反思结果:")
        print("-" * 30)
        print(f"💭 反思内容: {result_state.get('error_reflection', '无反思内容')}")
        print(f"🎯 决策结果: {result_state.get('error_decision', '无决策')}")
        print(f"🔄 重试标志: {result_state.get('retry_target_node', '无')}")
        print(f"⏭️ 跳过标志: {result_state.get('skip_current_step', False)}")
        print(f"❌ 错误状态: {result_state.get('has_error', False)}")
        
        # 分析决策合理性
        decision = result_state.get('error_decision', 'unknown')
        print(f"\n📝 决策分析:")
        if decision == "retry":
            print("⚠️ LLM决定重试 - 可能合理，也许能通过参数调整解析成功")
        elif decision == "skip":
            print("✅ LLM决定跳过 - 合理，跳过当前解析尝试其他方式")
        elif decision == "terminate":
            print("✅ LLM决定终止 - 合理，数据格式完全错误无法继续")
        else:
            print(f"❓ 未知决策: {decision}")
        
        return result_state
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🗑️ 已清理测试文件: {test_file}")

if __name__ == "__main__":
    test_data_parsing_error() 