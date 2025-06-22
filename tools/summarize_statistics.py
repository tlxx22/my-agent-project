"""
仪表统计汇总工具
用于生成按型号归类的统计表
"""
import pandas as pd
from typing import Dict, List
import logging
from tools.classify_instrument_type import classify_instrument_type

logger = logging.getLogger(__name__)

def summarize_statistics(df: pd.DataFrame, use_llm_classification: bool = True) -> pd.DataFrame:
    """
    输入清洗后的DataFrame，输出按型号归类汇总的统计表
    
    Args:
        df: 清洗后的仪表DataFrame，包含字段：型号, 数量, 规格, 位号, 备注
        use_llm_classification: 是否使用LLM进行分类
    
    Returns:
        汇总统计DataFrame，字段包括：仪表类型, 型号, 数量总和, 规格汇总, 位号列表
    """
    if df.empty:
        logger.warning("输入DataFrame为空")
        return pd.DataFrame(columns=['仪表类型', '型号', '数量总和', '规格汇总', '位号列表'])
    
    # 确保必要的列存在
    required_columns = ['型号', '数量']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"DataFrame缺少必要的列: {col}")
    
    # 1. 获取唯一型号进行分类（避免重复分类）
    logger.info("开始对仪表型号进行分类...")
    
    # 获取唯一型号
    unique_models = df['型号'].dropna().unique()
    logger.info(f"发现 {len(unique_models)} 种唯一型号")
    
    # 为唯一型号构建上下文
    unique_contexts = []
    for model in unique_models:
        # 获取该型号的第一个记录的上下文信息
        model_rows = df[df['型号'] == model]
        first_row = model_rows.iloc[0]
        
        context_parts = []
        if '规格' in df.columns and pd.notna(first_row['规格']):
            context_parts.append(f"规格: {first_row['规格']}")
        if '备注' in df.columns and pd.notna(first_row['备注']):
            context_parts.append(f"备注: {first_row['备注']}")
        unique_contexts.append("; ".join(context_parts))
    
    # 逐个分类唯一型号
    unique_classifications = []
    for model, context in zip(unique_models, unique_contexts):
        classification = classify_instrument_type(
            model=model,
            spec="",
            context=context,
            row_index=-1,  # 不使用表格位置信息
            table_categories=None,  # 统计阶段不使用表格分类
        use_llm=use_llm_classification
    )
        unique_classifications.append(classification)
    
    # 创建型号到分类的映射
    model_to_type = dict(zip(unique_models, unique_classifications))
    
    # 将分类结果映射到完整DataFrame
    df_with_types = df.copy()
    df_with_types['仪表类型'] = df_with_types['型号'].map(model_to_type).fillna('未知')
    
    # 2. 按仪表类型和型号进行分组汇总
    logger.info("开始汇总统计...")
    
    # 准备汇总函数
    def aggregate_specs(specs):
        """汇总规格信息"""
        unique_specs = specs.dropna().unique()
        return "; ".join(unique_specs) if len(unique_specs) > 0 else ""
    
    def aggregate_tags(tags):
        """汇总位号信息"""
        unique_tags = tags.dropna().unique()
        return "; ".join(unique_tags) if len(unique_tags) > 0 else ""
    
    # 按仪表类型和型号分组
    groupby_columns = ['仪表类型', '型号']
    
    agg_dict = {
        '数量': 'sum',
    }
    
    # 添加可选列的聚合
    if '规格' in df_with_types.columns:
        agg_dict['规格'] = aggregate_specs
    if '位号' in df_with_types.columns:
        agg_dict['位号'] = aggregate_tags
    
    summary_df = df_with_types.groupby(groupby_columns).agg(agg_dict).reset_index()
    
    # 重命名列
    column_mapping = {
        '数量': '数量总和',
        '规格': '规格汇总',
        '位号': '位号列表'
    }
    summary_df = summary_df.rename(columns=column_mapping)
    
    # 确保所有必要的列都存在
    required_output_columns = ['仪表类型', '型号', '数量总和', '规格汇总', '位号列表']
    for col in required_output_columns:
        if col not in summary_df.columns:
            if col == '规格汇总':
                summary_df[col] = ""
            elif col == '位号列表':
                summary_df[col] = ""
    
    # 重新排列列的顺序
    summary_df = summary_df[required_output_columns]
    
    # 按仪表类型和数量排序
    summary_df = summary_df.sort_values(['仪表类型', '数量总和'], ascending=[True, False])
    
    # 重置索引
    summary_df = summary_df.reset_index(drop=True)
    
    logger.info(f"统计汇总完成，共 {len(summary_df)} 种仪表类型和型号组合")
    
    return summary_df

