"""
Excel表格读取工具
用于读取包含仪表清单的Excel文件
"""
import pandas as pd
import os
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def extract_tables_from_excel(file_path: str) -> List[Tuple[str, pd.DataFrame]]:
    """
    简化的表格提取函数，返回所有工作表
    
    Args:
        file_path: Excel文件路径
    
    Returns:
        List of (sheet_name, DataFrame) tuples
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if not file_path.lower().endswith(('.xls', '.xlsx')):
        raise ValueError("不支持的文件格式，请使用.xls或.xlsx文件")
    
    results = []
    
    try:
        # 读取所有sheet
        if file_path.lower().endswith('.xlsx'):
            xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        else:
            xl_file = pd.ExcelFile(file_path, engine='xlrd')
        
        for sheet_name in xl_file.sheet_names:
            logger.info(f"读取工作表: {sheet_name}")
            try:
                # 读取当前sheet，不设置header
                df = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)
                
                # 删除完全为空的行和列
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if not df.empty:
                    results.append((sheet_name, df))
                    logger.info(f"成功读取工作表 {sheet_name}: {df.shape}")
                
            except Exception as e:
                logger.error(f"读取工作表 {sheet_name} 失败: {str(e)}")
                continue
        
        xl_file.close()
        
    except Exception as e:
        logger.error(f"读取Excel文件失败: {str(e)}")
        raise
    
    logger.info(f"总共读取 {len(results)} 个工作表")
    return results

def extract_excel_tables(file_path: str, keyword: str = "仪表清单") -> List[Dict]:
    """
    读取Excel文件并提取所有工作表
    让用户自己选择需要的表格，而不是基于关键字自动过滤
    
    Args:
        file_path: Excel文件路径
        keyword: 保留参数以兼容现有调用，但不再使用
    
    Returns:
        包含所有表格信息的列表，每个元素包含sheet_name, headers, data
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 检查文件格式
    if not file_path.lower().endswith(('.xls', '.xlsx')):
        raise ValueError("不支持的文件格式，请使用.xls或.xlsx文件")
    
    results = []
    
    try:
        # 读取所有sheet
        if file_path.lower().endswith('.xlsx'):
            xl_file = pd.ExcelFile(file_path, engine='openpyxl')
        else:
            xl_file = pd.ExcelFile(file_path, engine='xlrd')
        
        for sheet_name in xl_file.sheet_names:
            logger.info(f"正在处理工作表: {sheet_name}")
            
            try:
                # 读取当前sheet - 获取准确的原始行数
                df_original = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)
                
                # 计算原始行数（去除完全空行）
                df_for_count = df_original.dropna(how='all')
                original_row_count = len(df_for_count)
                        
                # 清理空行空列
                df = df_original.dropna(how='all').dropna(axis=1, how='all')
                            
                if df.empty:
                    logger.info(f"工作表 {sheet_name} 为空，跳过")
                    continue
                
                # 直接处理每个工作表，传递原始行数
                table_info = _process_any_table(xl_file, sheet_name, df, original_row_count)
                if table_info:
                    results.append(table_info)
                    logger.info(f"成功处理工作表: {sheet_name} ({len(table_info['data'])}行)")
                    
            except Exception as e:
                logger.error(f"处理工作表 {sheet_name} 时出错: {str(e)}")
                continue
        
        xl_file.close()
        
    except Exception as e:
        logger.error(f"读取Excel文件时出错: {str(e)}")
        raise
    
    if not results:
        logger.warning(f"未找到任何有效的表格")
    else:
        logger.info(f"成功提取 {len(results)} 个表格")
    
    return results

def _process_any_table(xl_file, sheet_name: str, df: pd.DataFrame, original_row_count: int) -> Optional[Dict]:
    """
    处理任何工作表，不区分类型
    
    Args:
        xl_file: Excel文件对象
        sheet_name: 工作表名称
        df: DataFrame（原始完整数据）
        original_row_count: 原始行数
    
    Returns:
        表格信息字典
    """
    try:
        # 查找标题行
        header_row_idx = -1
        
        # 查找包含"位号"和"型号"的行作为标题行（仪表数据表格）
        for idx in range(min(10, len(df))):
            row_str = ' '.join(str(cell) for cell in df.iloc[idx].dropna()).lower()
            if '位号' in row_str and '型号' in row_str:
                header_row_idx = idx
                logger.info(f"在工作表 {sheet_name} 第 {idx+1} 行找到仪表标题行")
                break
        
        if header_row_idx >= 0:
            # 仪表数据表格：重新读取，使用找到的标题行
            table_df = pd.read_excel(xl_file, sheet_name=sheet_name, 
                                   skiprows=header_row_idx)
            
            # 清理空行
            table_df = table_df.dropna(how='all')
            
            if not table_df.empty:
                # 使用实际处理后的行数
                actual_row_count = len(table_df)
                return {
                    'name': sheet_name,
                    'description': f'包含{actual_row_count}行数据的仪表表格',
                    'sheet_name': sheet_name,
                    'headers': list(table_df.columns),
                    'data': table_df,
                    'table_type': 'instrument_data'
                }
        else:
            # 其他类型表格：直接使用原始数据
            logger.info(f"工作表 {sheet_name} 未找到仪表标题行，作为普通表格处理")
            actual_row_count = len(df)
            return {
                'name': sheet_name,
                'description': f'包含{actual_row_count}行数据的表格',
                'sheet_name': sheet_name,
                'headers': [f'Column_{i}' for i in range(len(df.columns))],
                'data': df,
                'table_type': 'general'
            }
        
    except Exception as e:
        logger.error(f"处理表格失败: {str(e)}")
    
    return None

def validate_instrument_table(df: pd.DataFrame) -> bool:
    """
    验证表格是否为有效的仪表清单表格
    
    Args:
        df: 待验证的DataFrame
    
    Returns:
        是否为有效的仪表表格
    """
    # 检查常见的仪表表格列名
    common_columns = ['型号', '规格', '数量', '位号', '备注', '仪表', '设备']
    
    columns_str = ' '.join(str(col).lower() for col in df.columns)
    
    # 至少包含一个常见列名
    found_columns = sum(1 for col in common_columns if col in columns_str)
    
    return found_columns >= 1 and len(df) > 0

def get_table_summary(table_info: Dict) -> str:
    """
    获取表格摘要信息
    
    Args:
        table_info: 表格信息字典
    
    Returns:
        表格摘要字符串
    """
    df = table_info['data']
    summary = f"""
工作表: {table_info['sheet_name']}
表头: {', '.join(table_info['headers'])}
数据行数: {len(df)}
关键字位置: 第{table_info['keyword_row']}行
    """.strip()
    
    return summary

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 这里可以添加测试用例
    print("Excel表格读取工具已就绪") 