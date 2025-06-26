#!/usr/bin/env python3
"""
错误反思测试 8: 推荐生成错误
=====================================
测试场景：LLM推荐生成失败
错误节点：generate_installation_reco
预期决策：retry（重新生成）或 skip（使用模板推荐）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def test_recommendation_generation_error():
    """测试推荐生成错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 8: 推荐生成错误")
    print("=" * 50)
    
    # 构造智能体状态 - 模拟推荐生成失败的情况
    state = InstrumentAgentState(
        # 基础消息
        messages=[HumanMessage(content="请生成详细的安装推荐报告")],
        
        # 错误相关状态
        has_error=True,
        error_context="推荐生成失败: LLM无法生成安装推荐，可能是API限制、token超限或模型错误",
        error_source_node="generate_installation_reco",
        
        # 文件相关状态
        excel_file_path="complex_instruments.xlsx",
        file_valid=True,
        file_error_message="",
        
        # 完整的处理链 - 所有前面步骤都成功
        extracted_tables=[{
            'name': 'Sheet1',
            'description': '包含复杂仪表数据的表格',
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
            {'仪表名称': '流量计', '位号': 'FT-003', '型号': 'GHI-789', '类型': '流量'},
            {'仪表名称': '液位计', '位号': 'LT-004', '型号': 'JKL-012', '类型': '液位'}
        ],
        classified_instruments=[
            {'仪表名称': '温度变送器', '位号': 'TT-001', '型号': 'ABC-123', '类型': '温度', '分类置信度': 0.9},
            {'仪表名称': '压力变送器', '位号': 'PT-002', '型号': 'DEF-456', '类型': '压力', '分类置信度': 0.8},
            {'仪表名称': '流量计', '位号': 'FT-003', '型号': 'GHI-789', '类型': '流量', '分类置信度': 0.85},
            {'仪表名称': '液位计', '位号': 'LT-004', '型号': 'JKL-012', '类型': '液位', '分类置信度': 0.75}
        ],
        classification_confidence=0.82,
        needs_user_confirmation=False,
        
        # 统计成功
        instrument_statistics={
            "总计": 4,
            "类型分布": {
                "温度": 1,
                "压力": 1,
                "流量": 1,
                "液位": 1
            },
            "平均置信度": 0.82
        },
        
        # 标准匹配成功
        matched_standards=[
            {"type": "温度", "standards": ["温度仪表安装规范第3.1条", "温度仪表接线规范第2.4条"]},
            {"type": "压力", "standards": ["压力仪表安装规范第4.2条", "压力仪表校准规范第1.3条"]},
            {"type": "流量", "standards": ["流量仪表安装规范第5.1条", "流量仪表维护规范第2.1条"]},
            {"type": "液位", "standards": ["液位仪表安装规范第6.3条", "液位仪表测试规范第3.2条"]}
        ],
        has_standards=True,
        
        # 授权成功
        user_approved_sensitive=True,
        
        # 推荐生成失败
        installation_recommendations=[],  # 生成失败，没有推荐内容
        
        # 任务规划状态
        original_user_input="请生成详细的安装推荐报告",
        planned_tasks=[
            {"type": "parse", "target": "complex_instruments.xlsx"},
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
        available_types=["温度", "压力", "流量", "液位"],
        needs_type_selection=False,
        final_report="",
        user_feedback="",
        error_reflection="",
        error_decision="",
        error_retry_count={"generate_installation_reco": 1},  # 已经重试过一次
        max_retries=2,
        retry_target_node="",
        skip_current_step=False,
        loop_count=0,
        max_loops=5,
        needs_file_processing=False,
        step_count=7
    )
    
    print(f"📁 测试文件路径: {state['excel_file_path']}")
    print(f"❌ 错误来源节点: {state['error_source_node']}")
    print(f"💬 错误信息: {state['error_context']}")
    print(f"🏷️ 分类的仪表数: {len(state['classified_instruments'])}")
    print(f"📊 统计数据: {state['instrument_statistics'].get('总计', 0)}")
    print(f"📋 匹配的标准数: {len(state['matched_standards'])}")
    print(f"📝 生成的推荐数: {len(state['installation_recommendations'])}")
    print(f"✅ 用户授权状态: {state['user_approved_sensitive']}")
    print(f"🎯 当前任务: 安装推荐生成")
    print(f"🔢 当前重试次数: {state['error_retry_count'].get('generate_installation_reco', 0)}")
    
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
        retry_count = state['error_retry_count'].get('generate_installation_reco', 0)
        if retry_count < state['max_retries']:
            print("✅ LLM决定重试 - 合理，推荐生成失败可能是临时问题")
        else:
            print("⚠️ LLM决定重试 - 但已达重试上限，应考虑备用方案")
    elif decision == "skip":
        print("✅ LLM决定跳过 - 合理，可以使用模板推荐或简化推荐")
    elif decision == "terminate":
        print("⚠️ LLM决定终止 - 可能过于严格，推荐生成失败不一定要终止")
    else:
        print(f"❓ 未知决策: {decision}")
    
    return result_state

if __name__ == "__main__":
    test_recommendation_generation_error() 