def generate_summary_report(summary_df: pd.DataFrame) -> str:
    """
    生成文字形式的汇总报告
    
    Args:
        summary_df: 汇总统计DataFrame
    
    Returns:
        格式化的汇总报告字符串
    """
    if summary_df.empty:
        return "没有找到有效的仪表数据。"
    
    report_lines = ["# 仪表清单统计汇总报告\n"]
    
    # 总体统计
    total_instruments = summary_df['数量总和'].sum()
    total_types = summary_df['仪表类型'].nunique()
    total_models = len(summary_df)
    
    report_lines.append(f"## 总体统计")
    report_lines.append(f"- 仪表总数量：{total_instruments} 台")
    report_lines.append(f"- 仪表类型数：{total_types} 种")
    report_lines.append(f"- 不同型号数：{total_models} 个\n")
    
    # 按类型分组统计
    type_summary = summary_df.groupby('仪表类型')['数量总和'].sum().sort_values(ascending=False)
    
    report_lines.append("## 按类型统计")
    for instrument_type, count in type_summary.items():
        percentage = (count / total_instruments) * 100
        report_lines.append(f"- {instrument_type}：{count} 台 ({percentage:.1f}%)")
    
    report_lines.append("")
    
    # 详细清单
    report_lines.append("## 详细清单")
    current_type = None
    
    for _, row in summary_df.iterrows():
        if row['仪表类型'] != current_type:
            current_type = row['仪表类型']
            report_lines.append(f"\n### {current_type}")
        
        line_parts = [f"- **{row['型号']}**：{row['数量总和']} 台"]
        
        if row['规格汇总'] and row['规格汇总'].strip():
            line_parts.append(f"规格：{row['规格汇总']}")
        
        if row['位号列表'] and row['位号列表'].strip():
            tags_count = len(row['位号列表'].split(';'))
            line_parts.append(f"位号：{tags_count}个")
        
        report_lines.append("  " + "，".join(line_parts))
    
    return "\n".join(report_lines)

def export_to_excel(summary_df: pd.DataFrame, output_path: str) -> bool:
    """
    导出汇总结果到Excel文件
    
    Args:
        summary_df: 汇总统计DataFrame
        output_path: 输出文件路径
    
    Returns:
        是否导出成功
    """
    try:
        # 创建Excel写入器
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 写入汇总数据
            summary_df.to_excel(writer, sheet_name='仪表统计汇总', index=False)
            
            # 如果有数据，添加透视表
            if not summary_df.empty:
                # 按类型汇总
                type_pivot = summary_df.groupby('仪表类型').agg({
                    '数量总和': 'sum',
                    '型号': 'count'
                }).rename(columns={'型号': '型号种类数'}).reset_index()
                
                type_pivot.to_excel(writer, sheet_name='按类型汇总', index=False)
        
        logger.info(f"成功导出汇总结果到: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"导出Excel文件失败: {str(e)}")
        return False

def get_summary_statistics(summary_df: pd.DataFrame) -> Dict:
    """
    获取汇总统计的数值信息
    
    Args:
        summary_df: 汇总统计DataFrame
    
    Returns:
        包含各种统计信息的字典
    """
    if summary_df.empty:
        return {
            'total_instruments': 0,
            'total_types': 0,
            'total_models': 0,
            'top_type': None,
            'top_type_count': 0,
            'type_distribution': {}
        }
    
    total_instruments = summary_df['数量总和'].sum()
    total_types = summary_df['仪表类型'].nunique()
    total_models = len(summary_df)
    
    # 按类型统计
    type_counts = summary_df.groupby('仪表类型')['数量总和'].sum().sort_values(ascending=False)
    top_type = type_counts.index[0] if not type_counts.empty else None
    top_type_count = type_counts.iloc[0] if not type_counts.empty else 0
    
    return {
        'total_instruments': int(total_instruments),
        'total_types': int(total_types),
        'total_models': int(total_models),
        'top_type': top_type,
        'top_type_count': int(top_type_count),
        'type_distribution': type_counts.to_dict()
    }

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '型号': ['WRN-630', 'WZP-230', 'Y-100', 'PT-3051', 'WRN-630'],
        '数量': [2, 1, 3, 1, 1],
        '规格': ['K型', 'PT100', '0-1.6MPa', '4-20mA', 'K型'],
        '位号': ['TE-001', 'TE-002', 'PI-001', 'PT-001', 'TE-003'],
        '备注': ['', '', '', '', '']
    })
    
    print("测试数据:")
    print(test_data)
    print("\n" + "="*50)
    
    # 测试汇总功能
    summary_result = summarize_statistics(test_data, use_llm_classification=False)
    print("汇总结果:")
    print(summary_result)
    print("\n" + "="*50)
    
    # 测试报告生成
    report = generate_summary_report(summary_result)
    print("汇总报告:")
    print(report)
    
    print("\n仪表统计汇总工具已就绪") 