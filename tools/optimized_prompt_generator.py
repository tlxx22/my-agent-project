"""
优化后的安装推荐生成器
基于验证实验结果优化的新版本提示词系统
"""
from typing import List, Dict, Optional
import logging
import os
from datetime import datetime
from tools.enhanced_rag_retriever import EnhancedRAGRetriever
from config.settings import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

class OptimizedInstallationGenerator:
    """基于验证结果优化的安装推荐生成器"""
    
    def __init__(self, model_name: str = None, auto_save: bool = True):
        """初始化优化版生成器"""
        self.model_name = model_name or LLM_MODEL
        self.retriever = EnhancedRAGRetriever()
        self.auto_save = auto_save
        
        # 确保输出目录存在
        self.output_dir = "./recommendation"
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("🚀 优化版安装推荐生成器已启动（基于验证反馈优化）")
        
        # 基于验证结果的优化系统提示词
        self.system_prompt = """你是专业的仪表工程师，负责生成安全、实用的安装推荐。请遵循以下原则：

**核心原则：**
1. **技术准确性优先**：只提供有把握的技术信息，包括标准规格、材料要求、安全规范
2. **承认知识边界**：对于具体操作细节、特殊工具使用、精确扭矩值等，如不确定请给出通用建议并引导查阅手册
3. **引导专业咨询**：明确指出需要查阅产品手册、相关标准或咨询现场工程师的情况
4. **安全第一**：重点突出安全风险识别和防护要求，确保人员和设备安全

**内容要求：**
- 提供框架性的技术指导和安全要点
- 给出通用的操作原则，避免虚构具体参数
- 重点突出安全风险识别和防护要求
- 明确标注需要进一步确认的技术细节
- 提供标准的材料规格和技术要求

**当遇到以下情况时，请采用保守原则：**
- 具体操作步骤：给出一般性流程，然后说明"详细操作步骤请参考产品安装手册或咨询设备供应商"
- 精确参数值：提供标准范围，然后说明"具体数值请核对产品技术规格书"
- 特殊工具要求：说明工具类型，然后说明"具体工具选择和使用方法请咨询设备供应商"
- 现场适配问题：给出一般要求，然后说明"现场具体条件请由专业工程师评估确认"
- 经济性分析：说明"成本分析和投资预算需根据具体项目情况，建议咨询专业工程师"

**输出风格：**
专业、简洁、负责任，明确区分确定的技术要求和需要进一步确认的内容。在不确定的地方明确提醒查阅相关文档或咨询专家。"""

    def _call_llm(self, prompt: str, max_tokens: int = 800) -> str:
        """使用优化后的系统提示词调用LLM"""
        try:
            from openai import OpenAI
            
            if not OPENAI_API_KEY:
                logger.error("未配置OpenAI API Key")
                return "无法生成推荐：未配置API密钥"
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.2  # 降低温度提高一致性
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
        """生成优化后的安装推荐方案"""
        
        # 获取相关规范内容
        comprehensive_standards = self.retriever.get_comprehensive_standards(instrument_type)
        
        # 准备上下文信息
        context_parts = []
        if comprehensive_standards['installation_methods']:
            context_parts.append("相关安装规范:")
            for i, method in enumerate(comprehensive_standards['installation_methods'][:3], 1):
                context_parts.append(f"{i}. {method['content']}")
        
        if comprehensive_standards['material_requirements']:
            context_parts.append("\n材料要求规范:")
            for i, material in enumerate(comprehensive_standards['material_requirements'][:2], 1):
                context_parts.append(f"{i}. {material['content']}")
        
        context = "\n".join(context_parts)
        
        # 优化后的主要推荐提示词
        main_prompt = f"""
为{instrument_type}生成安全可靠的安装推荐方案（{quantity}台）：

**仪表详情：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}  
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

**参考技术规范：**
{context}

**重要要求：**
1. 基于上述规范，只采用与{instrument_type}直接相关的标准内容
2. 对于具体操作细节，如果不确定请引导查阅手册或咨询专家
3. 重点突出安全要求和风险防护
4. 提供框架性指导，避免虚构具体参数

请按以下格式生成：

## 安装位置选择
- **具体位置要求**：
  - [基于标准的一般位置选择原则]
  - [测量精度和代表性要求]
  - [维护便利性考虑]

- **环境条件限制**：
  - [温度、湿度、振动等环境要求]
  - [腐蚀性介质的防护要求]

- **与其他设备的安全距离和干扰防护**：
  - [电磁干扰防护距离]
  - [安全操作空间要求]

- **针对型号{model_spec if model_spec else instrument_type}的特殊位置要求**：
  - [基于型号特性的特殊要求，如不确定请说明需要参考产品手册]

## 安装方式与步骤
- **详细的安装工艺流程**：
  - [一般性安装流程：预处理、安装、调试]
  - [关键注意事项]
  - **注意**：详细操作步骤请参考产品安装手册或咨询设备供应商

- **关键安装尺寸和技术参数**：
  - [标准安装尺寸要求]
  - **注意**：具体数值请核对产品技术规格书

- **连接方式和密封要求**：
  - [标准连接方式]
  - [密封等级和材料要求]

- **型号{model_spec if model_spec else instrument_type}的专用安装工艺**：
  - [基于型号的特殊要求，如不确定请说明需要参考技术文档]

- **质量控制检查点**：
  - [安装质量验收要点]
  - [功能测试要求]

要求：提供框架性指导，对不确定的具体参数明确说明需要查阅相关文档。
        """
        
        main_recommendation = self._call_llm(main_prompt)
        
        # 优化后的材料清单提示词
        material_prompt = f"""
{instrument_type}({quantity}台)标准材料清单：

**仪表信息：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台

**清单要求：**
1. 基于标准规范提供通用材料要求
2. 对于具体规格，请提供标准范围并提醒查阅技术文档
3. 重点关注安全和可靠性要求

请按以下格式列出：

## 主体安装材料
- **{instrument_type}型号**：{model_spec if model_spec else '按实际选型'}
  - **材质等级**：[标准材质要求，具体等级请参考产品规格书]
  - **数量**：{quantity}台
  - **技术标准**：[相关国家或行业标准]
- **专用配件**：[标准配件类型，具体型号请核对产品清单]

## 管路连接材料  
- **管道**：
  - **规格**：[标准管径范围，具体规格请根据工艺要求确定]
  - **材质**：[标准材质要求]
  - **数量**：[按现场布置计算，建议预留10-20%余量]
  - **压力等级**：[根据工艺压力确定，具体请咨询工艺工程师]
- **管件**：[标准弯头、三通等，规格与管道匹配]
- **阀门**：
  - **型号规格**：[标准阀门类型，具体选型请根据工艺要求]
  - **技术要求**：[相关标准要求]

## 电气连接材料
- **电缆**：
  - **型号**：[仪表信号电缆标准型号]
  - **长度**：[根据现场布线需求，请现场测量确定]
  - **防护等级**：[根据环境要求确定，建议不低于IP65]
- **接线盒**：[防护等级和材质要求]
- **穿线管**：[标准规格和防护要求]

## 支架固定材料
- **支架**：
  - **材质**：[标准支架材质]
  - **规格**：[根据设备重量和安装高度确定，建议咨询结构工程师]
- **固定螺栓**：[标准规格，具体长度根据安装条件确定]

**重要说明**：
- 以上为标准材料配置，具体规格和数量需根据现场实际情况确定
- 特殊环境下的材料选择请咨询专业工程师
- 采购前请核对产品技术文档和供应商推荐配置
        """
        
        material_list = self._call_llm(material_prompt, max_tokens=600)
        
        # 优化后的安全要求提示词
        safety_prompt = f"""
{instrument_type}安装安全要求分析：

**设备信息：**
- 类型：{instrument_type}
- 型号：{model_spec if model_spec else '标准型号'}
- 数量：{quantity}台
{f'- 工艺条件：{process_conditions}' if process_conditions else ''}

**安全分析要求：**
基于{instrument_type}的一般特性和安全要求，提供安全指导框架。对于具体安全参数，请引导查阅相关文档。

请按以下格式分析：

## 主要安全风险识别

- **基于{instrument_type}和型号"{model_spec if model_spec else '通用型号'}"特点的关键风险点**
  - [仪表类型的典型风险：如高温、高压、电气、机械等]
  - [环境风险：腐蚀、振动、电磁干扰等]
  - **注意**：具体风险评估请根据现场条件，建议咨询安全工程师

- **工艺过程中的潜在危险因素**
  - [工艺介质的危险性分析]
  - [操作条件的安全影响]

- **设备故障的安全影响分析**
  - [测量失效的后果]
  - [设备故障对工艺安全的影响]

## 安全防护措施

- **具体的安全防护设备和技术措施**
  - [标准防护设备类型]
  - [防护等级要求]
  - **注意**：具体防护设备选择请咨询设备供应商和安全工程师

- **安全联锁和报警系统要求**
  - [报警系统的一般要求]
  - [联锁逻辑的基本原则]
  - **注意**：具体联锁逻辑请由控制系统工程师设计

- **防爆、防腐、防雷等专项防护**
  - [防爆等级的确定原则]
  - [防腐材料的选择要求]
  - [防雷接地的基本要求]
  - **注意**：具体防护等级请根据现场危险区域划分确定

- **针对型号特性的专用安全措施**
  - [基于仪表特性的安全要求]
  - **注意**：型号特定的安全要求请参考产品安全手册

## 施工安全要求

- **安装施工过程的安全操作规程**
  - [一般施工安全要求]
  - [特殊作业的安全注意事项]
  - **注意**：详细的施工安全规程请参考相关安全标准和现场安全管理制度

- **特殊作业的安全防护要求**
  - [高空作业安全要求]
  - [动火作业安全要求（如需要）]
  - [有限空间作业安全要求（如适用）]

**重要提醒**：
- 以上为一般性安全要求，具体安全措施需根据现场实际情况制定
- 涉及人身安全的关键参数请务必咨询专业安全工程师
- 施工前请完成风险评估和安全交底
- 特殊环境下的安全要求请参考相关安全标准和法规
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

    def _save_recommendation_to_file(self, recommendation: Dict[str, str]) -> str:
        """保存推荐到文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            instrument_type = recommendation.get('instrument_type', '未知仪表')
            safe_instrument_type = "".join(c for c in instrument_type if c.isalnum() or c in ['_', '-'])
            filename = f"{timestamp}_{safe_instrument_type}_优化推荐.md"
            filepath = os.path.join(self.output_dir, filename)
            
            # 格式化内容
            formatted_content = self._format_recommendation_report(recommendation)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            logger.info(f"📄 优化版推荐已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存推荐文件时出错: {str(e)}")
            return ""

    def _format_recommendation_report(self, recommendation: Dict[str, str]) -> str:
        """格式化推荐报告"""
        report_parts = [
            f"# {recommendation['instrument_type']}安装推荐方案（优化版）",
            f"\n**仪表型号：** {recommendation.get('model_spec', '标准型号')}",
            f"**数量：** {recommendation.get('quantity', 1)}台",
            f"**生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**版本说明：** 基于验证反馈优化的智能体生成\n",
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
            "- 本推荐基于RAG检索的标准规范结合优化的LLM专业判断生成",
            "- 已根据验证实验反馈优化，更注重实用性和安全性",
            "- 对于具体技术参数，请查阅产品手册或咨询专业工程师",
            "- 实际应用时请结合具体工程情况进行调整"
        ]
        
        return "\n".join(report_parts)

# 测试函数
def test_optimized_generator():
    """测试优化版生成器"""
    print("🧪 测试优化版安装推荐生成器...")
    
    generator = OptimizedInstallationGenerator(auto_save=True)
    
    test_case = {
        'instrument_type': '压力表',
        'model_spec': 'EJA120A',
        'quantity': 2,
        'process_conditions': '高压蒸汽系统',
        'custom_requirements': '防爆要求'
    }
    
    try:
        recommendation = generator.generate_installation_recommendation(**test_case)
        print("✅ 优化版推荐生成成功!")
        print(f"📄 保存路径: {recommendation.get('saved_file_path', '未保存')}")
        return True
    except Exception as e:
        print(f"❌ 生成推荐时出错：{str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_optimized_generator() 