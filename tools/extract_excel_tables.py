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
    读取Excel文件并识别包含关键字的表格
    
    Args:
        file_path: Excel文件路径
        keyword: 识别关键字，默认为"仪表清单"
    
    Returns:
        包含表格信息的列表，每个元素包含sheet_name, headers, data
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
                # 读取当前sheet
                df = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)
                
                # 查找包含关键字的行
                keyword_found = False
                for idx, row in df.iterrows():
                    row_str = ' '.join(str(cell) for cell in row.dropna())
                    if keyword in row_str:
                        keyword_found = True
                        logger.info(f"在工作表 {sheet_name} 第 {idx+1} 行找到关键字: {keyword}")
                        
                        # 尝试识别表头
                        headers = None
                        data_start_idx = idx + 1
                        
                        # 检查关键字所在行是否可能是表头
                        if pd.notna(row).sum() > 1:  # 如果该行有多个非空值，可能是表头
                            headers = [str(cell).strip() for cell in row.dropna()]
                        else:
                            # 查找下一行作为表头
                            if data_start_idx < len(df):
                                next_row = df.iloc[data_start_idx]
                                if pd.notna(next_row).sum() > 1:
                                    headers = [str(cell).strip() for cell in next_row.dropna()]
                                    data_start_idx += 1
                        
                        # 读取数据
                        if headers and data_start_idx < len(df):
                            # 重新读取，使用识别的表头行
                            table_df = pd.read_excel(xl_file, sheet_name=sheet_name, 
                                                   skiprows=data_start_idx-1)  # 读取所有数据，不限制行数
                            
                            # 清理空行
                            table_df = table_df.dropna(how='all')
                            
                            if not table_df.empty:
                                results.append({
                                    'name': sheet_name,
                                    'description': f'包含{len(table_df)}行数据的仪表表格',
                                    'sheet_name': sheet_name,
                                    'headers': list(table_df.columns),
                                    'data': table_df,
                                    'keyword_row': idx + 1
                                })
                        
                        break  # 找到关键字后跳出当前sheet的循环
                
                if not keyword_found:
                    logger.info(f"工作表 {sheet_name} 中未找到关键字: {keyword}")
                    
            except Exception as e:
                logger.error(f"处理工作表 {sheet_name} 时出错: {str(e)}")
                continue
        
        xl_file.close()
        
    except Exception as e:
        logger.error(f"读取Excel文件时出错: {str(e)}")
        raise
    
    if not results:
        logger.warning(f"未在任何工作表中找到包含关键字 '{keyword}' 的表格")
    else:
        logger.info(f"成功提取 {len(results)} 个表格")
    
    return results

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