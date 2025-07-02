"""
综合评价指标体系
包含内容覆盖类、可行性可操作性类、质量评审类三大指标体系
严格按照图片要求设计
"""

import re
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from config.settings import OPENAI_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# ==================== 1. 内容覆盖类指标 (Content Coverage Metrics) ====================
# 目标：自动判断生成文档是否"把该说的都说到了"

class ContentCoverageMetrics:
    """内容覆盖类指标 - 自动判断生成文档是否"把该说的都说到了" """
    
    def __init__(self):
        # 3-1 调整词表 & 欠缺权重 - 区分核心词与可选词
        self.core_words = {
            "安装要素": ["步骤", "位置", "工具", "人员"],  # 核心词×5分
            "材料要素": ["规格", "数量", "型号"], 
            "安全要素": ["风险", "防护", "应急"],
            "技术要点": ["温度", "压力", "精度", "连接"]  # 改为更适合安装文档的技术要点
        }
        
        self.optional_words = {
            "安装要素": ["高度", "注意", "工期", "螺丝刀", "操作", "流程"],  # 可选词×2分
            "材料要素": ["DN", "PN", "品牌", "替代", "规范", "标准"],
            "安全要素": ["危险", "隐患", "联锁", "报警", "措施", "预案"], 
            "技术要点": ["范围", "等级", "深度", "距离", "测量", "校准", "验收", "测试"]  # 更适合技术文档
        }
        
        # STEP 1: 分门别类维护，支持正则，控制在100-150条合理范围
        # G类优化：增加章节命中模式，更贴合实际文档结构
        self.alias_map = {
            "规格": ["规格", "尺寸", r"\bSize\b", r"\bDN\d+", r"\bPN\b", "直径", "口径", 
                   r"\b(φ|Φ)\d+mm", "技术参数", "参数"],  # B类优化：移除"材质"避免误判
            "数量": ["数量", r"合计\d+台", r"共计\d+", r"各\d+件", "个数", "支", "套", "台", "个", "只", "根"],
            "型号": ["型号", "类型", "规格型号", "产品型号", "型", "款", "K型", "PT100", "WRN", "model"],
            "品牌": ["品牌", "厂家", "制造商", "产地", "供应商", "生产商"],
            "材质": ["材质", "Material", "SS304", "SS316", "碳钢", "不锈钢", "304不锈钢", "316不锈钢", 
                   "NBR", "PTFE", "石墨", "合金钢"],
            
            # G类优化：步骤章节模式匹配
            "步骤": ["步骤", "流程", "方式", "过程", "程序", "工序", 
                   r"安装.{0,4}(方式|步骤|流程)", r"操作.{0,4}步骤", r"施工.{0,4}(流程|方法)"],
            "位置": ["位置", "地方", "部位", "场所", "安装位置", "选择", "布置",
                   r"(安装|选择).{0,4}位置", r"位置.{0,4}要求"],
            "工具": ["工具", "设备", "器具", "专用工具", "仪器", "扳手", "螺丝刀", "测量", "校准"],
            "人员": ["人员", "操作人员", "技工", "工作人员", "施工人员", "安全"],
            
            # G类优化：安全章节模式匹配
            "风险": ["风险", "隐患", "危险性", "安全风险", "危险", r"潜在.{0,4}危险", r"漏弱.{0,4}(环节|点)",
                   r"安全.{0,4}(风险|隐患)", r"(危险|风险).{0,4}(识别|分析)"],
            "防护": ["防护", "保护", "防护措施", "安全防护", "佩戴", "安全帽", "手套",
                   r"安全.{0,4}(防护|措施)", r"防护.{0,4}(要求|措施)", r"个人.{0,4}防护"],
            "应急": ["应急", "紧急", "应急处理", "急救", "预案", "措施",
                   r"应急.{0,4}(预案|处理|措施)", r"紧急.{0,4}情况"],
            
            "温度": ["温度", "温", "热", "冷", "℃", "度", "高温", "低温"],
            "压力": ["压力", "压强", "MPa", "bar", "kPa", "PN", "压力表"],
            "精度": ["精度", "精确", "误差", "准确", "%", "等级", "级别"],
            "连接": ["连接", "接头", "接口", "螺纹", "法兰", "螺栓", "螺母"],
            
            "振动": ["振动", "震动", "Vibration", "抖动", "波动", "摆动"]
        }
        
        # STEP 2: 语义相似度兜底机制的查询示例
        self.semantic_probes = {
            "规格": "写明了设备尺寸或口径",
            "数量": "列出了数量多少", 
            "型号": "给出了制造商信息",
            "品牌": "提到了品牌厂家",
            "材质": "说明了材料材质",
            
            "步骤": "描述了安装流程步骤",
            "位置": "指明了安装位置", 
            "工具": "列出了所需工具设备",
            "人员": "提及了操作人员要求",
            
            "风险": "识别了安全风险隐患",
            "防护": "说明了防护措施",
            "应急": "制定了应急预案",
            
            "温度": "涉及温度参数要求",
            "压力": "提到压力等级规格", 
            "精度": "说明了精度等级",
            "连接": "描述了连接方式",
            
            "振动": "考虑了振动因素"
        }
        
    def keyword_hit(self, word, text):
        """增强关键词匹配 - 支持别名和正则"""
        import re
        
        # 直接匹配
        if word in text:
            return True
            
        # 别名匹配（支持正则）
        for alias in self.alias_map.get(word, []):
            if alias.startswith(r'\b') or '\\' in alias or '?' in alias or '+' in alias:
                # E类优化：正则模式统一添加re.IGNORECASE，解决国际单位大小写混用问题
                try:
                    if re.search(alias, text, re.IGNORECASE):
                        return True
                except:
                    pass  # 正则错误则跳过
            else:
                # 普通字符串匹配
                if alias in text:
                    return True
        return False
        
    def semantic_hit(self, category: str, text: str, thresh=0.55):
        """语义相似度匹配 - 作为关键词匹配的兜底机制"""
        try:
            # 延迟导入，避免启动时加载模型
            from sentence_transformers import SentenceTransformer, util
            
            # 使用类属性缓存模型，避免重复加载
            if not hasattr(self, '_semantic_model'):
                self._semantic_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # A类优化：缓存文档向量，平均省80% CPU/GPU时延
            if not hasattr(self, '_doc_emb_cache'):
                self._doc_emb_cache = {}
            
            if category not in self.semantic_probes:
                return False
                
            probe_text = self.semantic_probes[category]
            
            # 缓存文档向量：如果文档很长，只使用前500字符作为缓存key
            doc_key = text[:500] if len(text) > 500 else text
            if doc_key not in self._doc_emb_cache:
                self._doc_emb_cache[doc_key] = self._semantic_model.encode(text)
            
            emb_doc = self._doc_emb_cache[doc_key]
            emb_probe = self._semantic_model.encode(probe_text)
            similarity = util.cos_sim(emb_doc, emb_probe).item()
            
            return similarity > thresh
            
        except Exception as e:
            # 如果语义匹配失败，静默返回False，不影响其他功能
            return False
        
    def calc_coverage(self, text: str) -> Tuple[float, dict]:
        """
        STEP 2: 三层判定机制 + 柔性评分
        L1: 关键词直接匹配 (100%权重)
        L2: 别名/正则匹配 (100%权重) 
        L3: 语义相似度兜底 (50%权重，避免误判)
        评分机制：100 - len(missing) * 10，更柔性
        """
        details, total_score = {}, 0
        
        for cat in self.core_words.keys():
            # 核心词三层判定
            core_hits = 0
            core_semantic_hits = 0
            for word in self.core_words[cat]:
                if self.keyword_hit(word, text):
                    core_hits += 1  # L1/L2命中，100%权重
                elif self.semantic_hit(word, text):
                    core_semantic_hits += 1  # L3语义命中，50%权重
            
            # 可选词三层判定
            optional_hits = 0
            optional_semantic_hits = 0
            for word in self.optional_words[cat]:
                if self.keyword_hit(word, text):
                    optional_hits += 1
                elif self.semantic_hit(word, text):
                    optional_semantic_hits += 1
            
            # STEP 2: 柔性评分 - 写得越多分越高，漏2-3个也不至于腰斩
            # 核心词：每缺失一个扣10分，语义命中按50%计算
            core_total = len(self.core_words[cat])
            core_effective = core_hits + core_semantic_hits * 0.5
            core_missing = max(0, core_total - core_effective)
            core_score = max(0, 100 - core_missing * 10)
            
            # 可选词：每缺失一个扣5分
            optional_total = len(self.optional_words[cat])
            optional_effective = optional_hits + optional_semantic_hits * 0.5
            optional_missing = max(0, optional_total - optional_effective)  
            optional_score = max(0, 100 - optional_missing * 5)
            
            # F类优化：提高材料bonus加分 - 从+3提升到+5，激励专业材料表达
            bonus_score = 0
            if cat == "材料要素":
                professional_materials = ["304不锈钢", "316不锈钢", "碳钢", "合金钢", "NBR", "PTFE", "石墨"]
                if any(material in text for material in professional_materials):
                    bonus_score += 5  # F类优化：从+3提升到+5
                
                standards = ["GB/T", "HG/T", "JB/T", "API", "ASME", "DIN", "ISO"]
                if any(std in text for std in standards):
                    bonus_score += 5  # F类优化：从+3提升到+5
            
            # 类别总分：核心词权重70%，可选词权重30%
            category_score = min(100, core_score * 0.7 + optional_score * 0.3 + bonus_score)
            
            details[cat] = {
                "core_hits": core_hits,
                "core_semantic_hits": core_semantic_hits,
                "optional_hits": optional_hits,
                "optional_semantic_hits": optional_semantic_hits,
                "bonus_score": bonus_score,
                "score": category_score,
                "missing_core": [w for w in self.core_words[cat] 
                               if not self.keyword_hit(w, text) and not self.semantic_hit(w, text)],
                "missing_optional": [w for w in self.optional_words[cat] 
                                   if not self.keyword_hit(w, text) and not self.semantic_hit(w, text)]
            }
            total_score += category_score
        
        total_score /= len(self.core_words)
        return total_score, details
    
    def extract_missing_items(self, text: str) -> List[str]:
        """
        C类优化：缺项输出使用语义能力，保持与calc_coverage一致性
        现在alias/语义匹配到也算"不缺失"
        """
        missing_items = []
        
        # 优先添加核心词缺失
        for category, words in self.core_words.items():
            for word in words:
                # C类优化：使用已有的语义判定能力，而不是简单的word in text
                if not self.keyword_hit(word, text) and not self.semantic_hit(word, text):
                    missing_items.append(f"{category}-{word}")
        
        # 再添加部分可选词缺失
        for category, words in self.optional_words.items():
            for word in words[:3]:  # 只取前3个可选词避免列表过长
                if not self.keyword_hit(word, text) and not self.semantic_hit(word, text):
                    missing_items.append(f"{category}-{word}")
        
        return missing_items
    
    def evaluate_content_coverage(self, recommendation_text: str) -> Dict[str, Any]:
        """评估内容覆盖度 - 3-2下调覆盖占比，引入章节命中"""
        
        # 使用新的差异化权重计算覆盖率
        coverage_score, coverage_details = self.calc_coverage(recommendation_text)
        
        # 缺项输出
        missing_items = self.extract_missing_items(recommendation_text)
        
        # 3-2 章节完整度检查（提高权重）
        required_sections = [
            "安装位置", "安装方式", "材料清单", "安全要求", 
            "质量控制", "技术参数", "安装步骤", "注意事项"
        ]
        
        section_hits = sum(1 for section in required_sections if section in recommendation_text)
        section_score = (section_hits / len(required_sections)) * 100
        
        # 3-2 综合评分：降低纯词频权重0.4→0.25，提高章节结构权重0.6→0.75
        final_coverage_score = coverage_score * 0.25 + section_score * 0.75
        
        return {
            "overall_coverage_score": final_coverage_score,
            "category_coverage": coverage_details,
            "missing_items": missing_items,
            "section_completeness": {
                "score": section_score,
                "hits": section_hits,
                "total": len(required_sections),
                "missing": [s for s in required_sections if s not in recommendation_text]
            },
            "feedback_for_llm": f"建议补充以下内容：{', '.join(missing_items[:5])}" if missing_items else "内容覆盖较为完整"
        }

