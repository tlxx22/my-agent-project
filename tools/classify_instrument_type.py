"""
仪表型号归类工具
简化策略：表格中的明确分类 > LLM分类
"""
import re
from typing import Dict, Optional, List
import logging
from config.settings import INSTRUMENT_TYPE_MAPPING

logger = logging.getLogger(__name__)

# 简化的分类策略：只保留表格分类和LLM分类

def classify_from_table_category(table_category: str) -> Optional[str]:
    """
    使用表格中的明确分类（最高优先级）
    
    Args:
        table_category: 表格中已有的仪表类型
    
    Returns:
        标准化的分类结果，如果无法识别返回None
    """
    if not table_category or table_category.strip() == "" or table_category == "未分类":
        return None
    
    table_category = table_category.strip()
    
    # 直接匹配标准的6大类
    standard_categories = [
        "温度仪表", "压力仪表", "流量仪表", 
        "液位仪表", "两位式电动门控制箱", "气动调节阀"
    ]
    
    if table_category in standard_categories:
        logger.info(f"使用表格分类: {table_category}")
        return table_category
    
    # 对表格分类的适度模糊匹配（只对明确的表格数据）
    table_lower = table_category.lower()
    for std_category in standard_categories:
        std_keywords = std_category.replace("仪表", "").replace("两位式", "").replace("控制箱", "")
        if std_keywords in table_lower:
            logger.info(f"表格分类模糊匹配: '{table_category}' -> {std_category}")
            return std_category
    
    logger.warning(f"无法识别表格分类: {table_category}")
    return None

# 移除了基于规格和型号规则的分类函数，只保留表格分类和LLM分类

def classify_by_llm(model: str, spec: str = "", context: str = "") -> Optional[str]:
    """
    使用LLM进行仪表分类
    
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
            return None
        
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model=settings["llm_model"],
            api_key=settings["openai_api_key"],
            base_url=settings["openai_base_url"],
            temperature=0.1
        )
        
        # 明确指定6大类仪表类型
        valid_types = [
            "温度仪表", "压力仪表", "流量仪表", 
            "液位仪表", "两位式电动门控制箱", "气动调节阀"
        ]
        
        prompt = f"""
请根据仪表型号和规格信息判断其类型，从以下6类中选择最合适的一个：
{', '.join(valid_types)}

仪表型号：{model}
{f"规格信息：{spec}" if spec else ""}
{f"附加信息：{context}" if context else ""}

重要要求：
1. 只有在非常确定的情况下才返回具体的仪表类型
2. 如果型号不常见、规格信息不足、或存在任何不确定性，请直接返回"无法识别"
3. 不要基于部分信息进行猜测
4. 只返回类型名称，不要包含解释

请返回：仪表类型名称 或 "无法识别"
        """
        
        response = llm.invoke(prompt)
        result = response.content.strip()
        
        # 验证结果是否在预期类型中
        if result in valid_types:
            return result
        elif result == "无法识别":
            logger.info(f"LLM无法识别仪表类型: {model}")
            return "无法识别"
        else:
            logger.warning(f"LLM返回了无效的分类结果: {result}")
            return "无法识别"
            
    except Exception as e:
        logger.error(f"LLM分类时出错: {str(e)}")
        return "无法识别"

def classify_instrument_type(
    model: str, 
    spec: str = "", 
    context: str = "", 
    table_category: str = "", 
    use_llm: bool = True
) -> str:
    """
    对仪表进行分类，简化逻辑：表格分类 > LLM分类
    
    Args:
        model: 仪表型号
        spec: 规格信息
        context: 额外的上下文信息（如备注等）
        table_category: 表格中已有的仪表类型（最高优先级）
        use_llm: 是否使用LLM进行分类
    
    Returns:
        仪表类型字符串
    """
    if not model or model.strip() == "":
        return "无法识别"
    
    model = model.strip()
    
    # 1. 最高优先级：表格中的明确分类
    if table_category and table_category.strip():
        table_result = classify_from_table_category(table_category)
        if table_result:
            logger.info(f"表格分类成功: {model} -> {table_result} (来源: {table_category})")
            return table_result
    
    # 2. 使用LLM分类（传入所有可用信息）
    if use_llm:
        llm_result = classify_by_llm(model, spec, context)
        if llm_result and llm_result != "无法识别":
            logger.info(f"LLM分类成功: {model} -> {llm_result}")
            return llm_result
        elif llm_result == "无法识别":
            logger.info(f"LLM明确返回无法识别: {model}")
            return "无法识别"
    
    # 3. 都失败了，返回无法识别
    logger.warning(f"无法分类仪表: 型号={model}, 规格={spec[:50] if spec else '无'}, 表格分类={table_category}")
    return "无法识别"

def batch_classify_instruments(
    models: List[str], 
    specs: List[str] = None, 
    contexts: List[str] = None, 
    table_categories: List[str] = None,
    use_llm: bool = True
) -> List[str]:
    """
    批量分类仪表
    
    Args:
        models: 仪表型号列表
        specs: 对应的规格信息列表
        contexts: 对应的上下文信息列表
        table_categories: 对应的表格分类列表
        use_llm: 是否使用LLM
    
    Returns:
        分类结果列表
    """
    if specs is None:
        specs = [""] * len(models)
    if contexts is None:
        contexts = [""] * len(models)
    if table_categories is None:
        table_categories = [""] * len(models)
    
    results = []
    for model, spec, context, table_cat in zip(models, specs, contexts, table_categories):
        result = classify_instrument_type(model, spec, context, table_cat, use_llm)
        results.append(result)
    
    return results

# 置信度函数已移除，简化的分类策略不需要置信度评估

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试真实数据
    test_data = [
        ("WZP-630", "热电阻,分度号Pt100; 长度Lxl=300x150; 保护管1Cr18Ni9Ti,M33X2", "", "温度仪表"),
        ("WRN-630", "热电偶，分度号K; LXI=300X150; 保护管材料1Cr18Ni9Ti,M33X2", "", "温度仪表"),
        ("WSS-511", "双金属温度计; L=75; M27X2 ，0~300℃，Φ10", "", "温度仪表"),
        ("EJA430A-EBS4A-62DC", "压力变送器; 量程:0~10MPa; 输出信号:4-20mA; 电源:24VDC  两线制", "", "压力仪表"),
        ("Y-150", "压力表; 精度1.5级", "", "压力仪表"),
        ("110C", "气动薄膜式调节阀; 输入输出：4~20mA; 等百分比; 配电气定位器、过滤减压阀、反法兰等附件", "", "气动调节阀")
    ]
    
    print("基于表格分类的测试:")
    for model, spec, context, table_cat in test_data:
        result = classify_instrument_type(model, spec, context, table_cat, use_llm=False)
        print(f"{model} + 表格分类:{table_cat} -> {result}")
    
    print("\n仪表型号归类工具已更新完成") 