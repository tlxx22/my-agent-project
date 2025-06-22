"""
仪表表格解析工具 - 主行/补充行折叠算法实现
支持复杂的表格结构：主行+多个补充行的灵活组合
增强版：支持识别分类标题行并按区域分配仪表类别
"""
import pandas as pd
import re
from typing import Union, Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_quantity_field(quantity_str: Union[str, int, float]) -> int:
    """
    解析数量字段，处理各种格式并返回整数总数量
    
    支持的格式:
    - 简单数字: "5", 5, 5.0
    - 乘法表达式: "1×2", "2X2", "3x1", "2*3"
    - 带单位: "5台", "3个"
    - 复合表达式: "2×3+1", "1+2×3"
    
    Args:
        quantity_str: 数量字符串或数字
    
    Returns:
        解析后的整数数量
    """
    if pd.isna(quantity_str):
        return 0
    
    # 转换为字符串
    quantity_str = str(quantity_str).strip()
    
    if not quantity_str:
        return 0
    
    try:
        # 移除常见的单位词
        units_to_remove = ['台', '个', '套', '件', '只', '根', '支', '片', '块']
        for unit in units_to_remove:
            quantity_str = quantity_str.replace(unit, '')
        
        # 替换各种乘号为标准格式
        quantity_str = re.sub(r'[×Xx*]', '*', quantity_str)
        
        # 移除空格
        quantity_str = quantity_str.replace(' ', '')
        
        # 处理简单数字
        if re.match(r'^\d+(\.\d+)?$', quantity_str):
            return int(float(quantity_str))
        
        # 处理乘法表达式 (如: 2*3, 1*2*3)
        if re.match(r'^\d+(\*\d+)+$', quantity_str):
            parts = quantity_str.split('*')
            result = 1
            for part in parts:
                result *= int(part)
            return result
        
        # 处理复合表达式 (如: 2*3+1, 1+2*3)
        # 首先检查是否包含加法
        if '+' in quantity_str:
            # 按加号分割
            terms = quantity_str.split('+')
            total = 0
            for term in terms:
                term = term.strip()
                if '*' in term:
                    # 处理乘法项
                    parts = term.split('*')
                    product = 1
                    for part in parts:
                        product *= int(part)
                    total += product
                else:
                    # 简单数字项
                    total += int(term)
            return total
        
        # 处理减法表达式
        if '-' in quantity_str and not quantity_str.startswith('-'):
            terms = quantity_str.split('-')
            total = 0
            for i, term in enumerate(terms):
                term = term.strip()
                if '*' in term:
                    parts = term.split('*')
                    product = 1
                    for part in parts:
                        product *= int(part)
                    if i == 0:
                        total += product
                    else:
                        total -= product
                else:
                    if i == 0:
                        total += int(term)
                    else:
                        total -= int(term)
            return max(0, total)  # 确保不返回负数
        
        # 尝试直接计算表达式 (谨慎使用eval)
        # 仅当表达式只包含数字、基本运算符时才使用
        if re.match(r'^[\d+\-*/().]+$', quantity_str):
            try:
                result = eval(quantity_str)
                return int(result) if result >= 0 else 0
            except:
                pass
        
        # 如果以上都不匹配，尝试提取数字
        numbers = re.findall(r'\d+', quantity_str)
        if numbers:
            # 取第一个数字
            return int(numbers[0])
        
        # 无法解析，返回0
        logger.warning(f"无法解析数量字段: {quantity_str}")
        return 0
        
    except Exception as e:
        logger.error(f"解析数量字段时出错: {quantity_str}, 错误: {str(e)}")
        return 0