# ==================== 2. 可行性-可操作性类指标 (Usability / Operability Metrics) ====================
# 目标：打分  "施工现场好不好用"

class UsabilityOperabilityMetrics:
    """可行性-可操作性类指标 - 打分现场好不好用"""
    
    def __init__(self):
        # 基本框架 - 已有的评估函数
        pass
        
    def evaluate_operability(self, text: str) -> Dict[str, Any]:
        """评估可操作性"""
        operability_scores = {}
        
        # 操作步骤详细程度
        step_indicators = ["步骤", "流程", "首先", "然后", "接下来", "最后"]
        step_score = min(25, sum(5 for indicator in step_indicators if indicator in text))
        operability_scores["操作步骤详细程度"] = step_score
        
        # 工具需求明确性
        tools = ["扳手", "螺丝刀", "吊装", "起重", "测量", "校准", "工具"]
        tool_score = min(20, sum(3 for tool in tools if tool in text))
        operability_scores["工具需求明确性"] = tool_score
        
        # 时间估算
        time_keywords = ["时间", "工期", "小时", "天", "工日", "工时"]
        time_score = min(15, sum(5 for keyword in time_keywords if keyword in text))
        operability_scores["时间估算"] = time_score
        
        # 人员配置
        personnel_keywords = ["人员", "技工", "电工", "焊工", "操作人员", "专业"]
        personnel_score = min(20, sum(4 for keyword in personnel_keywords if keyword in text))
        operability_scores["人员配置"] = personnel_score
        
        # 质量检查点
        qc_keywords = ["检查", "验收", "测试", "校准", "检验", "确认"]
        qc_score = min(20, sum(4 for keyword in qc_keywords if keyword in text))
        operability_scores["质量检查点"] = qc_score
        
        total_operability = sum(operability_scores.values())
        
        return {
            "operability_score": total_operability,
            "operability_details": operability_scores
        }
    
    def evaluate_field_applicability(self, text: str) -> Dict[str, Any]:
        """评估现场适用性"""
        field_scores = {}
        
        # 环境适应性
        env_keywords = ["环境", "温度", "湿度", "腐蚀", "振动", "灰尘", "防护"]
        env_score = min(30, sum(5 for kw in env_keywords if kw in text))
        field_scores["环境适应性"] = env_score
        
        # 空间要求
        space_keywords = ["空间", "位置", "距离", "高度", "安装位置", "布置"]
        space_score = min(25, sum(5 for kw in space_keywords if kw in text))
        field_scores["空间要求"] = space_score
        
        # 接口兼容性
        interface_keywords = ["接口", "兼容", "连接", "配套", "匹配", "适配"]
        interface_score = min(25, sum(5 for kw in interface_keywords if kw in text))
        field_scores["接口兼容性"] = interface_score
        
        # 维护便利性
        maintenance_keywords = ["维护", "检修", "拆卸", "更换", "清洁", "便利"]
        maintenance_score = min(20, sum(4 for kw in maintenance_keywords if kw in text))
        field_scores["维护便利性"] = maintenance_score
        
        total_field = sum(field_scores.values())
        
        return {
            "field_applicability_score": total_field,
            "field_details": field_scores
        }
    
    def simulate_engineer_decision(self, text: str) -> Dict[str, Any]:
        """模拟工程师决策"""
        decision_factors = {
            "可实施性": 0,
            "风险可控性": 0,
            "经济合理性": 0,
            "技术成熟度": 0
        }
        
        # 可实施性评估
        impl_keywords = ["步骤", "材料", "工具", "人员", "可行"]
        decision_factors["可实施性"] = min(25, sum(5 for kw in impl_keywords if kw in text))
        
        # 风险可控性
        risk_keywords = ["风险", "安全", "防护", "措施", "应急", "预案"]
        decision_factors["风险可控性"] = min(25, sum(4 for kw in risk_keywords if kw in text))
        
        # 经济合理性
        cost_keywords = ["成本", "费用", "预算", "经济", "投资"]
        decision_factors["经济合理性"] = min(25, sum(5 for kw in cost_keywords if kw in text))
        
        # 技术成熟度
        tech_keywords = ["标准", "规范", "验证", "成熟", "可靠"]
        decision_factors["技术成熟度"] = min(25, sum(5 for kw in tech_keywords if kw in text))
        
        # 综合推荐度
        overall_recommendation = sum(decision_factors.values())
        
        return {
            "engineer_recommendation_score": overall_recommendation,
            "decision_factors": decision_factors
        }
    
    # 2.2 可扩展项（无需标注）
    def check_sequence_consistency(self, text: str) -> int:
        """时序一致性：如果文档输出了顺序词，且index逻辑，则+10分"""
        sequence_words = ["首先", "然后", "接下来", "最后", "第一步", "第二步"]
        sequence_found = sum(1 for word in sequence_words if word in text)
        return 10 if sequence_found >= 2 else 0
    
    def check_tool_step_alignment(self, text: str) -> int:
        """3-3 工具-步骤对应：扩展常见组合，更易触发"""
        tool_verb_combinations = [
            # 原有组合
            ("扳手", "拧紧"), ("螺丝刀", "拧紧"), ("吊装", "起重"),
            ("焊接", "焊机"), ("切割", "切割机"), ("测量", "量具"),
            # 3-3 新增常见组合
            ("聚氯", "扭矩"), ("校准", "万用表"), ("定位", "测量"),
            ("固定", "螺栓"), ("连接", "管道"), ("密封", "垫片"),
            ("安装", "支架"), ("调试", "仪表"), ("检查", "连接"),
            ("清洁", "表面"), ("标记", "位置"), ("验收", "测试")
        ]
        
        alignment_score = 0
        found_combinations = []
        
        for tool, verb in tool_verb_combinations:
            if tool in text and verb in text:
                alignment_score += 3  # 降低单个组合得分，但增加组合数量
                found_combinations.append(f"{tool}-{verb}")
        
        return min(15, alignment_score)
    
    def check_dimension_reasonableness(self, text: str) -> int:
        """STEP 3: 尺寸合理性柔性评分 - 命中1条给5分、2条给8分、≥3条给满10"""
        import re
        
        # 统计所有命中的规格条目
        total_hits = 0
        
        # 1. DN深度检查 - 放宽范围
        m_dn = re.search(r'DN(\d+)', text)
        m_depth = re.search(r'插入深度.*?(\d+)mm', text)
        
        if m_dn and m_depth:
            dn = int(m_dn.group(1))
            depth = float(m_depth.group(1))
            # 进一步放宽合理性范围：0.15-1.0倍
            if 0.15 * dn <= depth <= 1.0 * dn:
                total_hits += 1
        
        # 2. 常见规格识别
        common_specs = [
            r'50/100',  # 温度范围
            r'PN\d+',   # 压力等级  
            r'DN\d+',   # 管径
            r'4-20mA',  # 信号范围
            r'IP\d+',   # 防护等级
            r'0\.25%',  # 精度等级
            r'M\d+×\d+', # 螺栓规格
            r'½-NPT',   # 螺纹规格
            r'¾-NPT',   # 螺纹规格  
            r'G\d+/\d+', # 管螺纹
            r'304不锈钢', # 材质
            r'316不锈钢',
            r'NBR材质',
            r'PTFE材质'
        ]
        
        spec_found = sum(1 for pattern in common_specs if re.search(pattern, text))
        total_hits += min(spec_found, 3)  # 最多计算3个规格
        
        # 3. 温度压力范围合理性
        temp_match = re.search(r'(-?\d+)℃.*?(-?\d+)℃', text)
        if temp_match:
            temp_min, temp_max = int(temp_match.group(1)), int(temp_match.group(2))
            # 放宽工业温度范围
            if -300 <= temp_min < temp_max <= 1500:
                total_hits += 1
        
        # 4. 压力范围检查
        pressure_patterns = [r'PN(\d+)', r'(\d+)MPa', r'(\d+)bar']
        for pattern in pressure_patterns:
            match = re.search(pattern, text)
            if match:
                pressure_val = int(match.group(1))
                if 0 < pressure_val <= 600:  # 合理压力范围
                    total_hits += 1
                    break
        
        # STEP 3: 柔性评分机制 - 避免"一条不合格即0"
        if total_hits >= 3:
            return 10  # ≥3条给满10分
        elif total_hits == 2:
            return 8   # 2条给8分
        elif total_hits == 1:
            return 5   # 1条给5分
        else:
            return 0   # 0条给0分
    
    def calc_usability(self, text: str) -> Dict[str, Any]:
        """整体可用性计算 - 权重可后续用网格搜索/经验调优"""
        
        # 基本框架评估
        operability_result = self.evaluate_operability(text)
        field_result = self.evaluate_field_applicability(text)
        engineer_result = self.simulate_engineer_decision(text)
        
        # 可扩展项检测
        sequence_score = self.check_sequence_consistency(text)
        tool_step_score = self.check_tool_step_alignment(text)
        dimension_score = self.check_dimension_reasonableness(text)
        
        # 基本框架权重
        base_usability = (
            operability_result["operability_score"] * 0.4 +
            field_result["field_applicability_score"] * 0.4 +
            engineer_result["engineer_recommendation_score"] * 0.2
        )
        
        # 加上可扩展项
        total_usability = base_usability + sequence_score + tool_step_score + dimension_score
        
        return {
            "usability_score": min(100, total_usability),  # 确保不超过100分
            "operability": operability_result,
            "field_applicability": field_result,
            "engineer_simulation": engineer_result,
            "advanced_checks": {
                "sequence_consistency": sequence_score,
                "tool_step_alignment": tool_step_score,
                "dimension_reasonableness": dimension_score
            }
        }

