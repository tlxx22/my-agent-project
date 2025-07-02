#!/usr/bin/env python3
"""
智能体交互式体验
"""

import logging
import sys
from pathlib import Path
from langchain_core.messages import HumanMessage

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入智能体
from agents.instrument_agent import create_instrument_agent

# 节点名称中英文映射
NODE_NAME_MAP = {
    "fetch_user_context": "获取用户上下文",
    "llm_task_planner": "智能任务规划",
    "ask_user_confirm_tasks": "显示任务规划",
    "task_router": "任务路由",
    "enter_upload_file": "文件上传验证",
    "error_no_file_or_format": "文件错误处理",
    "extract_excel_tables": "提取Excel表格",
    "clarify_table_choice": "表格选择确认",
    "parse_instrument_table": "解析仪表数据",
    "classify_instrument_type": "智能仪表分类",
    "ask_user_confirm_type": "分类结果确认",
    "summarize_statistics": "统计数据汇总",
    "validate_recommendation_types": "验证推荐类型",
    "ask_user_select_type": "类型选择确认",
    "check_user_intent": "分析用户意图",
    "respond_statistics": "生成统计报告",
    "display_existing_statistics": "显示统计结果",  # stats任务专用
    "match_standard_clause": "匹配安装标准",
    "standards_gateway": "标准检查网关",
    "respond_stats_with_note": "生成统计说明",
    "ask_user_approval": "请求工具授权",
    "spec_sensitive_tools": "执行专业分析",
    "skip_sensitive_and_go_on": "跳过专业分析",
    "generate_installation_reco": "生成安装推荐",
    "respond_full_report": "生成完整报告",
    "feedback_loop_gateway": "反馈循环处理",
    "advance_task_index": "推进任务进度",
    "error_handler": "错误处理",
    "__start__": "开始",
    "__end__": "结束",
    "__interrupt__": "等待用户输入"
}

def get_chinese_node_name(node_name):
    """获取节点的中文名称"""
    return NODE_NAME_MAP.get(node_name, node_name)

