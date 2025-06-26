#!/usr/bin/env python3
"""
错误反思测试 3: 表格提取失败
=====================================
测试场景：Excel文件损坏或无法读取
错误节点：extract_excel_tables
预期决策：retry（可能是临时读取问题）或 terminate（文件确实损坏）
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

def create_corrupted_excel_file():
    """创建一个损坏的Excel文件"""
    test_file = "test_corrupted.xlsx"
    # 创建一个看起来像Excel但实际上是损坏的文件
    with open(test_file, 'wb') as f:
        f.write(b"PK\x03\x04CORRUPTED_EXCEL_FILE_CONTENT")
    return test_file

def test_table_extraction_error():
    """测试表格提取失败的LLM反思和决策"""
    
    print("🧪 错误反思测试 3: 表格提取失败")
    print("=" * 50)
    
    # 创建损坏的测试文件
    test_file = create_corrupted_excel_file()
    print(f"💥 已创建损坏的Excel文件: {test_file}")
    
    try:
        # 构造智能体状态 - 模拟表格提取失败的情况
        state = InstrumentAgentState(
            # 基础消息
            messages=[HumanMessage(content=f"请分析 {test_file} 文件")],
            
            # 错误相关状态
            has_error=True,
            error_context=f"表格提取失败: 无法读取Excel文件 {test_file}，文件可能已损坏",
            error_source_node="extract_excel_tables",
            
            # 文件相关状态
            excel_file_path=test_file,
            file_valid=True,  # 文件存在且格式正确，但内容损坏
            file_error_message="",
            
            # 表格相关状态
            extracted_tables=[],  # 提取失败，没有表格
            has_multiple_tables=False,
            selected_table_index=0,
            needs_llm_table_selection=False,
            
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
            parsed_instruments=[],
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
            error_retry_count={"extract_excel_tables": 1},  # 已经重试过一次
            max_retries=2,
            retry_target_node="",
            skip_current_step=False,
            loop_count=0,
            max_loops=5,
            needs_file_processing=True,
            step_count=2
        )
        
        print(f"📁 测试文件路径: {state['excel_file_path']}")
        print(f"❌ 错误来源节点: {state['error_source_node']}")
        print(f"💬 错误信息: {state['error_context']}")
        print(f"🔢 当前重试次数: {state['error_retry_count'].get('extract_excel_tables', 0)}")
        
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
            retry_count = state['error_retry_count'].get('extract_excel_tables', 0)
            if retry_count < state['max_retries']:
                print("✅ LLM决定重试 - 合理，可能是临时读取问题")
            else:
                print("⚠️ LLM决定重试 - 但已达重试上限，应该考虑其他选择")
        elif decision == "skip":
            print("⚠️ LLM决定跳过 - 风险较高，跳过表格提取可能导致后续失败")
        elif decision == "terminate":
            print("✅ LLM决定终止 - 合理，文件损坏无法继续")
        else:
            print(f"❓ 未知决策: {decision}")
        
        return result_state
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🗑️ 已清理测试文件: {test_file}")

if __name__ == "__main__":
    test_table_extraction_error() 