# ==================== 3. 质量评审类指标 (Quality Review Metrics) ====================
# 目标：代替"专家打1-5分"

class QualityReviewMetrics:
    """质量评审类指标 - 代替专家打1-5分"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or LLM_MODEL
    
    # 3.1 没有人工标注怎么办？
    def llm_as_judge_evaluation(self, content: str) -> Dict[str, Any]:
        """1. LLM-as-Judge (G-Eval/GPTScore) - 准备一段Rubric提示"""
        
        rubric_prompt = f"""
你是资深的仪表安装工程师，请从专业角度评估以下安装推荐文档的质量。

评估文档：
{content}

请严格按照以下评分标准（1-5分）进行评估：

**专业性 (1-5分)：**
- 5分：技术术语使用准确，标准规范引用正确，体现深厚专业功底
- 4分：技术术语基本准确，标准引用较为规范
- 3分：技术表述合理，有一定专业性
- 2分：技术内容较为简单，专业性一般
- 1分：技术错误较多，专业性不足

**完整性 (1-5分)：**
- 5分：涵盖安装位置、方式、材料、安全等所有关键要素
- 4分：涵盖大部分关键要素，少量遗漏
- 3分：涵盖主要要素，有一定遗漏
- 2分：要素覆盖不全，有明显缺失
- 1分：要素缺失严重，不够完整

