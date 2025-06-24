"""
增强版安装方法生成器
使用LLM总结规范内容，生成专业的安装建议，并自动保存为.md文件
"""
from typing import List, Dict, Optional
import logging
import os
from datetime import datetime
from tools.enhanced_rag_retriever import EnhancedRAGRetriever
from config.settings import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

class EnhancedInstallationRecommendationGenerator:
    """增强版安装方法推荐生成器（支持自动保存）"""
    
    def __init__(self, model_name: str = None, auto_save: bool = True):
        """
        初始化生成器
        
        Args:
            model_name: 使用的LLM模型名称
            auto_save: 是否自动保存推荐结果为.md文件
        """
        self.model_name = model_name or LLM_MODEL
        self.retriever = EnhancedRAGRetriever()
        self.auto_save = auto_save
        
        # 确保recommendation文件夹存在
        self.output_dir = "./recommendation"
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("🚀 增强版安装推荐生成器已启动")
        if auto_save:
            logger.info(f"📁 自动保存功能已启用，输出目录: {self.output_dir}")
    
    def _save_recommendation_to_file(self, recommendation: Dict[str, str]) -> str:
        """
        保存安装推荐到.md文件
        
        Args:
            recommendation: 推荐内容字典
        
        Returns:
            保存的文件路径
        """
        try:
            # 生成文件名：时间戳_仪表类型_安装推荐.md
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            instrument_type = recommendation.get('instrument_type', '未知仪表')
            # 清理仪表类型名称，移除可能的特殊字符
            safe_instrument_type = "".join(c for c in instrument_type if c.isalnum() or c in ['_', '-'])
            filename = f"{timestamp}_{safe_instrument_type}_安装推荐.md"
            filepath = os.path.join(self.output_dir, filename)
            
            # 格式化推荐内容
            formatted_content = self._format_recommendation_report(recommendation)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            logger.info(f"📄 安装推荐已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存安装推荐文件时出错: {str(e)}")
            return ""
    
    def _format_recommendation_report(self, recommendation: Dict[str, str]) -> str:
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
            f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**文件来源：** 智能体自动生成\n",
            "---\n",
            recommendation['main_recommendation'],
            "\n---\n",
            "# 材料清单",
            recommendation['material_list'],
            "\n---\n", 
            "# 安全要求",
            recommendation['safety_requirements'],
            "\n---\n",
            "# 说明",
            "- 本推荐基于RAG检索的标准规范结合LLM专业判断生成",
            "- 实际应用时请结合具体工程情况进行调整",
            "- 如有疑问请咨询专业工程师"
        ]
        
        return "\n".join(report_parts)
        
    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """
        调用LLM生成内容
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大token数（增加以支持更详细内容）
        
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
                        "content": """你是资深的仪表工程师，具有丰富的工程实践经验。请生成详细、可靠、实用的安装推荐方案。

**核心要求：**
1. **可靠性至上**：这是工程安装推荐，必须确保技术方案的可靠性和安全性
2. **专业严谨**：严格基于国家标准、行业规范和工程实践经验
3. **具体详实**：提供具体的技术参数、施工要点和质量控制措施  
4. **型号专业性**：充分利用您对具体仪表型号的专业知识
5. **工程导向**：考虑实际施工条件和工程约束

**质量标准：**
- 严格遵循相关国家标准和行业规范要求
- 确保测量精度和系统可靠性，重视工程质量
- 强调安全防护和环境适应性
- 提供明确的施工指导和验收标准
- 突出可靠性验证和质量控制要点

