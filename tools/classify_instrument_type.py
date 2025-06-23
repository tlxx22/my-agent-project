"""
仪表型号归类工具
动态从表格中识别分类，支持两种模式：
1. 表格中有明确分类（优先级最高）- 解析类似"一: 温度仪表"的分类标题
2. 表格中无分类时使用LLM判断
"""
import re
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

def extract_categories_from_table(table_data: List[List[str]]) -> Dict[str, List[int]]:
    """
    从表格数据中提取分类信息
    识别类似"一: 温度仪表"、"二: 压力仪表"这样的分类标题行
    
    Args:
        table_data: 表格数据，每行是一个字符串列表
    
    Returns:
        字典: {分类名称: [对应的行号列表]}
    """
    categories = {}
    current_category = None
    category_pattern = re.compile(r'^[一二三四五六七八九十\d+][\s:：\.\-\、]*(.*)$')
    
    for row_idx, row in enumerate(table_data):
        if not row or len(row) == 0:
            continue
        
        # 检查第一列是否是分类标题
        first_cell = str(row[0]).strip()
        if not first_cell:
            continue
        
        # 检查是否是分类标题行
        is_category_row = False
        category_name = ""
        
        # 情况1：第一列是序号（如"一:"），第二列是分类名（如"温度仪表"）
        if category_pattern.match(first_cell) and len(row) > 1:
            second_cell = str(row[1]).strip()
            if second_cell and len(second_cell) > 1:
                category_name = second_cell
                is_category_row = True
                logger.info(f"识别到分离式分类标题: 序号='{first_cell}' 名称='{second_cell}'")
        
        # 情况2：分类信息都在第一列（如"一: 温度仪表"）
        elif category_pattern.match(first_cell):
            match = category_pattern.match(first_cell)
            extracted_name = match.group(1).strip()
            if extracted_name and len(extracted_name) > 1:
                category_name = extracted_name
                is_category_row = True
                logger.info(f"识别到合并式分类标题: '{first_cell}'")
        
        if is_category_row and category_name:
            # 标准化分类名称，添加常见的后缀
            if not any(suffix in category_name for suffix in ['仪表', '控制', '阀门', '装置', '设备', '表', '器', '箱']):
                if '温度' in category_name or '热' in category_name:
                    category_name += '仪表'
                elif '压力' in category_name:
                    category_name += '仪表'
                elif '流量' in category_name:
                    category_name += '仪表'
                elif '液位' in category_name:
                    category_name += '仪表'
                elif '调节' in category_name or '控制' in category_name:
                    if '阀' in category_name:
                        pass  # 保持原样
                    else:
                        category_name += '控制箱'
            
            current_category = category_name
            if current_category not in categories:
                categories[current_category] = []
            
            logger.info(f"识别到分类标题: 第{row_idx+1}行 -> {current_category}")
            continue
        
        # 如果当前行不是分类标题，且有当前分类，则添加到当前分类
        if current_category and first_cell and not category_pattern.match(first_cell):
            # 检查是否是有效的仪表行（有位号或型号）
            has_valid_content = False
            for cell in row:
                cell_str = str(cell).strip()
                if cell_str and len(cell_str) > 1:
                    has_valid_content = True
                    break
            
            if has_valid_content:
                categories[current_category].append(row_idx)
    
    logger.info(f"从表格中识别到 {len(categories)} 个分类: {list(categories.keys())}")
    return categories

def classify_from_table_position(row_index: int, categories: Dict[str, List[int]]) -> Optional[str]:
    """
    根据行号在表格分类中查找对应的类别
    
    Args:
        row_index: 行号（0基）
        categories: 从表格中提取的分类信息
    
    Returns:
        对应的分类名称，如果找不到返回None
    """
    for category_name, row_indices in categories.items():
        if row_index in row_indices:
            return category_name
    return None

def classify_by_llm(model: str, spec: str = "", context: str = "") -> Optional[str]:
    """
    使用LLM进行仪表分类（当表格中没有明确分类时使用）
    
    Args:
        model: 仪表型号
        spec: 规格信息
        context: 额外上下文信息
    
    Returns:
        LLM分类结果
    """
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        if not settings.get("openai_api_key"):
            logger.warning("未配置OpenAI API Key，跳过LLM分类")
            return "无法识别"
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings["llm_model"],
            api_key=settings["openai_api_key"],
            base_url=settings["openai_base_url"],
            temperature=0.1
        )
        
        prompt = f"""
请根据仪表型号和规格信息判断其类型。

仪表型号：{model}
{f"规格信息：{spec}" if spec else ""}
{f"附加信息：{context}" if context else ""}

请分析这是什么类型的仪表，常见类型包括但不限于：
- 温度仪表（如热电偶、热电阻、温度计等）
- 压力仪表（如压力表、压力变送器等）
- 流量仪表（如流量计、流量变送器等）
- 液位仪表（如液位计、液位变送器等）
- 调节阀门（如气动调节阀、电动调节阀等）
- 控制设备（如控制箱、控制器等）

重要要求：
1. 只有在非常确定的情况下才返回具体的仪表类型
2. 如果型号不常见、规格信息不足、或存在任何不确定性，请直接返回"无法识别"
3. 不要基于部分信息进行猜测
4. 只返回类型名称，不要包含解释

请返回：仪表类型名称 或 "无法识别"
        """
        
        response = llm.invoke(prompt)
        result = response.content.strip()
        
        if result == "无法识别":
            logger.info(f"LLM无法识别仪表类型: {model}")
            return "无法识别"
        else:
            logger.info(f"LLM分类结果: {model} -> {result}")
            return result
            
    except Exception as e:
        logger.error(f"LLM分类时出错: {str(e)}")
        return "无法识别"