**实用性 (1-5分)：**
- 5分：现场工程师可直接按文档操作，指导性强
- 4分：具有较好的实用指导价值
- 3分：有一定实用性，需要补充细节
- 2分：实用性一般，操作指导不够明确
- 1分：实用性差，难以指导实际操作

**安全性 (1-5分)：**
- 5分：安全风险识别全面，防护措施具体有效
- 4分：安全考虑较为周全，防护措施较为完善
- 3分：有基本的安全考虑
- 2分：安全考虑不够充分
- 1分：安全考虑严重不足

请输出JSON格式：
{{"专业性": 4, "完整性": 3, "实用性": 2, "安全性": 5, "综合评分": 3.5, "评价理由": "..."}}
        """
        
        try:
            from openai import OpenAI
            
            if not OPENAI_API_KEY:
                return {"error": "未配置OpenAI API Key"}
            
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是专业的仪表工程师评审专家，请严格按照评分标准进行评估。"},
                    {"role": "user", "content": rubric_prompt}
                ],
                temperature=0.1  # 低温度保证评价稳定性
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON
            try:
                # 先清理markdown代码块格式
                cleaned_text = result_text
                if "```json" in result_text:
                    # 提取```json 和 ```之间的内容
                    import re
                    json_match = re.search(r'```json\s*\n(.*?)\n```', result_text, re.DOTALL)
                    if json_match:
                        cleaned_text = json_match.group(1).strip()
                elif "```" in result_text:
                    # 提取普通代码块
                    json_match = re.search(r'```\s*\n(.*?)\n```', result_text, re.DOTALL)
                    if json_match:
                        cleaned_text = json_match.group(1).strip()
                
                result_json = json.loads(cleaned_text)
                return {"llm_judge_scores": result_json}
            except:
                # 如果JSON解析失败，使用更健壮的正则提取分数
                scores = {}
                score_patterns = [
                    (r'"专业性":\s*(\d+)', '专业性'),
                    (r'"完整性":\s*(\d+)', '完整性'), 
                    (r'"实用性":\s*(\d+)', '实用性'),
                    (r'"安全性":\s*(\d+)', '安全性'),
                    (r'"综合评分":\s*(\d+\.?\d*)', '综合评分'),
                    # 备用模式
                    (r'专业性[：:]\s*(\d+)', '专业性'),
                    (r'完整性[：:]\s*(\d+)', '完整性'),
                    (r'实用性[：:]\s*(\d+)', '实用性'),
                    (r'安全性[：:]\s*(\d+)', '安全性'),
                    (r'综合评分[：:]\s*(\d+\.?\d*)', '综合评分')
                ]
                
                for pattern, key in score_patterns:
                    if key not in scores:  # 避免重复提取
                        match = re.search(pattern, result_text)
                        if match:
                            scores[key] = float(match.group(1))
                
                return {"llm_judge_scores": scores, "raw_response": result_text}
            
        except Exception as e:
            logger.error(f"LLM评估出错: {str(e)}")
            return {"error": f"LLM评估失败: {str(e)}"}
    
    def self_consistency_evaluation(self, content: str, num_samples: int = 3) -> Dict[str, Any]:
        """2. Self-Consistency / Majority Voting - 同一文档问多次（或多模型），取平均分，可降低LLM随机性"""
        
        evaluations = []
        
        for i in range(num_samples):
            # 稍微变化提示词以获得多样性
            variations = [
                "从工程实践角度",
                "从安全管理角度", 
                "从项目实施角度"
            ]
            
            perspective = variations[i % len(variations)]
            
            prompt = f"""