def find_category_sections(df: pd.DataFrame) -> List[Tuple[str, int, int]]:
    """
    识别表格中的分类标题行，确定每个类别的起始和结束行
    
    Args:
        df: 原始DataFrame
    
    Returns:
        List of (category_name, start_row, end_row)
    """
    category_patterns = [
        (r".*一[：:\s].*", "温度仪表"),
        (r".*二[：:\s].*", "压力仪表"), 
        (r".*三[：:\s].*", "流量仪表"),
        (r".*四[：:\s].*", "液位仪表"),
        (r".*五[：:\s].*", "两位式电动门控制箱"),
        (r".*六[：:\s].*", "气动调节阀")
    ]
    
    sections = []
    
    for idx in range(len(df)):
        row_text = " ".join([str(val) for val in df.iloc[idx].values if pd.notna(val)])
        logger.debug(f"第{idx+1}行内容: {row_text}")
        
        for pattern, category_name in category_patterns:
            if re.search(pattern, row_text, re.IGNORECASE):
                sections.append((category_name, idx, -1))  # -1表示结束行待确定
                logger.info(f"找到分类标题行: {category_name} 在第{idx+1}行")
                break
    
    # 确定每个分类的结束行
    for i in range(len(sections)):
        current_start = sections[i][1]
        if i < len(sections) - 1:
            next_start = sections[i+1][1]
            sections[i] = (sections[i][0], current_start, next_start - 1)
        else:
            # 最后一个分类到表格结束
            sections[i] = (sections[i][0], current_start, len(df) - 1)
    
    logger.info(f"识别到 {len(sections)} 个分类区域")
    return sections

def find_header_row(df: pd.DataFrame) -> int:
    """
    定位标题行：同时包含"位号"+"测点"或"型号"
    
    Args:
        df: 原始DataFrame
    
    Returns:
        标题行索引，如果未找到返回-1
    """
    key_patterns = [
        ["位号", "型号"],
        ["位号", "测点"], 
        ["tag", "model"],
        ["工位号", "设备型号"],
        ["仪表位号", "仪表型号"]
    ]
    
    for idx in range(min(10, len(df))):  # 只检查前10行
        row_str = ' '.join(str(cell).lower() for cell in df.iloc[idx] if pd.notna(cell))
        
        for patterns in key_patterns:
            if all(pattern.lower() in row_str for pattern in patterns):
                logger.info(f"找到标题行在第 {idx+1} 行: {patterns}")
                return idx
    
    logger.warning("未找到包含位号+型号的标题行")
    return -1

def assign_categories_by_sections(df: pd.DataFrame, category_sections: List[Tuple[str, int, int]]) -> pd.DataFrame:
    """
    根据分类区域为每行数据分配类别
    
    Args:
        df: 解析后的仪表数据DataFrame
        category_sections: 分类区域列表
    
    Returns:
        添加了'仪表类型'列的DataFrame
    """
    df = df.copy()
    df['仪表类型'] = "未分类"
    df['原始行号'] = range(len(df))
    
    # 为每行分配类别
    for category_name, start_row, end_row in category_sections:
        # 找到属于此区域的数据行
        for idx, row in df.iterrows():
            original_row = row.get('原始行号', idx)
            if start_row <= original_row <= end_row:
                df.at[idx, '仪表类型'] = category_name
    
    # 删除临时的原始行号列
    df = df.drop('原始行号', axis=1)
    
    return df

