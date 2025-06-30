#!/usr/bin/env python3
"""
错误反思测试 7: 标准匹配失败
=====================================
测试场景：无法找到匹配的安装标准
错误节点：match_standard_clause
预期决策：skip（使用通用标准）或 retry（调整匹配参数）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def test_standards_matching_error():
    """测试标准匹配失败的LLM反思和决策"""
    
    print("🧪 错误反思测试 7: 标准匹配失败")
    print("=" * 50)
    
    # 构造智能体状态 - 模拟标准匹配失败的情况
    state = InstrumentAgentState(
        # 基础消息
        messages=[HumanMessage(content="请为特殊仪表生成安装推荐")],
        
        # 错误相关状态
        has_error=True,
        error_context="标准匹配失败: 无法为特殊仪表类型找到匹配的安装标准，标准库中可能缺少相关规范",
        error_source_node="match_standard_clause",
        
        # 文件相关状态
        excel_file_path="special_instruments.xlsx",
        file_valid=True,
        file_error_message="",
        
        # 完整的处理链 - 前面步骤都成功
        extracted_tables=[{
            'name': 'Sheet1',
            'description': '包含特殊仪表数据的表格',
            'sheet_name': 'Sheet1',
            'headers': ['仪表名称', '位号', '型号', '类型'],
            'keyword_row': 0,
            'data_dict': []
        }],
        has_multiple_tables=False,
        selected_table_index=0,
        needs_llm_table_selection=False,
        
        # 解析和分类成功，但是特殊类型
        parsed_instruments=[
            {'仪表名称': '量子传感器', '位号': 'QT-001', '型号': 'QUANTUM-X1', '类型': '量子测量'},
            {'仪表名称': '等离子探测器', '位号': 'PT-002', '型号': 'PLASMA-Y2', '类型': '等离子检测'},
            {'仪表名称': '超声波阵列', '位号': 'UT-003', '型号': 'ULTRA-Z3', '类型': '超声检测'}
        ],
        classified_instruments=[
            {'仪表名称': '量子传感器', '位号': 'QT-001', '型号': 'QUANTUM-X1', '类型': '量子测量', '分类置信度': 0.6},
            {'仪表名称': '等离子探测器', '位号': 'PT-002', '型号': 'PLASMA-Y2', '类型': '等离子检测', '分类置信度': 0.5},
            {'仪表名称': '超声波阵列', '位号': 'UT-003', '型号': 'ULTRA-Z3', '类型': '超声检测', '分类置信度': 0.7}
        ],
        classification_confidence=0.6,
        needs_user_confirmation=False,
        
        # 统计成功
        instrument_statistics={
            "总计": 3,
            "类型分布": {
                "量子测量": 1,
                "等离子检测": 1,
                "超声检测": 1
            },
            "置信度": 0.6
        },
        
        # 标准匹配失败
        matched_standards=[],  # 没有找到匹配的标准
        has_standards=False,
        
        # 任务规划状态
        original_user_input="请为特殊仪表生成安装推荐",
        planned_tasks=[
            {"type": "parse", "target": "special_instruments.xlsx"},
            {"type": "stats", "target": "全部"},
            {"type": "reco", "target": "全部"}
        ],
        current_task_index=2,  # 当前在推荐任务
        task_results=[
            {"type": "parse", "status": "success"},
            {"type": "stats", "status": "success"}
        ],
        needs_user_task_confirmation=False,
        
        # 初始化其他必要字段
        user_intent="reco",
        recommendation_target="全部",
        invalid_types=[],
        available_types=["温度", "压力", "流量", "液位"],  # 标准类型，不包含特殊类型
        needs_type_selection=False,
        user_approved_sensitive=False,
        installation_recommendations=[],
        final_report="",
        user_feedback="",
        error_reflection="",
        error_decision="",
        error_retry_count={"match_standard_clause": 1},
        max_retries=2,
        retry_target_node="",
        skip_current_step=False,
        loop_count=0,
        max_loops=5,
        needs_file_processing=False,
        step_count=6
    )
    
    print(f"📁 测试文件路径: {state['excel_file_path']}")
    print(f"❌ 错误来源节点: {state['error_source_node']}")
    print(f"💬 错误信息: {state['error_context']}")
    print(f"🏷️ 分类的仪表数: {len(state['classified_instruments'])}")
    print(f"📊 统计数据: {state['instrument_statistics'].get('总计', 0)}")
    print(f"📋 匹配的标准数: {len(state['matched_standards'])}")
    print(f"🎯 当前任务: 安装推荐")
    print(f"🔢 当前重试次数: {state['error_retry_count'].get('match_standard_clause', 0)}")
    
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
        print("⚠️ LLM决定重试 - 需要检查，特殊类型重试可能仍然失败")
    elif decision == "skip":
        print("✅ LLM决定跳过 - 合理，可以使用通用标准或显示无标准提示")
    elif decision == "terminate":
        print("⚠️ LLM决定终止 - 可能过于严格，无标准不一定要终止")
    else:
        print(f"❓ 未知决策: {decision}")
    
    return result_state

if __name__ == "__main__":
    test_standards_matching_error() 