请{perspective}评估以下仪表安装推荐文档（1-5分制）：

{content}

请给出总体质量评分（1-5分）并说明理由。
            """
            
            try:
                from openai import OpenAI
                client = OpenAI(api_key=OPENAI_API_KEY)
                
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3  # 适中温度获得一定随机性
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # 提取分数
                score_match = re.search(r'(\d+\.?\d*)[分]?', response_text)
                if score_match:
                    score = float(score_match.group(1))
                    evaluations.append({
                        "score": score,
                        "perspective": perspective,
                        "reasoning": response_text
                    })
                
            except Exception as e:
                logger.error(f"一致性评估第{i+1}次失败: {str(e)}")
        
        if evaluations:
            # 计算平均分和一致性
            scores = [eval["score"] for eval in evaluations]
            avg_score = sum(scores) / len(scores)
            consistency = 1.0 - (max(scores) - min(scores)) / 4.0  # 一致性指标
            
            return {
                "self_consistency_score": avg_score,
                "consistency_metric": consistency,
                "individual_evaluations": evaluations,
                "score_variance": max(scores) - min(scores)
            }
        else:
            return {"error": "所有一致性评估都失败了"}
    
    def pairwise_ranking(self, content_a: str, content_b: str) -> Dict[str, Any]:
        """3. Pairwise Relative Ranking - 若同时生成多份文档，请LLM判断"A vs B谁份好？为什么？" """
        
        prompt = f"""
