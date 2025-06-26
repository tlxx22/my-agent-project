#!/usr/bin/env python3
"""
错误反思测试 2: 文件格式错误
=====================================
测试场景：用户指定的文件不是Excel格式
错误节点：enter_upload_file
预期决策：terminate（格式错误无法处理）或 retry（用户可能输错文件名）
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.instrument_agent import InstrumentAgentState, enhanced_error_handler
from langchain_core.messages import HumanMessage

def create_test_txt_file():
    """创建一个测试用的txt文件"""
    test_file = "test_wrong_format.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("这是一个文本文件，不是Excel文件\n")
        f.write("仪表名称,类型,位号\n")
        f.write("热电偶,温度,TI-001\n")
    return test_file

def test_file_format_error():
    """测试文件格式错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 2: 文件格式错误")
    print("=" * 50)
    
    # 创建测试文件
    test_file = create_test_txt_file()
    print(f"📝 已创建测试文件: {test_file}")
    
    try:
        # 构造智能体状态 - 模拟文件格式错误的情况
        state = InstrumentAgentState(
            # 基础消息
            messages=[HumanMessage(content=f"请分析 {test_file} 文件")],
            
            # 错误相关状态
            has_error=True,
            error_context=f"文件格式必须是.xlsx或.xls，但提供的是: {test_file}",
            error_source_node="enter_upload_file",
            
            # 文件相关状态
            excel_file_path=test_file,
            file_valid=False,
            file_error_message=f"文件格式必须是.xlsx或.xls，但提供的是: {test_file}",
            
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
            print("⚠️ LLM决定重试 - 需要检查，格式错误重试意义不大")
        elif decision == "skip":
            print("❌ LLM决定跳过 - 不合理，格式错误无法跳过")
        elif decision == "terminate":
            print("✅ LLM决定终止 - 合理，格式错误无法处理")
        else:
            print(f"❓ 未知决策: {decision}")
        
        return result_state
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🗑️ 已清理测试文件: {test_file}")

if __name__ == "__main__":
    test_file_format_error() 