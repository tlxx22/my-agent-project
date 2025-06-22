"""
安装方法生成器
使用LLM总结规范内容，生成专业的安装建议
"""
from typing import List, Dict, Optional
import logging
from tools.match_standard_clause import StandardClauseRetriever
from config.settings import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

class InstallationRecommendationGenerator:
    """安装方法推荐生成器"""
    
    def __init__(self, model_name: str = None):
        """
        初始化生成器
        
        Args:
            model_name: 使用的LLM模型名称
        """
        self.model_name = model_name or LLM_MODEL
        self.retriever = StandardClauseRetriever()
        
    def _call_llm(self, prompt: str, max_tokens: int = 400) -> str:
        """
        调用LLM生成内容
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大token数
        
        Returns:
            生成的文本内容
        """
        try:
            from openai import OpenAI
            
            if not OPENAI_API_KEY:
                logger.error("未配置OpenAI API Key")
                return "无法生成推荐：未配置API密钥"
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是专业的仪表工程师。请生成简洁实用的安装建议，重点突出关键技术要点，避免冗长描述。"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"调用LLM时出错: {str(e)}")
            return f"生成推荐时出现错误: {str(e)}"
    
    def generate_installation_recommendation(
        self, 
        instrument_type: str, 
        model_spec: str = "", 
        quantity: int = 1,
        process_conditions: str = "",
        custom_requirements: str = ""
    ) -> Dict[str, str]:
        """
        生成仪表安装推荐方案
        
        Args:
            instrument_type: 仪表类型
            model_spec: 仪表型号规格
            quantity: 数量
            process_conditions: 工艺条件描述
            custom_requirements: 特殊要求
        
        Returns:
            包含安装方案各部分的字典
        """
        # 获取相关规范内容
        comprehensive_standards = self.retriever.get_comprehensive_standards(instrument_type)
        
        # 准备上下文信息
        context_parts = []
        
        # 安装方法规范
        if comprehensive_standards['installation_methods']:
            context_parts.append("相关安装规范:")
            for i, method in enumerate(comprehensive_standards['installation_methods'][:3], 1):
                context_parts.append(f"{i}. {method['content']}")
        
        # 材料要求规范
        if comprehensive_standards['material_requirements']:
            context_parts.append("\n材料要求规范:")
            for i, material in enumerate(comprehensive_standards['material_requirements'][:2], 1):
                context_parts.append(f"{i}. {material['content']}")
        
        context = "\n".join(context_parts)
        
        # 构建主要推荐提示词
        main_prompt = f"""
为{instrument_type}生成简洁的安装方案（{quantity}台）：

型号：{model_spec if model_spec else '标准型号'}
{f'工艺条件：{process_conditions}' if process_conditions else ''}

参考规范：
{context}

请按格式输出（每部分2-3行）：

## 安装位置
[位置选择要点]

## 安装方式  
[关键安装步骤]

## 材料要求
[主要材料规格]

## 注意事项
[关键安全要点]

要求：内容简洁、突出要点、实用性强。
        """
        
        # 生成主要推荐内容
        main_recommendation = self._call_llm(main_prompt)
        
        # 生成材料清单
        material_prompt = f"""
{instrument_type}({quantity}台)安装材料清单：

型号：{model_spec if model_spec else '标准型号'}

简洁列出：
## 管路材料
- [规格、数量]

## 电气材料  
- [电缆等规格、数量]

## 辅助材料
- [支架等规格、数量]

要求：简洁明了，标注关键规格。
        """
        
        material_list = self._call_llm(material_prompt, max_tokens=300)
        
        # 生成安全要求
        safety_prompt = f"""
{instrument_type}安装安全要求：

数量：{quantity}台
{f'工艺条件：{process_conditions}' if process_conditions else ''}

简洁输出：
## 主要风险
[关键风险点]

## 防护措施
[重要防护要求]

## 注意事项
[安全操作要点]

要求：简洁实用，突出重点。
        """
        
        safety_requirements = self._call_llm(safety_prompt, max_tokens=250)
        
        return {
            'main_recommendation': main_recommendation,
            'material_list': material_list,
            'safety_requirements': safety_requirements,
            'instrument_type': instrument_type,
            'model_spec': model_spec,
            'quantity': quantity
        }
    
    def generate_batch_recommendation(self, instruments_summary: Dict) -> str:
        """
        为多种仪表生成批量安装建议
        
        Args:
            instruments_summary: 仪表汇总信息字典
        
        Returns:
            批量安装建议文本
        """
        if not instruments_summary or 'type_distribution' not in instruments_summary:
            return "无有效的仪表信息，无法生成建议。"
        
        # 构建批量建议提示词
        instrument_info = []
        for instrument_type, count in instruments_summary['type_distribution'].items():
            if count > 0:
                instrument_info.append(f"- {instrument_type}：{count}台")
        
        batch_prompt = f"""
请为以下仪表清单制定综合安装方案：

仪表清单：
{chr(10).join(instrument_info)}

总计：{instruments_summary['total_instruments']}台仪表，{instruments_summary['total_types']}种类型

请生成：

## 项目概况
[项目规模分析和特点]

## 安装策略
[分阶段安装建议和优先级]

## 资源配置建议
[人员、设备、材料配置建议]

## 进度安排建议
[合理的施工进度安排]

## 质量控制要点
[关键质量控制措施]

## 风险管控
[项目风险识别和应对措施]

要求：
1. 考虑仪表类型的协调性
2. 优化施工组织方案
3. 突出关键控制点
4. 语言专业简洁
        """
        
        return self._call_llm(batch_prompt, max_tokens=1000)
    
    def generate_maintenance_plan(self, instrument_type: str, quantity: int = 1) -> str:
        """
        生成维护保养计划
        
        Args:
            instrument_type: 仪表类型
            quantity: 数量
        
        Returns:
            维护保养计划文本
        """
        maintenance_prompt = f"""
请为{quantity}台{instrument_type}制定专业的维护保养计划：

## 日常维护
[日常检查项目和周期]

## 定期保养
[定期保养内容和时间间隔]

## 专项检修
[专项检修项目和年度安排]

## 备品备件
[推荐的备品备件清单]

## 维护记录
[需要记录的关键参数和项目]

要求内容实用，便于执行。
        """
        
        return self._call_llm(maintenance_prompt, max_tokens=600)

