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
    识别表格中的分类标题行，精确匹配分类格式
    
    Args:
        df: 原始DataFrame
    
    Returns:
        List of (category_name, start_row, end_row)
    """
    sections = []
    
    logger.info("🔍 精确识别表格分类标题")
    
    for idx in range(len(df)):
        row_text = " ".join([str(val) for val in df.iloc[idx].values if pd.notna(val)])
        row_text_clean = row_text.strip()
        
        if not row_text_clean:
            continue
            
        logger.debug(f"检查第{idx+1}行: {row_text_clean}")
        
        # 精确匹配中文数字分类标题（支持多种标点符号：、：、.等）
        chinese_num_patterns = [
            (r'^一[：:\s\.\,\、\.]+(.+)', '一'),
            (r'^二[：:\s\.\,\、\.]+(.+)', '二'),
            (r'^三[：:\s\.\,\、\.]+(.+)', '三'),
            (r'^四[：:\s\.\,\、\.]+(.+)', '四'),
            (r'^五[：:\s\.\,\、\.]+(.+)', '五'),
            (r'^六[：:\s\.\,\、\.]+(.+)', '六'),
            (r'^七[：:\s\.\,\、\.]+(.+)', '七'),
            (r'^八[：:\s\.\,\、\.]+(.+)', '八'),
            (r'^九[：:\s\.\,\、\.]+(.+)', '九'),
            (r'^十[：:\s\.\,\、\.]+(.+)', '十')
        ]
        
        # 匹配特殊情况：紧跟分类名的情况
        special_patterns = [
            (r'^一、(.+)', '一'),
            (r'^二、(.+)', '二'),
            (r'^三、(.+)', '三'),
            (r'^四、(.+)', '四'),
            (r'^五、(.+)', '五'),
            (r'^六、(.+)', '六'),
            (r'^七、(.+)', '七'),
            (r'^八、(.+)', '八'),
            (r'^九、(.+)', '九'),
            (r'^十、(.+)', '十')
        ]
        
        # 组合所有模式
        all_patterns = chinese_num_patterns + special_patterns
        
        found = False
        for pattern, num_char in all_patterns:
            match = re.search(pattern, row_text_clean)
            if match:
                # 提取分类名称
                category_name = match.group(1).strip().split()[0] if match.group(1).strip().split() else '未知分类'
                
                # 进一步验证：确保这真的是分类标题
                # 1. 分类名称不能太长
                if len(category_name) > 50:  # 放宽长度限制
                    continue
                    
                # 2. 不能包含明显的技术参数（放宽限制）
                tech_params = ['MPa', '级', '℃', '°C', 'mm', 'Ф', 'DN', 'PN']
                if any(param in category_name for param in tech_params):
                    continue
                
                # 3. 不能包含复杂符号（允许括号，因为分类中可能包含）
                complex_chars = ['=']
                if any(char in category_name for char in complex_chars):
                    continue
                
                # 4. 应该包含仪表相关词汇（放宽要求，支持更多类型）
                instrument_keywords = ['仪表', '设备', '系统', '控制', '装置', '变送器', '传感器', '计', '表', '阀', '箱', '门', '风门', '头', '分析']
                if not any(keyword in category_name for keyword in instrument_keywords):
                    # 对于明确的数字分类，即使不包含关键词也可能是有效分类
                    logger.warning(f"分类 '{category_name}' 不包含仪表关键词，但继续处理")
                
                sections.append((category_name, idx, -1))  # -1表示结束行待确定
                logger.info(f"✅ 找到分类标题: {num_char}：{category_name} 在第{idx+1}行")
                found = True
                break
        
        if found:
            continue  # 找到匹配后跳过其他检查
    
    # 确定每个分类的结束行
    for i in range(len(sections)):
        current_start = sections[i][1]
        if i < len(sections) - 1:
            next_start = sections[i+1][1]
            sections[i] = (sections[i][0], current_start, next_start - 1)
        else:
            # 最后一个分类到表格结束
            sections[i] = (sections[i][0], current_start, len(df) - 1)
    
    logger.info(f"🎯 成功识别到 {len(sections)} 个分类区域")
    for category_name, start_row, end_row in sections:
        logger.info(f"   分类: {category_name}, 起始行: {start_row+1}, 结束行: {end_row+1}")
    
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
    
    # 主行mask：识别真正的仪表行，排除分类标题和说明行
    # 1. 位号不为空
    # 2. 排除纯数字编号（如"一：", "二："等分类标题）
    # 3. 排除说明行
    def is_valid_instrument_row(tag_value):
        """判断是否为有效的仪表行"""
        if not tag_value or str(tag_value).strip() in ['', 'nan', 'None']:
            return False
        
        tag_str = str(tag_value).strip()
        
        # 排除分类标题行（如"一："、"二："、"三："、"一、"等）
        if re.match(r'^[一二三四五六七八九十\d+][:：\s\.\,\、\.]*$', tag_str):
            return False
        
        # 排除完整的分类标题行（如"一、温度仪表"）
        if re.match(r'^[一二三四五六七八九十\d+][：:\s\.\,\、\.、]+.+', tag_str):
            return False
        
        # 排除说明行
        if tag_str.startswith('说明'):
            return False
        
        # 仪表位号通常包含字母和数字的组合
        if re.match(r'^[A-Z]+[A-Z0-9\-]*\d+$', tag_str, re.IGNORECASE):
            return True
        
        # 或者是特殊格式的位号（如MB-101等）
        if re.match(r'^[A-Z]{1,4}-\d+$', tag_str, re.IGNORECASE):
            return True
        
        return False
    
    mask_main = df_data[tag_col].apply(is_valid_instrument_row)
    
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
    
    # 重建型号列：保持原始型号值，包括空值
    def get_model_value(row):
        if mask_main_aligned.loc[row.name]:
            original_model = model_values.get(row["group_id"], "")
            # 对于电动门控制箱等特殊情况，使用描述性名称
            if original_model in ["", "nan", None] or pd.isna(original_model):
                tag_value = str(row.get(tag_col, ""))
                if tag_value.startswith("MB-"):
                    # 电动门控制箱使用测点名称作为型号
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
                    # 对于其他情况，保持型号为空
                    return ""
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
    
    if category_sections:
        # 情况1：表格有明确分类，按分类区域分配
        logger.info("📋 表格有明确分类，使用分类区域分配")
        for category_name, start_row, end_row in category_sections:
            # 找到属于此区域的数据行
            mask_in_section = (df_final['_original_row'] >= start_row) & (df_final['_original_row'] <= end_row)
            df_final.loc[mask_in_section, '仪表类型'] = category_name
            logger.info(f"分配 {mask_in_section.sum()} 行到类别: {category_name}")
    else:
        # 情况2：表格没有分类，使用LLM判断仪表类型
        logger.info("🤖 表格没有明确分类，使用LLM智能判断仪表类型")
        df_final = _classify_instruments_with_llm(df_final, tag_col, model_col)
    
    # 删除临时列
    df_final = df_final.drop('_original_row', axis=1)
    
    # Step i: 删除空白桶 - 只要求位号不为空
    # 允许型号为空（如双色水位计等没有标准型号的仪表）
    df_final = df_final[
        (df_final[tag_col].notna()) & 
        (df_final[tag_col].astype(str).str.strip() != '') &
        (df_final[tag_col].astype(str).str.strip() != 'nan')
    ].copy()
    
    # 标准化列名 - 确保格式一致性
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
    
    # 确保必要列存在 - 无论有分类还是无分类，格式完全一致
    required_cols = ['位号', '型号', '数量', '规格', '备注', '仪表类型']
    for col in required_cols:
        if col not in df_final.columns:
            if col == '数量':
                df_final[col] = 1
            elif col == '仪表类型':
                df_final[col] = "未分类"
            else:
                df_final[col] = ""
    
    # 选择最终列 - 确保两种情况格式完全一致
    final_cols = ['位号', '型号', '数量', '规格', '备注', '仪表类型']
    df_final = df_final[final_cols].copy()
    
    logger.info(f"✅ 成功解析 {len(df_final)} 行仪表数据")
    logger.info(f"📊 原始表格行数: {len(df_original)} 行（包含所有行和空行）")
    logger.info(f"🔍 有效仪表数据: {len(df_final)} 行（去除分类标题和空行后）")
    
    # 输出分类统计
    category_stats = df_final['仪表类型'].value_counts()
    logger.info("📈 分类统计:")
    for category, count in category_stats.items():
        logger.info(f"   • {category}: {count}台")
    
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

def _classify_instruments_with_llm(df: pd.DataFrame, tag_col: str, model_col: str) -> pd.DataFrame:
    """
    当表格没有明确分类时，使用LLM智能判断每个仪表的类型
    确保返回的DataFrame格式与有分类情况完全一致
    
    Args:
        df: 仪表数据DataFrame
        tag_col: 位号列名
        model_col: 型号列名
    
    Returns:
        添加了智能分类的DataFrame（格式与有分类情况一致）
    """
    try:
        from config.settings import get_openai_config
        
        llm_config = get_openai_config()
        if not llm_config.get('api_key'):
            logger.warning("⚠️ 没有LLM配置，无法智能分类，保持未分类状态")
            # 确保返回格式一致：所有仪表标记为"未分类"
            df_result = df.copy()
            df_result['仪表类型'] = "未分类"
            return df_result
        
        logger.info(f"🤖 开始LLM智能分类 {len(df)} 个仪表")
        
        # 准备分析数据
        instruments_for_analysis = []
        for idx, row in df.iterrows():
            instrument_info = {
                'index': idx,
                'tag': str(row.get(tag_col, '')).strip(),
                'model': str(row.get(model_col, '')).strip(),
                'spec': str(row.get('规格', '')).strip(),
                'remark': str(row.get('备注', '')).strip()
            }
            instruments_for_analysis.append(instrument_info)
        
        # 分批处理（每次最多10个仪表）
        batch_size = 10
        df_result = df.copy()
        
        # 初始化所有仪表为未分类，确保格式一致
        df_result['仪表类型'] = "未分类"
        
        for i in range(0, len(instruments_for_analysis), batch_size):
            batch = instruments_for_analysis[i:i+batch_size]
            logger.info(f"🔍 处理批次 {i//batch_size + 1}: {len(batch)} 个仪表")
            
            # 构建LLM分析提示
            instruments_text = ""
            for j, inst in enumerate(batch):
                instruments_text += f"仪表{j+1}: 位号={inst['tag']}, 型号={inst['model']}, 规格={inst['spec']}, 备注={inst['remark']}\n"
            
            prompt = f"""请分析以下仪表数据，为每个仪表判断其类型。