def classify_instrument_type(
    model: str, 
    spec: str = "", 
    context: str = "", 
    row_index: int = -1,
    table_categories: Dict[str, List[int]] = None,
    use_llm: bool = True
) -> str:
    """
    对仪表进行分类
    
    Args:
        model: 仪表型号
        spec: 规格信息
        context: 额外的上下文信息（如备注等）
        row_index: 在表格中的行号（0基）
        table_categories: 从表格中提取的分类信息
        use_llm: 是否使用LLM进行分类
    
    Returns:
        仪表类型字符串
    """
    if not model or model.strip() == "":
        return "无法识别"
    
    model = model.strip()
    
    # 优先级1：表格中的明确分类
    if table_categories and row_index >= 0:
        table_result = classify_from_table_position(row_index, table_categories)
        if table_result:
            logger.info(f"表格分类成功: 第{row_index+1}行 {model} -> {table_result}")
            return table_result
    
    # 优先级2：使用LLM分类
    if use_llm:
        llm_result = classify_by_llm(model, spec, context)
        if llm_result and llm_result != "无法识别":
            logger.info(f"LLM分类成功: {model} -> {llm_result}")
            return llm_result
        elif llm_result == "无法识别":
            logger.info(f"LLM明确返回无法识别: {model}")
            return "无法识别"
    
    # 都失败了，返回无法识别
    logger.warning(f"无法分类仪表: 型号={model}, 规格={spec[:50] if spec else '无'}")
    return "无法识别"

def batch_classify_from_table(
    table_data: List[List[str]], 
    model_column: int = 1,  # 型号列的索引
    spec_column: int = 2,   # 规格列的索引
    use_llm: bool = True
) -> Tuple[List[str], Dict[str, List[int]]]:
    """
    从表格数据中批量分类仪表
    
    Args:
        table_data: 表格数据
        model_column: 仪表型号所在的列索引
        spec_column: 规格信息所在的列索引
        use_llm: 是否使用LLM
    
    Returns:
        (分类结果列表, 识别的分类信息)
    """
    # 首先提取表格中的分类信息
    categories = extract_categories_from_table(table_data)
    
    results = []
    for row_idx, row in enumerate(table_data):
        if len(row) <= model_column:
            results.append("无法识别")
            continue
        
        model = str(row[model_column]).strip() if model_column < len(row) else ""
        spec = str(row[spec_column]).strip() if spec_column < len(row) else ""
        
        if not model:
            results.append("无法识别")
            continue
        
        result = classify_instrument_type(
            model=model,
            spec=spec,
            row_index=row_idx,
            table_categories=categories,
            use_llm=use_llm
        )
        results.append(result)
    
    return results, categories

def batch_classify_instruments(
    models: List[str], 
    specs: List[str] = None, 
    table_categories: List[str] = None,
    use_llm: bool = True
) -> List[str]:
    """
    批量分类仪表
    
    Args:
        models: 仪表型号列表
        specs: 规格信息列表（可选）
        table_categories: 表格中的分类信息列表（可选）
        use_llm: 是否使用LLM分类
    
    Returns:
        分类结果列表
    """
    if not models:
        return []
    
    specs = specs or [""] * len(models)
    table_categories = table_categories or [""] * len(models)
    

    
    # 确保所有列表长度一致
    max_len = max(len(models), len(specs), len(table_categories))
    while len(specs) < max_len:
        specs.append("")
    while len(table_categories) < max_len:
        table_categories.append("")
    
    results = []
    for i, model in enumerate(models):
        # 优先使用表格分类
        if i < len(table_categories) and table_categories[i] and table_categories[i].strip():
            result = table_categories[i].strip()
            logger.info(f"使用表格分类: {model} -> {result}")
        else:
            # 使用标准分类逻辑
            spec = specs[i] if i < len(specs) else ""

            result = classify_instrument_type(
                model=model,
                spec=spec,
                use_llm=use_llm
            )
        
        results.append(result)
    
    return results

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 模拟表格数据测试
    test_table = [
        ["位号", "测点名称", "仪表名称及规格", "型号"],
        ["一:", "温度仪表", "", ""],
        ["TE101", "给水温度", "热电阻,分度号Pt100", "WZP-630"],
        ["TE102", "蒸汽温度", "热电偶，分度号K", "WRN-630"],
        ["二:", "压力仪表", "", ""],
        ["PT101", "给水压力", "压力变送器; 量程:0~10MPa", "EJA430A-EBS4A-62DC"],
        ["PT102", "省煤器进口水压力", "压力变送器", "EJA430A-EBS4A-62DC"],
    ]
    
    print("测试表格分类提取:")
    results, categories = batch_classify_from_table(test_table, model_column=3, spec_column=2, use_llm=False)
    
    print(f"识别的分类: {categories}")
    for i, (row, result) in enumerate(zip(test_table, results)):
        if len(row) > 3 and row[3]:  # 有型号的行
            print(f"第{i+1}行: {row[3]} -> {result}")
    
    print("\n仪表分类工具已修复完成") 