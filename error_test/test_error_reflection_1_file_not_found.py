#!/usr/bin/env python3
"""
错误反思测试 1: 文件不存在错误
=====================================
测试场景：用户指定的Excel文件不存在
错误节点：enter_upload_file
预期决策：retry（可能是路径错误）或 terminate（文件确实不存在）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def test_file_not_found_error():
    """测试文件不存在错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 1: 文件不存在错误")
    print("=" * 50)
    
    # 构造智能体状态 - 模拟文件不存在的情况
    state = InstrumentAgentState(
        # 基础消息
        messages=[HumanMessage(content="请分析 /path/to/nonexistent/file.xlsx 文件")],
        
        # 错误相关状态
        has_error=True,
        error_context="文件不存在: /path/to/nonexistent/file.xlsx",
        error_source_node="enter_upload_file",
        
        # 文件相关状态
        excel_file_path="/path/to/nonexistent/file.xlsx",
        file_valid=False,
        file_error_message="文件不存在: /path/to/nonexistent/file.xlsx",
        
        # 任务规划状态
        original_user_input="请分析 /path/to/nonexistent/file.xlsx 文件",
        planned_tasks=[
            {"type": "parse", "target": "/path/to/nonexistent/file.xlsx"},
            {"type": "stats", "target": "全部"},
            {"type": "reco", "target": "全部"}
        ],
        current_task_index=0,
        task_results=[],
        needs_user_task_confirmation=False,
        
        # 初始化其他必要字段
        extracted_tables=[],
        has_multiple_tables=False,
        selected_table_index=0,
        needs_llm_table_selection=False,
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
        error_retry_count={},
        max_retries=2,
        retry_target_node="",
        skip_current_step=False,
        loop_count=0,
        max_loops=5,
        needs_file_processing=True,
        step_count=0
    )
    
    print(f"📁 测试文件路径: {state['excel_file_path']}")
    print(f"❌ 错误来源节点: {state['error_source_node']}")
    print(f"💬 错误信息: {state['error_context']}")
    print(f"🔢 当前重试次数: {state['error_retry_count'].get('enter_upload_file', 0)}")
    
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
        print("✅ LLM决定重试 - 合理，可能是临时路径问题")
    elif decision == "skip":
        print("⚠️ LLM决定跳过 - 需要检查，文件错误通常不应跳过")
    elif decision == "terminate":
        print("🛑 LLM决定终止 - 合理，文件不存在无法继续")
    else:
        print(f"❓ 未知决策: {decision}")
    
    return result_state

if __name__ == "__main__":
    test_file_not_found_error() 