def extract_and_parse_instrument_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    核心函数：实现主行/补充行折叠算法 + 分类区域识别
    
    规则框架：
    a. 识别分类标题行和区域边界
    b. 定位数据标题行 - 同时包含"位号"+"型号"  
    c. 切分数据区 - 标题行以下
    d. 识别"主行" - 位号≠空且型号≠空
    e. 向下收集补充行 - 在下一条主行出现前，把行号累进到当前主行的"桶"里
    f. 主行forward-fill空列 - 位号forward-fill；型号只保留主行的值
    g. 补充列折叠 - 对同一group_id：字符串列→";".join，数量列→第一条非空
    h. 根据分类区域分配仪表类型
    i. 删除空白桶 - 主键列为空的行删除
    
    Args:
        df: 原始Excel DataFrame（可能有header或没有header）
    
    Returns:
        折叠后的标准化DataFrame，包含'仪表类型'列
    """
    if df.empty:
        logger.warning("输入DataFrame为空")
        return pd.DataFrame()
    
    # 保存原始行索引用于类别分配
    df_original = df.copy()
    df_original['original_index'] = range(len(df_original))
    
    # Step a: 识别分类标题行和区域边界
    category_sections = find_category_sections(df_original)
    
    # 检查是否已经有合适的列名（测试模式）
    if '位号' in df.columns and '型号' in df.columns:
        logger.info("检测到已设置列名，跳过标题行查找")
        df_data = df.copy()
        idx_header = -1  # 表示无需处理标题行
    else:
        # Step b: 定位数据标题行
        idx_header = find_header_row(df)
        if idx_header == -1:
            logger.error("无法找到有效的标题行")
            return pd.DataFrame()
        
        # Step c: 切分数据区 
        df_data = df.iloc[idx_header+1:].copy()
        df_data.columns = df.iloc[idx_header]  # 使用标题行作为列名
        df_data = df_data.reset_index(drop=True)
    
    if df_data.empty:
        logger.warning("标题行后无数据")
        return pd.DataFrame()
    
    # 保存原始索引映射
    if idx_header != -1:
        original_indices = list(range(idx_header + 1, idx_header + 1 + len(df_data)))
    else:
        original_indices = list(range(len(df_data)))
    
    df_data['_original_row'] = original_indices
    
    # 智能识别列名映射
    column_mapping = {}
    for col in df_data.columns:
        col_str = str(col).lower().strip()
        if any(keyword in col_str for keyword in ['位号', 'tag', '工位号']):
            column_mapping['位号'] = col
        elif any(keyword in col_str for keyword in ['型号', 'model', '设备型号', '仪表型号']):
            column_mapping['型号'] = col
        elif any(keyword in col_str for keyword in ['数量', 'qty', 'quantity', '台数']):
            column_mapping['数量'] = col
        elif any(keyword in col_str for keyword in ['规格', 'spec', '型式', '描述']):
            column_mapping['规格'] = col
        elif any(keyword in col_str for keyword in ['备注', 'remark', '说明', 'note']):
            column_mapping['备注'] = col
    
    # 检查必要列是否存在
    if '位号' not in column_mapping or '型号' not in column_mapping:
        logger.error(f"缺少必要的列：位号或型号。当前列：{list(df_data.columns)}")
        return pd.DataFrame()
    
    logger.info(f"列映射: {column_mapping}")
    
    # Step d: 识别"主行" - 位号≠空且型号≠空
    tag_col = column_mapping['位号']
    model_col = column_mapping['型号']
    
    # 清理空值和字符串
    df_data[tag_col] = df_data[tag_col].astype(str).str.strip()
    df_data[model_col] = df_data[model_col].astype(str).str.strip()
    
    # 主行mask：位号不为空且（型号不为空 或者 位号包含特殊标识）
    # 特殊处理：电动门控制箱（MB-）等可能没有标准型号
    mask_main = (
        df_data[tag_col].notna() & 
        (df_data[tag_col] != '') &
        (df_data[tag_col] != 'nan') &
        (
            # 标准情况：型号不为空
            (df_data[model_col].notna() & 
        (df_data[model_col] != '') &
             (df_data[model_col] != 'nan')) |
            # 特殊情况：电动门控制箱等可能没有型号但有位号
            df_data[tag_col].str.contains(r'^(MB-|CV-|FV-|HV-|LV-|PV-|TV-)', na=False)
        )
    )
    
    if not mask_main.any():
        logger.error("没有找到任何主行（位号+型号同时非空）")
        return pd.DataFrame()
    
    logger.info(f"找到 {mask_main.sum()} 个主行")
    
    # Step e: 向下收集补充行 - group_id分组
    df_data["group_id"] = mask_main.cumsum()
    
    # 过滤掉group_id为0的行（标题行之前的垃圾行）
    df_data = df_data[df_data["group_id"] > 0].copy()
    
    if df_data.empty:
        logger.error("过滤后无有效数据")
        return pd.DataFrame()
    
    # Step f: 主行forward-fill空列
    # 位号forward-fill（每个组内的补充行继承主行的位号）
    df_data[tag_col] = df_data.groupby("group_id")[tag_col].ffill()
    
    # 型号只保留主行的值（补充行的型号清空）
    # 重建mask_main以匹配新的索引
    mask_main_aligned = mask_main.reindex(df_data.index, fill_value=False)
    
    # 找到每个组的主行位置并记录型号值
    model_values = {}
    for group_id in df_data["group_id"].unique():
        group_data = df_data[df_data["group_id"] == group_id]
        group_main_mask = mask_main_aligned[group_data.index]
        group_main_rows = group_data[group_main_mask]
        
        if not group_main_rows.empty:
            model_values[group_id] = group_main_rows.iloc[0][model_col]
        else:
            model_values[group_id] = ""
    
    # 重建型号列：只有主行有值，补充行为空
    def get_model_value(row):
        if mask_main_aligned.loc[row.name]:
            original_model = model_values.get(row["group_id"], "")
            # 如果型号为空但位号符合特殊模式，使用测点名称或给默认值
            if original_model in ["", "nan", None] or pd.isna(original_model):
                tag_value = str(row.get(tag_col, ""))
                if tag_value.startswith("MB-"):
                    # 电动门控制箱使用测点名称作为型号，如果没有则用默认值
                    test_point_col = None
                    for col in df_data.columns:
                        if any(keyword in str(col).lower() for keyword in ['测点', '名称', '说明']):
                            test_point_col = col
                            break
                    if test_point_col and pd.notna(row.get(test_point_col)):
                        return str(row.get(test_point_col, "")).strip()
                    else:
                        return "电动门控制箱"  # 默认型号
                elif tag_value.startswith(("CV-", "FV-", "HV-", "LV-", "PV-", "TV-")):
                    return "控制阀"  # 默认型号
                else:
                    return "未知型号"
            return original_model
        else:
            return ""
    
    df_data[model_col] = df_data.apply(get_model_value, axis=1)
    
    # Step g: 补充列折叠
    # 准备聚合函数
    def safe_join(series):
        """安全地连接字符串，过滤空值"""
        valid_values = [str(v).strip() for v in series if pd.notna(v) and str(v).strip() != '' and str(v).strip() != 'nan']
        return "; ".join(unique_preserve_order(valid_values)) if valid_values else ""
    
    def first_valid(series):
        """返回第一个有效值"""
        for v in series:
            if pd.notna(v) and str(v).strip() != '' and str(v).strip() != 'nan':
                return v
        return None
    
    def sum_quantities(series):
        """求和数量，使用解析函数"""
        total = 0
        for v in series:
            if pd.notna(v):
                parsed = parse_quantity_field(v)
                total += parsed
        return total if total > 0 else 1  # 默认最少为1
    
    def first_original_row(series):
        """获取组内第一个原始行号，用于类别分配"""
        return series.iloc[0] if len(series) > 0 else -1
    
    # 构建聚合字典
    agg_dict = {
        tag_col: 'first',  # 位号取第一个（已经forward-fill过）
        model_col: first_valid,  # 型号取第一个有效值（主行的值）
        '_original_row': first_original_row  # 保存原始行号用于类别分配
    }
    
    # 处理其他列
    for col_name, col in column_mapping.items():
        if col_name in ['位号', '型号']:
            continue
        elif col_name == '数量':
            agg_dict[col] = sum_quantities
        else:
            agg_dict[col] = safe_join
    
    # 对于未映射的列，使用默认聚合策略
    for col in df_data.columns:
        if col not in agg_dict and col not in ["group_id", "_original_row"]:
            # 判断列的类型
            if df_data[col].dtype in ['int64', 'float64'] or col_name_suggests_numeric(col):
                agg_dict[col] = sum_quantities
            else:
                agg_dict[col] = safe_join
    
    # 按group_id分组聚合
    df_final = df_data.groupby("group_id").agg(agg_dict).reset_index(drop=True)
    
    # Step h: 根据分类区域分配仪表类型
    df_final['仪表类型'] = "未分类"
    
    for category_name, start_row, end_row in category_sections:
        # 找到属于此区域的数据行
        mask_in_section = (df_final['_original_row'] >= start_row) & (df_final['_original_row'] <= end_row)
        df_final.loc[mask_in_section, '仪表类型'] = category_name
        logger.info(f"分配 {mask_in_section.sum()} 行到类别: {category_name}")
    
    # 删除临时列
    df_final = df_final.drop('_original_row', axis=1)
    
    # Step i: 删除空白桶 - 主键列为空的行删除
    # 过滤掉位号或型号为空的行
    df_final = df_final[
        (df_final[tag_col].notna()) & 
        (df_final[tag_col].astype(str).str.strip() != '') &
        (df_final[tag_col].astype(str).str.strip() != 'nan') &
        (df_final[model_col].notna()) & 
        (df_final[model_col].astype(str).str.strip() != '') &
        (df_final[model_col].astype(str).str.strip() != 'nan')
    ].copy()
    
    # 标准化列名
    standard_columns = {'位号': tag_col, '型号': model_col}
    if '数量' in column_mapping:
        standard_columns['数量'] = column_mapping['数量']
    if '规格' in column_mapping:
        standard_columns['规格'] = column_mapping['规格']  
    if '备注' in column_mapping:
        standard_columns['备注'] = column_mapping['备注']
    
    # 重命名为标准列名
    rename_dict = {v: k for k, v in standard_columns.items()}
    df_final = df_final.rename(columns=rename_dict)
    
    # 确保必要列存在
    required_cols = ['位号', '型号', '数量', '规格', '备注', '仪表类型']
    for col in required_cols:
        if col not in df_final.columns:
            if col == '数量':
                df_final[col] = 1
            elif col == '仪表类型':
                df_final[col] = "未分类"
            else:
                df_final[col] = ""
    
    # 选择最终列
    final_cols = ['位号', '型号', '数量', '规格', '备注', '仪表类型']
    df_final = df_final[final_cols].copy()
    
    logger.info(f"成功解析 {len(df_final)} 行仪表数据")
    
    # 输出分类统计
    category_stats = df_final['仪表类型'].value_counts()
    logger.info("分类统计:")
    for category, count in category_stats.items():
        logger.info(f"  {category}: {count}台")
    
    return df_final

def unique_preserve_order(lst):
    """保持顺序的去重"""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def col_name_suggests_numeric(col_name):
    """根据列名判断是否可能是数值列"""
    numeric_keywords = ['数量', '台数', '个数', '价格', '金额', 'qty', 'quantity', 'price', 'amount']
    col_str = str(col_name).lower()
    return any(keyword in col_str for keyword in numeric_keywords)

def validate_parsed_data(df: pd.DataFrame) -> bool:
    """
    验证解析后的数据是否有效
    
    Args:
        df: 解析后的DataFrame
    
    Returns:
        数据是否有效
    """
    if df.empty:
        return False
    
    # 检查是否有有效的位号和型号
    valid_tags = df['位号'].str.strip().str.len() > 0
    valid_models = df['型号'].str.strip().str.len() > 0
    
    # 检查数量是否为正数
    valid_quantities = df['数量'] > 0
    
    return valid_tags.any() and valid_models.any() and valid_quantities.any()

# 向后兼容的接口
def extract_instrument_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    向后兼容的接口函数
    """
    return extract_and_parse_instrument_table(df)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试数量解析功能
    test_quantities = ["5", "1×2", "2X3", "3x2", "2*3+1", "5台", "3个", "2×3-1"]
    
    print("数量解析测试:")
    for qty in test_quantities:
        result = parse_quantity_field(qty)
        print(f"{qty} -> {result}")
    
    print("\n仪表表格解析工具已就绪") 