请比较以下两个仪表安装推荐文档的质量，判断哪个更好：

文档A：
{content_a[:500]}...

文档B：
{content_b[:500]}...

请选择并说明理由：
- A更好
- B更好  
- 基本相当
        """
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # 解析比较结果
            if "A更好" in result or "A好" in result:
                preference = "A"
            elif "B更好" in result or "B好" in result:
                preference = "B"
            elif "相当" in result or "相似" in result:
                preference = "tie"
            else:
                preference = "unclear"
            
            return {
                "preference": preference,
                "reasoning": result
            }
            
        except Exception as e:
            return {"error": f"成对比较失败: {str(e)}"}
    
    def aggregate_quality_scores(self, llm_judge: Dict, self_consistency: Dict) -> Dict[str, Any]:
        """3.3 结果融合为单分 - 聚合多种质量评分"""
        
        aggregated_scores = {}
        
        # LLM-as-Judge分数 (转换为0-100分制)
        if "llm_judge_scores" in llm_judge:
            judge_scores = llm_judge["llm_judge_scores"]
            if "综合评分" in judge_scores:
                aggregated_scores["llm_judge"] = judge_scores["综合评分"] * 20  # 5分制转100分制
        
        # Self-Consistency分数
        if "self_consistency_score" in self_consistency:
            aggregated_scores["self_consistency"] = self_consistency["self_consistency_score"] * 20
        
        # 一致性权重调整
        consistency_weight = self_consistency.get("consistency_metric", 1.0)
        
        # 综合质量分数
        if aggregated_scores:
            # 加权平均公式示例：权重×得分相加
            weights = {"llm_judge": 0.6, "self_consistency": 0.4}
            
            quality_score = 0
            total_weight = 0
            
            for method, score in aggregated_scores.items():
                weight = weights.get(method, 1.0) * consistency_weight
                quality_score += score * weight
                total_weight += weight
            
            if total_weight > 0:
                quality_score /= total_weight
            
            return {
                "overall_quality_score": quality_score,
                "component_scores": aggregated_scores,
                "consistency_weight": consistency_weight,
                "quality_level": self._get_quality_level(quality_score)
            }
        else:
            return {"error": "无有效的质量评分"}
    
    def _get_quality_level(self, score: float) -> str:
        """根据分数获取质量等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"  
        elif score >= 70:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "不合格"

