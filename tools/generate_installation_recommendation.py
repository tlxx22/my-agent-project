"""
安装方法生成器
使用LLM总结规范内容，生成专业的安装建议
"""
from typing import List, Dict, Optional
import logging
import os
from datetime import datetime
from tools.enhanced_rag_retriever import EnhancedRAGRetriever
from config.settings import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# 导入增强版生成器
try:
    from .enhanced_installation_generator import EnhancedInstallationRecommendationGenerator
    _enhanced_available = True
    logger.info("🔄 检测到增强版生成器，将使用自动保存功能")
except ImportError:
    _enhanced_available = False
    logger.warning("⚠️ 增强版生成器不可用，使用标准版本")

class InstallationRecommendationGenerator:
    """安装方法推荐生成器（兼容性包装器）"""
    
    def __init__(self, model_name: str = None, auto_save: bool = True):
        """
        初始化生成器
        
        Args:
            model_name: 使用的LLM模型名称
            auto_save: 是否自动保存推荐结果为.md文件
        """
        if _enhanced_available and auto_save:
            # 使用增强版生成器
            self._generator = EnhancedInstallationRecommendationGenerator(model_name, auto_save)
            self._use_enhanced = True
            logger.info("🚀 使用增强版安装推荐生成器（支持自动保存）")
        else:
            # 使用标准版本
            self._use_enhanced = False
            self.model_name = model_name or LLM_MODEL
            self.retriever = EnhancedRAGRetriever()
            logger.info("🚀 使用标准版安装推荐生成器")
        
        # 确保recommendation文件夹存在
        self.output_dir = "./recommendation"
        os.makedirs(self.output_dir, exist_ok=True)
        
        if auto_save:
            logger.info(f"📁 自动保存功能已启用，输出目录: {self.output_dir}")
        
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
                        "content": """你是专业的仪表工程师，负责生成安全、实用的安装推荐。请遵循以下原则：

**核心原则：**
1. **技术准确性优先**：只提供有把握的技术信息，包括标准规格、材料要求、安全规范
2. **承认知识边界**：对于具体操作细节、特殊工具使用、精确扭矩值等，如不确定请给出通用建议
3. **引导专业咨询**：明确指出需要查阅产品手册、相关标准或咨询现场工程师的情况

**内容要求：**
- 提供框架性的技术指导和安全要点
- 给出通用的操作原则，避免虚构具体参数
- 重点突出安全风险识别和防护要求
- 明确标注需要进一步确认的技术细节

**当遇到以下情况时，请采用保守原则：**
- 具体操作步骤：给出一般性流程，建议"详细步骤请参考产品安装手册"
- 精确参数值：提供标准范围，建议"具体数值请核对技术规格书"
- 特殊工具：说明类型即可，建议"工具选择请咨询设备供应商"
- 现场适配：给出一般要求，建议"现场条件请由专业工程师评估"

**输出风格：**
专业、简洁、负责任，明确区分确定的技术要求和需要进一步确认的内容。"""
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
        if self._use_enhanced:
            return self._generator.generate_installation_recommendation(
                instrument_type=instrument_type,
                model_spec=model_spec,
                quantity=quantity,
                process_conditions=process_conditions,
                custom_requirements=custom_requirements
            )
        else:
            # 获取相关规范内容
            comprehensive_standards = self.retriever.get_comprehensive_standards(instrument_type)
            
            # 准备格式化的候选标准信息
            context_parts = []
            
            # 安装方法规范
            if comprehensive_standards['installation_methods']:
                context_parts.append("=== 候选安装标准条款 ===")
                for i, method in enumerate(comprehensive_standards['installation_methods'][:5], 1):
                    context_parts.append(f"[标准条款 {i}]")
                    context_parts.append(f"{method['content']}")
                    context_parts.append("---")
            
            # 材料要求规范
            if comprehensive_standards['material_requirements']:
                context_parts.append("\n=== 候选材料要求条款 ===")
                for i, material in enumerate(comprehensive_standards['material_requirements'][:3], 1):
                    context_parts.append(f"[材料条款 {i}]")
                    context_parts.append(f"{material['content']}")
                    context_parts.append("---")
            
            context = "\n".join(context_parts)
            
            # 构建主要推荐提示词
            main_prompt = f"""
为{instrument_type}生成专业的安装推荐方案（{quantity}台）：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

{context}

**重要说明：**
1. 以上每个[标准条款 X]和[材料条款 X]都是独立的候选标准，用"---"分隔
2. 请仔细分析每条标准是否真正适用于{instrument_type}
3. 只采用与{instrument_type}直接相关和适用的标准条款
4. 如果某条标准明显不适用或与其他仪表相关，请忽略
5. **请充分利用您对型号"{model_spec}"的专业知识（如有）**，包括：
   - 该型号的技术特点和适用场景
   - 该型号的安装特殊要求
   - 该型号的常见问题和注意事项
   - 该型号的材料和工艺特性
6. 基于筛选后的相关标准和专业判断生成推荐

请按格式输出（每部分2-3行，基于相关标准和专业知识）：

## 安装位置
[基于相关标准和型号特性的位置选择要点]

## 安装方式  
[基于相关标准和型号特点的关键安装步骤]

## 材料要求
[基于相关标准和型号规格的主要材料规格]

## 注意事项
[基于相关标准、型号特性和专业判断的关键安全要点]

要求：
- 优先使用与{instrument_type}和型号"{model_spec}"真正相关的标准条款
- 结合您对该型号的专业知识，补充标准未覆盖的内容
- 内容简洁专业，突出该型号的特殊要求
- 如果对该型号有专业了解，请在推荐中体现型号特性
            """
            
            # 生成主要推荐内容
            main_recommendation = self._call_llm(main_prompt)
            
            # 生成材料清单
            material_prompt = f"""
{instrument_type}({quantity}台)专业材料清单：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台

参考的材料要求条款：
{context}

**重要说明：**
1. 以上是候选的材料标准条款，用"---"分隔
2. 请筛选出与{instrument_type}真正相关的材料要求
3. **请利用您对型号"{model_spec}"的专业知识**，考虑：
   - 该型号的材料兼容性要求
   - 该型号的安装配件规格
   - 该型号的连接方式和接口标准
   - 该型号的环境适应性材料要求
4. 基于相关标准和型号特性列出材料清单

简洁列出：
## 管路材料
- [基于相关标准和型号特性的规格、数量]

## 电气材料  
- [基于相关标准和型号接口的电缆等规格、数量]

## 辅助材料
- [基于相关标准和型号安装要求的支架等规格、数量]

要求：
- 优先采用与{instrument_type}和型号"{model_spec}"相关的材料标准
- 如果您了解该型号的特殊材料要求，请在清单中体现
- 标注关键规格参数和型号兼容性
- 基于专业判断补充必要的专用材料
            """
            
            material_list = self._call_llm(material_prompt, max_tokens=300)
            
            # 生成安全要求
            safety_prompt = f"""
{instrument_type}安装安全要求分析：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

参考的安全标准条款：
{context}

**重要说明：**
1. 以上是候选的标准条款，请筛选与{instrument_type}安全相关的内容
2. **请利用您对型号"{model_spec}"的专业知识**，考虑：
   - 该型号的安全等级和防护要求
   - 该型号的工作环境限制
   - 该型号的故障模式和预防措施
   - 该型号的维护安全注意事项
3. 基于相关标准和型号特性制定安全要求

简洁输出：
## 主要风险
[基于{instrument_type}和型号"{model_spec}"特点的关键风险点]

## 防护措施
[基于相关标准和型号特性的重要防护要求]

## 注意事项
[基于相关标准、型号特性和专业判断的安全操作要点]

要求：
- 突出{instrument_type}和型号"{model_spec}"特有的安全风险
- 如果您了解该型号的安全特性，请在要求中体现
- 采用相关和适用的安全标准
- 提供针对该型号的实用防护措施
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
        if self._use_enhanced:
            return self._generator.generate_batch_recommendation(instruments_summary)
        else:
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