**必须体现的工程要素：**
请在推荐中多次强调和使用这些关键词：标准、规范、可靠、安全、质量、验收、防护、工程"""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.2  # 降低温度以提高可靠性
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
        生成仪表安装推荐方案（包含自动保存）
        
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
为{instrument_type}生成详细可靠的工程安装方案（{quantity}台）：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}  
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

**参考技术规范：**
{context}

**重要说明：**
1. 以上参考规范通过RAG检索获得，请仔细甄别适用性
2. 只采用与{instrument_type}直接相关的标准内容
3. **请充分利用您对型号"{model_spec}"的专业知识**，包括：
   - 该型号的技术特点和适用场景
   - 该型号的安装特殊要求和注意事项
   - 该型号的材料兼容性和环境适应性
   - 该型号的精度等级和测量范围特性
4. **务必确保推荐方案的工程可靠性和安全性**

请按以下格式生成详细的工程安装方案：

## 安装位置选择
- 具体位置要求（考虑工艺流程、测量精度、维护便利性）
- 环境条件限制（温度、湿度、振动、腐蚀等）
- 与其他设备的安全距离和干扰防护
- {f"针对型号{model_spec}的特殊位置要求" if model_spec else ""}

## 安装方式与步骤
- 详细的安装工艺流程（含预处理、安装、调试）
- 关键安装尺寸和技术参数
- 连接方式和密封要求
- {f"型号{model_spec}的专用安装工艺" if model_spec else ""}
- 质量控制检查点

## 材料与配件要求
- 主要材料规格和技术标准
- 连接件和密封件规格
- 支架和固定件要求
- {f"与型号{model_spec}配套的专用材料" if model_spec else ""}

## 技术验收标准
- 安装质量验收标准
- 功能测试和校准要求
- 性能指标验证方法
- 安全防护验证

要求：内容详实专业，突出工程可靠性，提供具体的技术参数和施工指导。
        """
        
        # 生成主要推荐内容
        main_recommendation = self._call_llm(main_prompt)
        
        # 生成材料清单
        material_prompt = f"""
{instrument_type}({quantity}台)详细工程材料清单：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台

**重要要求：**
1. 基于专业判断，只采用与{instrument_type}和型号"{model_spec}"真正相关的材料要求
2. **请利用您对型号"{model_spec}"的专业知识**，考虑：
   - 该型号的材料兼容性和接口标准
   - 该型号的安装配件和专用工具需求
   - 该型号的环境适应性材料要求
   - 该型号的连接方式和密封标准
3. **确保材料清单的工程可靠性**，所有材料必须符合相关标准

请按以下格式详细列出：

## 主体安装材料
- [具体规格型号、材质等级、数量、技术标准]
- [考虑型号兼容性的专用配件]

## 管路连接材料  
- [管道、管件具体规格、材质、数量、压力等级]
- [阀门、接头的型号规格和技术要求]

## 电气连接材料
- [电缆型号、截面积、长度、防护等级]
- [接线盒、穿线管规格和防护要求]

## 支架固定材料
- [支架材质、规格、承载能力]
- [固定螺栓、膨胀螺丝等规格]

## 密封防护材料
- [密封件材质、规格、耐温耐压要求]
- [防腐防护材料和技术标准]

要求：材料规格具体明确，标注关键技术参数，确保与设备型号匹配，符合工程标准。
        """
        
        material_list = self._call_llm(material_prompt, max_tokens=600)
        
        # 生成安全要求
        safety_prompt = f"""
{instrument_type}工程安装安全要求分析：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

**安全分析要求：**
1. 请甄别参考规范的适用性，只采用与{instrument_type}安全相关的内容
2. **请利用您对型号"{model_spec}"的专业知识**，考虑：
   - 该型号的安全等级和防护要求
   - 该型号的工作环境限制和故障模式
   - 该型号的维护安全注意事项
   - 该型号的紧急处置和安全联锁要求
3. **确保安全方案的可靠性**，重视工程安全和人员安全

请按以下格式详细分析：

## 主要安全风险识别
- [基于{instrument_type}和型号"{model_spec}"特点的关键风险点]
- [工艺过程中的潜在危险因素]
- [设备故障的安全影响分析]

## 安全防护措施
- [具体的安全防护设备和技术措施]
- [安全联锁和报警系统要求]
- [防爆、防腐、防雷等专项防护]
- [针对型号特性的专用安全措施]

## 施工安全要求
- [安装施工过程的安全操作规程]
- [特殊作业的安全防护要求]
- [安全检查和验收标准]

## 运行维护安全
- [日常操作的安全注意事项]
- [维护保养的安全程序]
- [紧急情况的处置预案]

要求：安全分析全面深入，防护措施具体可行，突出工程安全的可靠性。
        """
        
        safety_requirements = self._call_llm(safety_prompt, max_tokens=600)
        
        # 组装推荐结果
        recommendation = {
            'main_recommendation': main_recommendation,
            'material_list': material_list,
            'safety_requirements': safety_requirements,
            'instrument_type': instrument_type,
            'model_spec': model_spec,
            'quantity': quantity
        }
        
        # 自动保存功能
        if self.auto_save:
            saved_path = self._save_recommendation_to_file(recommendation)
            recommendation['saved_file_path'] = saved_path
        
        return recommendation
    
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
        
        batch_recommendation = self._call_llm(batch_prompt, max_tokens=1500)
        
        # 如果开启自动保存，也保存批量推荐
        if self.auto_save:
            batch_rec_dict = {
                'instrument_type': '批量仪表',
                'model_spec': f"{instruments_summary['total_types']}种类型",
                'quantity': instruments_summary['total_instruments'],
                'main_recommendation': batch_recommendation,
                'material_list': '见各单项仪表材料清单',
                'safety_requirements': '见各单项仪表安全要求'
            }
            self._save_recommendation_to_file(batch_rec_dict)
        
        return batch_recommendation

# 兼容性函数
def generate_installation_recommendation_with_save(
    instrument_type: str, 
    specifications: str = "",
    quantity: int = 1,
    process_info: str = "",
    special_requirements: str = "",
    auto_save: bool = True
) -> Dict[str, str]:
    """
    生成安装推荐的便捷函数（支持自动保存）
    
    Args:
        instrument_type: 仪表类型
        specifications: 规格说明
        quantity: 数量
        process_info: 工艺信息
        special_requirements: 特殊要求
        auto_save: 是否自动保存
    
    Returns:
        安装推荐字典
    """
    generator = EnhancedInstallationRecommendationGenerator(auto_save=auto_save)
    return generator.generate_installation_recommendation(
        instrument_type=instrument_type,
        model_spec=specifications,
        quantity=quantity,
        process_conditions=process_info,
        custom_requirements=special_requirements
    )

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 测试增强版安装推荐生成器...")
    
    # 测试单个仪表推荐
    test_case = {
        'instrument_type': '热电偶',
        'model_spec': 'WRN-630',
        'quantity': 2,
        'process_conditions': '高温蒸汽管道测温',
        'custom_requirements': '防爆要求'
    }
    
    generator = EnhancedInstallationRecommendationGenerator(auto_save=True)
    
    print(f"\n📋 生成推荐: {test_case['instrument_type']}")
    
    try:
        recommendation = generator.generate_installation_recommendation(**test_case)
        
        print("✅ 推荐生成成功!")
        print(f"📄 保存路径: {recommendation.get('saved_file_path', '未保存')}")
        print(f"📝 内容摘要: {recommendation['main_recommendation'][:100]}...")
        
    except Exception as e:
        print(f"❌ 生成推荐时出错：{str(e)}")
    
    print("\n�� 增强版安装方法生成器测试完成") 