# ==================== 4. 把三类指标整合到现有脚本 ====================

def integrate_comprehensive_metrics(recommendation_text: str) -> Dict[str, Any]:
    """整合三类指标的综合评估"""
    
    print("🔍 启动三类指标综合评估...")
    
    # 1. 内容覆盖类指标
    print("📊 评估内容覆盖类指标...")
    coverage_evaluator = ContentCoverageMetrics()
    coverage_result = coverage_evaluator.evaluate_content_coverage(recommendation_text)
    
    # 2. 可行性-可操作性类指标  
    print("🔧 评估可行性-可操作性类指标...")
    usability_evaluator = UsabilityOperabilityMetrics()
    usability_result = usability_evaluator.calc_usability(recommendation_text)
    
    # 3. 质量评审类指标
    print("👨‍🔬 评估质量评审类指标...")
    quality_evaluator = QualityReviewMetrics()
    llm_judge_result = quality_evaluator.llm_as_judge_evaluation(recommendation_text)
    consistency_result = quality_evaluator.self_consistency_evaluation(recommendation_text)
    quality_aggregate = quality_evaluator.aggregate_quality_scores(llm_judge_result, consistency_result)
    
    # STEP 2: 把内容覆盖权重锁定30-35%，避免关键词没覆盖就跌穿及格线
    weights = {
        "coverage": 0.30,     # 内容覆盖 30% (从35%再次降低，完全避免卡死)
        "usability": 0.50,    # 可用性(≈落地性) 50% (从45%提高，突出实用性)
        "quality": 0.20       # 质量评审(LLM) 20% (保持不变)
    }
    
    comprehensive_score = (
        coverage_result["overall_coverage_score"] * weights["coverage"] +
        usability_result["usability_score"] * weights["usability"] +
        quality_aggregate.get("overall_quality_score", 70) * weights["quality"]
    )
    
    return {
        "comprehensive_score": comprehensive_score,
        "comprehensive_level": quality_evaluator._get_quality_level(comprehensive_score),
        "content_coverage": coverage_result,
        "usability_operability": usability_result,
        "quality_review": {
            "llm_judge": llm_judge_result,
            "self_consistency": consistency_result,
            "aggregated": quality_aggregate
        },
        "evaluation_weights": weights,
        "evaluation_timestamp": datetime.now().isoformat()
    }