# 配置日志 - 设置为WARNING级别以减少输出噪音
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def interactive_experience():
    """交互式体验智能体"""
    
    print("🎉 欢迎使用仪表分析智能体交互式体验")
    print("=" * 60)
    print("💡 您可以输入以下类型的指令:")
    print("   • 我要分析仪表，给我统计数据和安装建议")
    print("   • 给我仪表统计数据")
    print("   • 给我安装推荐")
    print("   • 分析仪表数据")
    print("   • quit 或 exit 退出")
    print("=" * 60)
    
    # 创建智能体
    print("🔧 正在初始化智能体...")
    try:
        agent = create_instrument_agent()
        print("✅ 智能体初始化成功！")
    except Exception as e:
        print(f"❌ 智能体初始化失败: {e}")
        return
    
    # 交互循环
    session_id = 1
    
    while True:
        print(f"\n💬 会话 {session_id}")
        print("-" * 30)
        
        # 获取用户输入
        try:
            user_input = input("👤 请输入您的指令: ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 感谢使用！再见！")
            break
        
        # 检查退出指令
        if user_input.lower() in ['quit', 'exit', '退出', '结束']:
            print("👋 感谢使用！再见！")
            break
        
        if not user_input:
            print("⚠️ 请输入有效指令")
            continue
        
        print(f"🚀 智能体正在处理: '{user_input}'")
        print("-" * 50)
        
        try:
            # 初始状态
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "current_task_index": 0,
                "loop_count": 0,
                "max_loops": 3
            }
            
            # 配置 - 增加递归限制
            config = {
                "configurable": {"thread_id": f"session_{session_id}"},
                "recursion_limit": 50  # 增加递归限制以支持复杂的多任务流程
            }
            
            # 执行处理
            step_count = 0
            results = []
            
            print("🔄 执行过程:")
            
            # 执行直到中断或完成 - 步骤显示由智能体节点负责
            for chunk in agent.stream(initial_state, config):
                for node_name, node_data in chunk.items():
                    # 跳过中断显示，步骤由节点内部显示
                    if node_name == "__interrupt__":
                        continue
                    
                    # 提取关键信息
                    if node_name == "respond_statistics" and "instrument_statistics" in node_data:
                        results.append(("统计数据", node_data.get("instrument_statistics")))
                    elif node_name == "respond_full_report" and "final_report" in node_data:
                        results.append(("完整报告", node_data.get("final_report")))
                    elif node_name == "respond_stats_with_note" and "final_report" in node_data:
                        results.append(("统计报告", node_data.get("final_report")))
                
                # 防止过长流程
                if step_count > 50:
                    print("  ⚠️ 步骤过多，自动停止")
                    break
            
            # 处理中断
            while True:
                current_state = agent.get_state(config)
                next_nodes = current_state.next
                
                if not next_nodes:
                    # 流程完成
                    break
                
                # 中断节点的步骤显示由智能体节点负责
                
                # 为中断节点显示步骤（在用户交互之前）
                for node_name in next_nodes:
                    step_count = current_state.values.get("step_count", 0) + 1
                    chinese_name = get_chinese_node_name(node_name)
                    print(f"  ⚡ 步骤 {step_count}: {chinese_name}")
                
                # 处理不同类型的中断
                if "ask_user_confirm_tasks" in next_nodes:
                    print(f"\n📋 任务规划:")
                    planned_tasks = current_state.values.get("planned_tasks", [])
                    print(f"系统已规划 {len(planned_tasks)} 个任务:")
                    for i, task in enumerate(planned_tasks, 1):
                        print(f"  {i}. {task.get('type')} - {task.get('target')}")
                    
                    confirm_input = input("👤 是否确认这个任务规划? (确认/修改): ").strip()
                    
                elif "clarify_table_choice" in next_nodes:
                    print(f"\n📊 表格选择:")
                    tables = current_state.values.get("extracted_tables", [])
                    print("发现多个表格，请选择要分析的表格:")
                    for i, table in enumerate(tables, 1):
                        name = table.get('name', f'表格{i}')
                        rows = len(table.get('data_dict', []))
                        desc = f"包含{rows}行数据的仪表表格"
                        print(f"  {i}. {name} ({rows}行) - {desc}")
                    
                    confirm_input = input("👤 请选择表格编号 (例如: 选择第2个表格): ").strip()
                    
                elif "ask_user_confirm_type" in next_nodes:
                    print(f"\n🏷️ 分类结果确认:")
                    classified = current_state.values.get("classified_instruments", [])
                    confidence = current_state.values.get("classification_confidence", 0.0)
                    print(f"系统分类了 {len(classified)} 个仪表，平均置信度: {confidence:.2f}")
                    
                    # 显示前5个分类结果
                    print("分类结果预览:")
                    for i, inst in enumerate(classified[:5], 1):
                        model = inst.get('型号', '未知')
                        inst_type = inst.get('类型', '未知')
                        conf = inst.get('置信度', 0)
                        print(f"  {i}. {model} -> {inst_type} (置信度: {conf:.2f})")
                    
                    if len(classified) > 5:
                        print(f"  ... 还有 {len(classified)-5} 个仪表")
                    
                    confirm_input = input("👤 分类结果是否正确? (确认/修改): ").strip()
                    
                elif "ask_user_select_type" in next_nodes:
                    print(f"\n🔄 类型选择:")
                    invalid_types = current_state.values.get("invalid_types", [])
                    available_types = current_state.values.get("available_types", [])
                    
                    print(f"⚠️ 检测到不存在的仪表类型: {', '.join(invalid_types)}")
                    print(f"\n📋 表格中可用的类型:")
                    for i, atype in enumerate(available_types, 1):
                        print(f"  {i}. {atype}")
                    
                    print(f"\n💡 您可以:")
                    print(f"   • 选择特定类型：例如 '温度仪表' 或 '压力仪表'")
                    print(f"   • 选择多个类型：例如 '温度仪表和压力仪表'")
                    print(f"   • 选择全部：例如 '全部' 或 '所有类型'")
                    
                    confirm_input = input("👤 请重新选择有效的仪表类型: ").strip()
                    
                elif "ask_user_approval" in next_nodes:
                    print(f"\n🔐 敏感工具授权:")
                    standards = current_state.values.get("matched_standards", [])
                    print(f"系统将使用敏感工具处理 {len(standards)} 条安装标准来生成推荐")
                    print()
                    print("💡 什么是'敏感工具'？")
                    print("   这些是需要特殊权限的高级处理工具，包括:")               
                    print("   🤖 LLM增强分析工具 - 使用大模型生成专业建议")
                    print("   📊 智能匹配算法 - 深度分析仪表规格与标准匹配")
                    print("   🔧 专业推荐引擎 - 基于行业标准的智能推荐系统")
                    print()
                    print("⚡ 为什么需要授权？")
                    print("   • 确保数据安全和处理透明度")
                    print("   • 让您了解系统将进行的高级处理")
                    print("   • 控制LLM调用成本")
                    
                    confirm_input = input("👤 是否授权使用这些高级工具? (同意/拒绝): ").strip()
                    
                else:
                    print(f"\n⚠️ 未知中断类型: {next_nodes}")
                    confirm_input = input("👤 请输入指令继续: ").strip()
                
                # 继续执行
                if confirm_input:
                    current_values = current_state.values
                    updated_state = {
                        **current_values,
                        "messages": current_values.get("messages", []) + [
                            HumanMessage(content=confirm_input)
                        ]
                    }
                    agent.update_state(config, updated_state)
                
                # 继续执行直到下一个中断或完成 - 步骤显示由节点负责
                print(f"\n🔄 继续执行...")
                for chunk in agent.stream(None, config):
                    for node_name, node_data in chunk.items():
                        # 跳过中断显示和已经显示过的中断节点
                        if node_name == "__interrupt__" or node_name in next_nodes:
                            continue
                        
                        # 提取关键信息
                        if node_name == "respond_statistics" and "instrument_statistics" in node_data:
                            results.append(("统计数据", node_data.get("instrument_statistics")))
                        elif node_name == "respond_full_report" and "final_report" in node_data:
                            results.append(("完整报告", node_data.get("final_report")))
                        elif node_name == "respond_stats_with_note" and "final_report" in node_data:
                            results.append(("统计报告", node_data.get("final_report")))
                    
                    # 防止过长流程
                    if step_count > 100:
                        print("  ⚠️ 步骤过多，自动停止")
                        break
            
            # 获取最终状态
            final_state = agent.get_state(config)
            
            # 显示结果
            print("\n📊 处理结果:")
            print("=" * 50)
            
            # 显示任务信息
            planned_tasks = final_state.values.get("planned_tasks", [])
            completed_tasks = final_state.values.get("current_task_index", 0)
            
            if planned_tasks:
                print(f"📋 任务规划: {len(planned_tasks)} 个任务")
                for i, task in enumerate(planned_tasks, 1):
                    status = "✅" if i <= completed_tasks else "⏳"
                    print(f"   {status} 任务{i}: {task.get('type')} - {task.get('target')}")
            
            stats = final_state.values.get("instrument_statistics")
            if stats:
                print(f"\n📈 统计结果:")
                print(f"   总仪表条目: {stats.get('总数量', '未知')} 条")
                print(f"   总台数: {stats.get('总台数', '未知')} 台")
                type_distribution = stats.get('类型统计', {})
                print(f"   仪表类型: {len(type_distribution)} 种")
                print(f"   不同型号: {stats.get('不同型号数', '未知')} 种")
                
                # 显示只有位号无型号的统计
                no_model_count = stats.get('只有位号无型号', 0)
                if no_model_count > 0:
                    print(f"   只有位号无型号: {no_model_count} 台")
                
                if type_distribution:
                    print("   类型分布:")
                    # 按数量排序显示
                    sorted_types = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)
                    total_count = stats.get('总台数', 1)
                    for type_name, count in sorted_types:
                        # 显示所有类型，包括"无法识别"
                        percentage = (count / total_count) * 100
                        print(f"     • {type_name}: {count} 台 ({percentage:.1f}%)")
            
            recommendations = final_state.values.get("installation_recommendations")
            if recommendations:
                print(f"\n🔧 安装推荐: ({len(recommendations)} 种型号)")
                for i, rec in enumerate(recommendations[:5], 1):  # 显示前5个推荐
                    type_name = rec.get('仪表类型', '未知')
                    model_name = rec.get('型号', '未知型号')
                    quantity = rec.get('数量', 0)
                    print(f"   {i}. {type_name} - {model_name}: {quantity} 台")
                    if len(rec.get('推荐内容', '')) > 150:
                        print(f"      {rec.get('推荐内容', '')[:150]}...")
                    else:
                        print(f"      {rec.get('推荐内容', '')}")
                    print()  # 空行分隔
            
            final_report = final_state.values.get("final_report")
            if final_report and not stats and not recommendations:
                print(f"📄 报告:")
                if len(final_report) > 200:
                    print(f"   {final_report[:200]}...")
                else:
                    print(f"   {final_report}")
            
            # 获取智能体内部的真实步骤计数
            actual_step_count = final_state.values.get("step_count", 0)
            print(f"\n✅ 处理完成 (共 {actual_step_count} 步)")
            
        except Exception as e:
            print(f"❌ 处理异常: {e}")
            print("💡 请尝试其他指令或检查输入格式")
        
        session_id += 1
        
        # 询问是否继续
        print("\n" + "=" * 60)
        continue_choice = input("🔄 是否继续体验? (y/N): ").strip().lower()
        if continue_choice not in ['y', 'yes', '是', '继续']:
            print("👋 感谢使用！再见！")
            break

if __name__ == "__main__":
    interactive_experience() 