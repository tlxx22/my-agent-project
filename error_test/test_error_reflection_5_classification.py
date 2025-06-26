#!/usr/bin/env python3
"""
错误反思测试 5: 分类失败错误
=====================================
测试场景：仪表数据解析成功但分类失败
错误节点：classify_instrument_type
预期决策：retry（调整分类参数）或 skip（使用默认分类）
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

def create_valid_excel_file():
    """创建一个包含有效仪表数据但难以分类的Excel文件"""
    test_file = "test_classification_fail.xlsx"
    
    # 创建包含奇怪仪表名称的数据，难以分类
    df = pd.DataFrame({
        '仪表名称': ['神秘设备A', '未知传感器X', '特殊装置99', '不明仪表Z'],
        '位号': ['MI-001', 'XI-002', 'SI-099', 'ZI-999'],
        '型号': ['ABC-123-XYZ', 'DEF-456-UVW', 'GHI-789-RST', 'JKL-000-MNO'],
        '备注': ['功能不明', '用途待定', '类型未知', '分类困难']
    })
    
    df.to_excel(test_file, index=False)
    return test_file

def test_classification_error():
    """测试分类失败错误的LLM反思和决策"""
    
    print("🧪 错误反思测试 5: 分类失败错误")
    print("=" * 50)
    
    # 创建包含难以分类数据的测试文件
    test_file = create_valid_excel_file()
    print(f"🔍 已创建难以分类的Excel文件: {test_file}")
    
    try:
        # 构造智能体状态 - 模拟分类失败的情况
        state = InstrumentAgentState(
            # 基础消息
            messages=[HumanMessage(content=f"请分析 {test_file} 文件")],
            
            # 错误相关状态
            has_error=True,
            error_context="仪表分类失败: 无法识别仪表类型，可能是仪表名称不标准或类型定义缺失",
            error_source_node="classify_instrument_type",
            
            # 文件相关状态
            excel_file_path=test_file,
            file_valid=True,
            file_error_message="",
            
            # 表格相关状态
            extracted_tables=[{
                'name': 'Sheet1',
                'description': '包含难以分类仪表数据的表格',
                'sheet_name': 'Sheet1',
                'headers': ['仪表名称', '位号', '型号', '备注'],
                'keyword_row': 0,
                'data_dict': [
                    {'仪表名称': '神秘设备A', '位号': 'MI-001', '型号': 'ABC-123-XYZ', '备注': '功能不明'},
                    {'仪表名称': '未知传感器X', '位号': 'XI-002', '型号': 'DEF-456-UVW', '备注': '用途待定'},
                    {'仪表名称': '特殊装置99', '位号': 'SI-099', '型号': 'GHI-789-RST', '备注': '类型未知'},
                    {'仪表名称': '不明仪表Z', '位号': 'ZI-999', '型号': 'JKL-000-MNO', '备注': '分类困难'}
                ]
            }],
            has_multiple_tables=False,
            selected_table_index=0,
            needs_llm_table_selection=False,
            
            # 解析相关状态 - 解析成功
            parsed_instruments=[
                {'仪表名称': '神秘设备A', '位号': 'MI-001', '型号': 'ABC-123-XYZ', '备注': '功能不明'},
                {'仪表名称': '未知传感器X', '位号': 'XI-002', '型号': 'DEF-456-UVW', '备注': '用途待定'},
                {'仪表名称': '特殊装置99', '位号': 'SI-099', '型号': 'GHI-789-RST', '备注': '类型未知'},
                {'仪表名称': '不明仪表Z', '位号': 'ZI-999', '型号': 'JKL-000-MNO', '备注': '分类困难'}
            ],
            
            # 分类相关状态 - 分类失败
            classified_instruments=[],  # 分类失败，没有分类结果
            classification_confidence=0.1,  # 置信度很低
            needs_user_confirmation=True,
            
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
            error_retry_count={"classify_instrument_type": 1},  # 已经重试过一次
            max_retries=2,
            retry_target_node="",
            skip_current_step=False,
            loop_count=0,
            max_loops=5,
            needs_file_processing=True,
            step_count=4
        )
        
        print(f"📁 测试文件路径: {state['excel_file_path']}")
        print(f"❌ 错误来源节点: {state['error_source_node']}")
        print(f"💬 错误信息: {state['error_context']}")
        print(f"📋 解析的仪表数: {len(state['parsed_instruments'])}")
        print(f"🏷️ 分类的仪表数: {len(state['classified_instruments'])}")
        print(f"📊 分类置信度: {state['classification_confidence']}")
        print(f"🔢 当前重试次数: {state['error_retry_count'].get('classify_instrument_type', 0)}")
        
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
            retry_count = state['error_retry_count'].get('classify_instrument_type', 0)
            if retry_count < state['max_retries']:
                print("✅ LLM决定重试 - 合理，可以尝试调整分类参数或算法")
            else:
                print("⚠️ LLM决定重试 - 但已达重试上限，应考虑其他方案")
        elif decision == "skip":
            print("✅ LLM决定跳过 - 合理，可以使用默认分类继续流程")
        elif decision == "terminate":
            print("⚠️ LLM决定终止 - 可能过于严格，分类失败不一定要终止")
        else:
            print(f"❓ 未知决策: {decision}")
        
        return result_state
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\n🗑️ 已清理测试文件: {test_file}")

if __name__ == "__main__":
    test_classification_error() 