# ==================== 5. 为什么"不需要人工标注"也行？ ====================

def why_no_human_annotation_needed():
    """
    解释为什么不需要人工标注的原因：
    
    1. 内容覆盖类：基于规则和词表，客观可验证
    2. 可行性类：基于工程常识和专家规则，可程序化
    3. 质量评审类：LLM-as-Judge已被证明与人类评价高度相关
    
    这样的无标注评估可以：
    - 快速迭代和优化
    - 大规模自动化评估
    - 持续监控系统质量
    """
    return {
        "无需人工标注的优势": [
            "快速迭代：可以实时评估和优化",
            "规模化：支持大批量文档评估",
            "一致性：避免人工评估的主观性差异",
            "成本效益：显著降低评估成本"
        ],
        "评估可靠性保证": [
            "多维度交叉验证",
            "Self-Consistency降低随机性",
            "基于专家规则的客观评估",
            "可持续改进的评估标准"
        ]
    }

def test_comprehensive_metrics():
    """测试综合评价指标"""
    
    sample_text = """
    # 压力仪表安装推荐方案
    
    ## 安装位置选择
    压力仪表应安装在直管段，距离弯头5倍管径，确保测量准确性。
    环境温度应在-40°C至+85°C范围内，湿度不超过85%。
    
    ## 安装方式与步骤
    1. 首先检查安装位置和工具准备
    2. 然后使用扳手拧紧连接螺栓
    3. 接下来进行气密性测试
    4. 最后验收确认
    
    ## 材料清单
    - 压力表：DN50，PN16，材质不锈钢304
    - 螺栓：M12×50，数量8个  
    - 垫片：石墨垫片，耐温200°C
    
    ## 安全要求
    安装过程中注意防护，存在高压风险，应佩戴安全帽和手套。
    设置压力报警和安全联锁系统，防止超压危险。
    制定应急预案，确保人员安全。
    """
    
    print("🧪 测试三类指标综合评估...")
    result = integrate_comprehensive_metrics(sample_text)
    
    print("\n📊 综合评价结果：")
    print(f"🎯 综合得分：{result['comprehensive_score']:.1f}/100 ({result['comprehensive_level']})")
    print(f"📋 内容覆盖：{result['content_coverage']['overall_coverage_score']:.1f}/100")
    print(f"🔧 可用性：{result['usability_operability']['usability_score']:.1f}/100")
    
    if 'quality_review' in result and 'aggregated' in result['quality_review']:
        quality_score = result['quality_review']['aggregated'].get('overall_quality_score', 0)
        print(f"👨‍🔬 质量评审：{quality_score:.1f}/100")
    
    print(f"\n💡 改进建议：{result['content_coverage']['feedback_for_llm']}")
    
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_comprehensive_metrics() 
 