def generate_installation_recommendation(
    instrument_type: str, 
    specifications: str = "",
    quantity: int = 1,
    process_info: str = "",
    special_requirements: str = ""
) -> Dict[str, str]:
    """
    生成安装推荐的便捷函数
    
    Args:
        instrument_type: 仪表类型
        specifications: 规格说明
        quantity: 数量
        process_info: 工艺信息
        special_requirements: 特殊要求
    
    Returns:
        安装推荐字典
    """
    generator = InstallationRecommendationGenerator()
    return generator.generate_installation_recommendation(
        instrument_type=instrument_type,
        model_spec=specifications,
        quantity=quantity,
        process_conditions=process_info,
        custom_requirements=special_requirements
    )

def format_recommendation_report(recommendation: Dict[str, str]) -> str:
    """
    格式化推荐报告为完整文档
    
    Args:
        recommendation: 推荐内容字典
    
    Returns:
        格式化的完整报告
    """
    report_parts = [
        f"# {recommendation['instrument_type']}安装推荐方案",
        f"\n**仪表型号：** {recommendation.get('model_spec', '标准型号')}",
        f"**数量：** {recommendation.get('quantity', 1)}台",
        f"**生成时间：** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        recommendation['main_recommendation'],
        "\n---\n",
        "# 材料清单",
        recommendation['material_list'],
        "\n---\n", 
        "# 安全要求",
        recommendation['safety_requirements']
    ]
    
    return "\n".join(report_parts)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 测试单个仪表推荐
    print("测试仪表安装推荐生成...")
    
    test_cases = [
        {
            'instrument_type': '热电偶',
            'model_spec': 'WRN-630',
            'quantity': 2,
            'process_conditions': '高温蒸汽管道测温',
            'custom_requirements': '防爆要求'
        },
        {
            'instrument_type': '压力表',
            'model_spec': 'Y-100',
            'quantity': 1,
            'process_conditions': '常温水管压力监测',
            'custom_requirements': ''
        }
    ]
    
    generator = InstallationRecommendationGenerator()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试案例 {i}: {test_case['instrument_type']}")
        print('='*60)
        
        try:
            recommendation = generator.generate_installation_recommendation(**test_case)
            
            # 显示推荐摘要
            main_rec = recommendation['main_recommendation']
            if len(main_rec) > 200:
                print(f"主要推荐：{main_rec[:200]}...")
            else:
                print(f"主要推荐：{main_rec}")
                
            print(f"材料清单长度：{len(recommendation['material_list'])}字符")
            print(f"安全要求长度：{len(recommendation['safety_requirements'])}字符")
            
        except Exception as e:
            print(f"生成推荐时出错：{str(e)}")
    
    print("\n安装方法生成器已就绪") 