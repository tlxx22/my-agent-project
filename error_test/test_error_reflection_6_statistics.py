#!/usr/bin/env python3
"""
错误反思测试 6: 统计计算错误
=====================================
测试场景：仪表分类成功但统计计算失败
错误节点：summarize_statistics
预期决策：retry（重新计算）或 skip（使用简化统计）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def test_statistics_error():
    """测试统计计算错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 6: 统计计算错误")
    print("=" * 50)
    
    # 构造智能体状态 - 模拟统计计算失败的情况
    state = InstrumentAgentState(
        # 基础消息
        messages=[HumanMessage(content="请分析仪表数据并生成统计报告")],
        
        # 错误相关状态
        has_error=True,
        error_context="统计计算失败: 无法生成仪表统计信息，可能是数据格式异常或计算逻辑错误",
        error_source_node="summarize_statistics",
        
        # 文件相关状态
        excel_file_path="test_data.xlsx",
        file_valid=True,
        file_error_message="",
        
        # 表格相关状态
        extracted_tables=[{
            'name': 'Sheet1',
            'description': '包含仪表数据的表格',
            'sheet_name': 'Sheet1',
            'headers': ['仪表名称', '位号', '型号', '类型'],
            'keyword_row': 0,
            'data_dict': []
        }],
        has_multiple_tables=False,
        selected_table_index=0,
        needs_llm_table_selection=False,
        
        # 解析和分类成功
        parsed_instruments=[
            {'仪表名称': '温度变送器', '位号': 'TT-001', '型号': 'ABC-123', '类型': '温度'},
            {'仪表名称': '压力变送器', '位号': 'PT-002', '型号': 'DEF-456', '类型': '压力'},
            {'仪表名称': '流量计', '位号': 'FT-003', '型号': 'GHI-789', '类型': '流量'}
        ],
        classified_instruments=[
            {'仪表名称': '温度变送器', '位号': 'TT-001', '型号': 'ABC-123', '类型': '温度', '分类置信度': 0.9},
            {'仪表名称': '压力变送器', '位号': 'PT-002', '型号': 'DEF-456', '类型': '压力', '分类置信度': 0.8},
            {'仪表名称': '流量计', '位号': 'FT-003', '型号': 'GHI-789', '类型': '流量', '分类置信度': 0.7}
        ],
        classification_confidence=0.8,
        needs_user_confirmation=False,
        
        # 统计相关状态 - 统计失败
        instrument_statistics={},  # 统计失败，没有统计数据
        
        # 任务规划状态
        original_user_input="请分析仪表数据并生成统计报告",
        planned_tasks=[
            {"type": "parse", "target": "test_data.xlsx"},
            {"type": "stats", "target": "全部"},
            {"type": "reco", "target": "全部"}
        ],
        current_task_index=1,  # 当前在统计任务
        task_results=[{"type": "parse", "status": "success"}],
        needs_user_task_confirmation=False,
        
        # 初始化其他必要字段
        user_intent="stats",
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
        needs_file_processing=False,
        step_count=5
    )
    
    print(f"📁 测试文件路径: {state['excel_file_path']}")
    print(f"❌ 错误来源节点: {state['error_source_node']}")
    print(f"💬 错误信息: {state['error_context']}")
    print(f"📋 解析的仪表数: {len(state['parsed_instruments'])}")
    print(f"🏷️ 分类的仪表数: {len(state['classified_instruments'])}")
    print(f"📊 统计数据: {len(state['instrument_statistics'])}")
    print(f"🎯 当前任务: 统计分析")
    print(f"🔢 当前重试次数: {state['error_retry_count'].get('summarize_statistics', 0)}")
    
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
        print("✅ LLM决定重试 - 合理，统计计算错误通常可以通过重试解决")
    elif decision == "skip":
        print("✅ LLM决定跳过 - 合理，可以使用简化统计或跳过统计继续推荐")
    elif decision == "terminate":
        print("⚠️ LLM决定终止 - 可能过于严格，统计失败不一定影响推荐功能")
    else:
        print(f"❓ 未知决策: {decision}")
    
    return result_state

if __name__ == "__main__":
    test_statistics_error() 