"""
LangGraph标准工具定义
使用@tool装饰器定义所有工具函数
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from langchain_core.tools import tool
import logging

# 导入原有功能模块
from .extract_excel_tables import extract_excel_tables as _extract_excel_tables
from .parse_instrument_table import extract_instrument_info as _extract_instrument_info, validate_parsed_data
from .classify_instrument_type import batch_classify_instruments as _batch_classify_instruments
from .summarize_statistics import summarize_statistics as _summarize_statistics, generate_summary_report, get_summary_statistics
from .match_standard_clause import StandardClauseRetriever
from .generate_installation_recommendation import InstallationRecommendationGenerator

logger = logging.getLogger(__name__)

# 全局实例
_retriever = None
_recommendation_generator = None

def get_retriever():
    """获取检索器实例"""
    global _retriever
    if _retriever is None:
        _retriever = StandardClauseRetriever()
    return _retriever

def get_recommendation_generator():
    """获取推荐生成器实例"""
    global _recommendation_generator
    if _recommendation_generator is None:
        _recommendation_generator = InstallationRecommendationGenerator()
    return _recommendation_generator

@tool
def extract_excel_tables(file_path: str, keyword: str = "仪表清单") -> Dict[str, Any]:
    """
    从Excel文件中提取包含指定关键字的表格数据
    
    Args:
        file_path: Excel文件路径
        keyword: 识别关键字，默认为"仪表清单"
    
    Returns:
        包含提取结果的字典：{"success": bool, "tables": List[Dict], "message": str}
    """
    try:
        tables = _extract_excel_tables(file_path, keyword)
        
        if not tables:
            # 尝试其他关键字
            for alt_keyword in ["仪表", "设备清单", "材料表"]:
                tables = _extract_excel_tables(file_path, alt_keyword)
                if tables:
                    break
        
        if tables:
            return {
                "success": True,
                "tables": tables,
                "message": f"成功提取 {len(tables)} 个表格"
            }
        else:
            return {
                "success": False,
                "tables": [],
                "message": "未在Excel文件中找到仪表相关表格"
            }
            
    except Exception as e:
        logger.error(f"提取表格失败: {str(e)}")
        return {
            "success": False,
            "tables": [],
            "message": f"提取表格失败: {str(e)}"
        }

@tool
def parse_instrument_table(table_data: Dict) -> Dict[str, Any]:
    """
    解析仪表表格数据，提取型号、数量等信息
    
    Args:
        table_data: 表格数据字典，包含data字段（pandas DataFrame）
    
    Returns:
        解析结果字典：{"success": bool, "parsed_data": Dict, "message": str}
    """
    try:
        if "data" not in table_data:
            raise ValueError("表格数据中缺少data字段")
        
        df = table_data["data"]
        
        # 解析仪表信息
        parsed_df = _extract_instrument_info(df)
        
        # 验证解析结果
        if not validate_parsed_data(parsed_df):
            raise ValueError("解析的数据无效")
        
        # 转换为字典格式以便序列化
        parsed_data = {
            "columns": list(parsed_df.columns),
            "data": parsed_df.to_dict('records'),
            "row_count": len(parsed_df)
        }
        
        return {
            "success": True,
            "parsed_data": parsed_data,
            "message": f"成功解析 {len(parsed_df)} 行仪表数据"
        }
        
    except Exception as e:
        logger.error(f"解析表格失败: {str(e)}")
        return {
            "success": False,
            "parsed_data": None,
            "message": f"解析表格失败: {str(e)}"
        }

@tool
def classify_instrument_types(parsed_data: Dict, use_llm: bool = True) -> Dict[str, Any]:
    """
    对仪表进行类型分类
    
    Args:
        parsed_data: 解析后的数据字典
        use_llm: 是否使用LLM进行分类
    
    Returns:
        分类结果字典：{"success": bool, "classified_data": Dict, "message": str}
    """
    try:
        if not parsed_data or "data" not in parsed_data:
            raise ValueError("无效的解析数据")
        
        # 重建DataFrame
        df = pd.DataFrame(parsed_data["data"])
        
        # 提取型号和上下文
        models = df['型号'].tolist()
        contexts = []
        
        for _, row in df.iterrows():
            context_parts = []
            if '规格' in df.columns and str(row['规格']).strip():
                context_parts.append(f"规格: {row['规格']}")
            if '备注' in df.columns and str(row['备注']).strip():
                context_parts.append(f"备注: {row['备注']}")
            contexts.append("; ".join(context_parts))
        
        # 进行分类
        instrument_types = _batch_classify_instruments(models, contexts, use_llm=use_llm)
        
        # 添加分类结果
        df['仪表类型'] = instrument_types
        
        # 转换为字典格式
        classified_data = {
            "columns": list(df.columns),
            "data": df.to_dict('records'),
            "row_count": len(df)
        }
        
        return {
            "success": True,
            "classified_data": classified_data,
            "message": f"成功分类 {len(df)} 个仪表"
        }
        
    except Exception as e:
        logger.error(f"分类仪表类型失败: {str(e)}")
        return {
            "success": False,
            "classified_data": None,
            "message": f"分类仪表类型失败: {str(e)}"
        }

@tool
def summarize_instrument_statistics(classified_data: Dict) -> Dict[str, Any]:
    """
    生成仪表统计汇总
    
    Args:
        classified_data: 分类后的数据字典
    
    Returns:
        统计结果字典：{"success": bool, "summary_data": Dict, "statistics_info": Dict, "message": str}
    """
    try:
        if not classified_data or "data" not in classified_data:
            raise ValueError("无效的分类数据")
        
        # 重建DataFrame
        df = pd.DataFrame(classified_data["data"])
        
        # 生成统计汇总
        summary_df = _summarize_statistics(df, use_llm_classification=False)
        
        # 获取统计信息
        stats_info = get_summary_statistics(summary_df)
        
        # 转换为字典格式
        summary_data = {
            "columns": list(summary_df.columns),
            "data": summary_df.to_dict('records'),
            "row_count": len(summary_df)
        }
        
        return {
            "success": True,
            "summary_data": summary_data,
            "statistics_info": stats_info,
            "message": f"统计汇总完成，共 {stats_info['total_instruments']} 台仪表"
        }
        
    except Exception as e:
        logger.error(f"统计汇总失败: {str(e)}")
        return {
            "success": False,
            "summary_data": None,
            "statistics_info": None,
            "message": f"统计汇总失败: {str(e)}"
        }

@tool
def match_installation_standards(statistics_info: Dict) -> Dict[str, Any]:
    """
    匹配仪表安装规范
    
    Args:
        statistics_info: 统计信息字典
    
    Returns:
        匹配结果字典：{"success": bool, "standard_clauses": Dict, "message": str}
    """
    try:
        if not statistics_info or 'type_distribution' not in statistics_info:
            raise ValueError("无效的统计信息")
        
        retriever = get_retriever()
        standard_clauses = {}
        
        # 为每种仪表类型检索相关规范
        for instrument_type, count in statistics_info['type_distribution'].items():
            if count > 0 and instrument_type != "未知":
                try:
                    # 获取综合规范信息
                    comprehensive_info = retriever.get_comprehensive_standards(instrument_type)
                    standard_clauses[instrument_type] = comprehensive_info
                    
                except Exception as e:
                    logger.warning(f"获取 {instrument_type} 规范失败: {str(e)}")
                    continue
        
        return {
            "success": True,
            "standard_clauses": standard_clauses,
            "message": f"成功匹配 {len(standard_clauses)} 种仪表的安装规范"
        }
        
    except Exception as e:
        logger.error(f"匹配安装规范失败: {str(e)}")
        return {
            "success": False,
            "standard_clauses": {},
            "message": f"匹配安装规范失败: {str(e)}"
        }

@tool
def generate_installation_recommendations(summary_data: Dict, statistics_info: Dict) -> Dict[str, Any]:
    """
    生成安装推荐方案
    
    Args:
        summary_data: 汇总数据字典
        statistics_info: 统计信息字典
    
    Returns:
        推荐结果字典：{"success": bool, "recommendations": Dict, "message": str}
    """
    try:
        if not summary_data or not statistics_info:
            raise ValueError("缺少必要的数据")
        
        generator = get_recommendation_generator()
        recommendations = {}
        
        # 重建DataFrame
        summary_df = pd.DataFrame(summary_data["data"])
        
        # 为主要仪表类型生成详细推荐
        top_types = summary_df.groupby('仪表类型')['数量总和'].sum().sort_values(ascending=False).head(3)
        
        for instrument_type, total_qty in top_types.items():
            if instrument_type != "未知":
                try:
                    # 获取该类型的典型型号
                    type_data = summary_df[summary_df['仪表类型'] == instrument_type]
                    main_model = type_data.iloc[0]['型号'] if not type_data.empty else ""
                    
                    # 生成推荐
                    recommendation = generator.generate_installation_recommendation(
                        instrument_type=instrument_type,
                        model_spec=main_model,
                        quantity=int(total_qty),
                        process_conditions="",
                        custom_requirements=""
                    )
                    
                    recommendations[instrument_type] = recommendation
                    
                except Exception as e:
                    logger.warning(f"生成 {instrument_type} 推荐失败: {str(e)}")
                    continue
        
        # 生成批量安装建议
        if statistics_info:
            try:
                batch_recommendation = generator.generate_batch_recommendation(statistics_info)
                recommendations['batch_plan'] = batch_recommendation
            except Exception as e:
                logger.warning(f"生成批量建议失败: {str(e)}")
        
        return {
            "success": True,
            "recommendations": recommendations,
            "message": f"成功生成 {len(recommendations)} 个推荐方案"
        }
        
    except Exception as e:
        logger.error(f"生成安装推荐失败: {str(e)}")
        return {
            "success": False,
            "recommendations": {},
            "message": f"生成安装推荐失败: {str(e)}"
        }

@tool
def generate_final_report(summary_data: Dict, recommendations: Dict, error_message: str = "") -> Dict[str, Any]:
    """
    生成最终报告
    
    Args:
        summary_data: 汇总数据字典
        recommendations: 推荐方案字典
        error_message: 错误信息
    
    Returns:
        报告结果字典：{"success": bool, "final_report": str, "message": str}
    """
    try:
        from .generate_installation_recommendation import format_recommendation_report
        
        report_parts = []
        
        # 标题
        report_parts.append("# 仪表识别与安装推荐报告\n")
        
        # 统计汇总部分
        if summary_data and summary_data.get("data"):
            summary_df = pd.DataFrame(summary_data["data"])
            summary_report = generate_summary_report(summary_df)
            report_parts.append(summary_report)
            report_parts.append("\n" + "="*60 + "\n")
        
        # 安装推荐部分
        if recommendations:
            report_parts.append("# 安装推荐方案\n")
            
            # 批量规划
            if 'batch_plan' in recommendations:
                report_parts.append("## 项目整体规划")
                report_parts.append(recommendations['batch_plan'])
                report_parts.append("\n" + "-"*40 + "\n")
            
            # 分类型推荐
            for instrument_type, recommendation in recommendations.items():
                if instrument_type != 'batch_plan':
                    report_parts.append(f"## {instrument_type}专项推荐")
                    if isinstance(recommendation, dict):
                        formatted_report = format_recommendation_report(recommendation)
                        report_parts.append(formatted_report)
                    else:
                        report_parts.append(str(recommendation))
                    report_parts.append("\n" + "-"*40 + "\n")
        
        # 错误信息
        if error_message:
            report_parts.append(f"\n⚠️ 处理过程中的问题：{error_message}")
        
        final_report = "\n".join(report_parts)
        
        return {
            "success": True,
            "final_report": final_report,
            "message": "最终报告生成完成"
        }
        
    except Exception as e:
        logger.error(f"生成最终报告失败: {str(e)}")
        return {
            "success": False,
            "final_report": f"报告生成失败: {str(e)}",
            "message": f"生成最终报告失败: {str(e)}"
        }

# 工具列表，用于LangGraph注册
INSTRUMENT_TOOLS = [
    extract_excel_tables,
    parse_instrument_table,
    classify_instrument_types,
    summarize_instrument_statistics,
    match_installation_standards,
    generate_installation_recommendations,
    generate_final_report
] 