仪表信息：
{instruments_text}

请基于以下常见仪表类型进行分类：
- 温度仪表：热电偶、热电阻、温度计、温度变送器
- 压力仪表：压力表、压力变送器、差压变送器
- 流量仪表：流量计、流量变送器、孔板、喷嘴
- 液位仪表：液位计、液位变送器、浮球液位计
- 控制设备：调节阀、控制阀、电动阀、气动阀
- 电气设备：控制箱、配电箱、操作台
- 分析仪表：分析仪、检测仪
- 其他仪表：如果不属于以上类型

请以JSON格式返回结果：
{{
    "classifications": [
        {{
            "instrument_index": 1,
            "category": "温度仪表",
            "confidence": 0.9,
            "reason": "位号TE开头，型号为热电阻"
        }},
        ...
    ]
}}

注意：
- 位号前缀含义：TE/TT=温度, PT/PI=压力, FT/FI=流量, LT/LI=液位, CV/FV=控制阀
- 根据型号、规格、备注综合判断
- 置信度范围0-1"""

            # 调用LLM
            classifications = _call_llm_for_classification(prompt, llm_config)
            
            if classifications and 'classifications' in classifications:
                # 应用分类结果
                for result in classifications['classifications']:
                    instrument_index = result.get('instrument_index', 0) - 1  # 转换为0索引
                    category = result.get('category', '其他仪表')
                    confidence = result.get('confidence', 0.5)
                    
                    if 0 <= instrument_index < len(batch) and confidence >= 0.5:
                        original_idx = batch[instrument_index]['index']
                        df_result.at[original_idx, '仪表类型'] = category
                        logger.info(f"✅ 仪表 {batch[instrument_index]['tag']} 分类为: {category} (置信度: {confidence})")
                    else:
                        logger.warning(f"⚠️ 跳过低置信度分类: 置信度 {confidence}")
            else:
                logger.warning(f"⚠️ 批次 {i//batch_size + 1} LLM分类失败")
        
        # 统计分类结果
        classification_stats = df_result['仪表类型'].value_counts()
        logger.info("🎯 LLM智能分类完成:")
        for category, count in classification_stats.items():
            logger.info(f"   • {category}: {count}台")
        
        # 确保返回的DataFrame格式与有分类情况完全一致
        # 包含相同的列：['位号', '型号', '数量', '规格', '备注', '仪表类型']
        return df_result
        
    except Exception as e:
        logger.error(f"❌ LLM智能分类失败: {str(e)}")
        logger.info("📋 保持原有的未分类状态")
        # 确保即使出错也返回一致的格式
        df_result = df.copy()
        df_result['仪表类型'] = "未分类"
        return df_result

def _call_llm_for_classification(prompt: str, config: dict) -> dict:
    """调用LLM进行仪表分类"""
    try:
        from openai import OpenAI
        import json
        import re
        
        client = OpenAI(
            api_key=config.get('api_key'),
            base_url=config.get('base_url', 'https://api.openai.com/v1')
        )
        
        response = client.chat.completions.create(
            model=config.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "你是一个专业的仪表分类专家，擅长根据位号、型号、规格等信息判断仪表类型。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        
        # 解析JSON响应
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # 尝试提取JSON内容
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                logger.warning(f"无法解析LLM分类响应: {result_text[:200]}...")
                return {}
                
    except Exception as e:
        logger.error(f"LLM分类调用失败: {str(e)}")
        return {}

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