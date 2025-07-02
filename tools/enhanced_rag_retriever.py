"""
增强RAG检索器
通过查询扩展、重排序、领域适应等技术提升检索质量和泛化性
"""
import os
import re
import pickle
from typing import List, Dict, Tuple, Optional, Set
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.build_index import DocumentIndexer
from tools.match_standard_clause import StandardClauseRetriever

logger = logging.getLogger(__name__)

class EnhancedRAGRetriever:
    """增强的RAG检索器"""
    
    def __init__(self, index_path: str = None):
        """初始化增强检索器"""
        self.base_retriever = StandardClauseRetriever(index_path)
        self.instrument_vocabulary = self._build_instrument_vocabulary()
        self.semantic_enhancer = self._build_semantic_enhancer()
        
    def _build_instrument_vocabulary(self) -> Dict[str, Dict]:
        """构建仪表领域词汇表和语义关系（使用基本硬编码词汇表）"""
        logger.info("构建基本仪表词汇表...")
        return self._build_basic_vocabulary()
    
    def _build_basic_vocabulary(self) -> Dict[str, Dict]:
        """基本词汇表（硬编码）——覆盖常见测控/分析/执行仪表"""
        return {
            # 1 ───────── 温度
            "温度仪表": {
                "main_types": [
                    "热电偶", "热电阻", "双金属温度计", "压力式温度计",
                    "表面温度计", "温度变送器", "光纤温度计"
                ],
                "related_terms": [
                    "测温", "感温", "温度传感器", "保护管", "测温点",
                    "PT100", "PT1000", "K型", "J型", "T型", "E型",
                    "补偿导线", "接线盒", "温包", "毛细管", "抗震"
                ],
                "installation_terms": [
                    "安装位置", "安装深度", "插入长度", "倾斜安装",
                    "固定方式", "伴热", "隔热", "弯曲半径", "防弯曲",
                    "防磨损", "防冲刷"
                ],
                "materials": [
                    "不锈钢", "316L", "304", "哈氏合金", "陶瓷", "金属套管"
                ]
            },

            # 2 ───────── 压力
            "压力仪表": {
                "main_types": [
                    "压力变送器", "差压变送器", "压力表", "绝压表",
                    "微压表", "压力开关", "隔膜压力表"
                ],
                "related_terms": [
                    "压力测量", "取压", "压力传感", "取压点", "导压管",
                    "膜片", "弹簧管", "三阀组", "隔离膜片", "毛细管",
                    "正压室", "负压室", "缓冲器"
                ],
                "installation_terms": [
                    "取压口", "安装高度", "导压管路", "环形冷凝弯",
                    "U型冷凝弯", "冷凝器", "脉冲管坡度", "排污阀",
                    "吹扫", "防堵", "伴热"
                ],
                "materials": [
                    "不锈钢管", "铜管", "聚四氟乙烯", "哈氏合金", "膜片材料"
                ]
            },

            # 3 ───────── 流量
            "流量仪表": {
                "main_types": [
                    "孔板流量计", "喷咀流量计", "文丘里流量计",
                    "电磁流量计", "涡街流量计", "涡轮流量计",
                    "转子流量计", "靶式流量计", "科里奥利质量流量计",
                    "超声波流量计", "椭圆齿轮流量计", "皮托管", "均速管"
                ],
                "related_terms": [
                    "流量测量", "流速", "流体", "介质流动", "直管段",
                    "上游", "下游", "定压孔", "均压环", "取压孔",
                    "满管", "接地环", "β系数", "电极", "衬里", "信号放大器"
                ],
                "installation_terms": [
                    "上游直管段", "下游直管段", "管道中心", "流向",
                    "接地", "法兰连接", "同轴度", "整流器", "支架", "减振"
                ],
                "materials": [
                    "衬里材料", "电极材料", "哈氏合金", "316L", "法兰",
                    "密封垫片", "接地线"
                ]
            },

            # 4 ───────── 液位 / 物位
            "液位仪表": {
                "main_types": [
                    "浮球液位计", "浮筒液位计", "磁翻板液位计", "导波雷达液位计",
                    "雷达液位计", "超声波液位计", "差压式液位计", "射线液位计"
                ],
                "related_terms": [
                    "液位测量", "物位", "界面", "液位范围", "浮子",
                    "浮球", "导波杆", "补偿式平衡容器", "旁路腔体",
                    "安装盲区", "回波", "波束角"
                ],
                "installation_terms": [
                    "安装位置", "安装高度", "导向管", "旁路管",
                    "取源管", "盲区", "防波挡板", "补偿容器", "防挂料"
                ],
                "materials": [
                    "304", "316L", "哈氏合金", "导波杆", "缆绳", "法兰"
                ]
            },

            # 5 ───────── 湿度
            "湿度仪表": {
                "main_types": ["温湿度变送器", "湿度传感器", "露点温湿度记录仪"],
                "related_terms": [
                    "湿度", "相对湿度", "湿敏元件", "干湿球",
                    "透气膜", "冷凝", "空气对流"
                ],
                "installation_terms": [
                    "通风", "遮阳", "防冷凝", "安装高度", "过滤帽"
                ],
                "materials": ["聚四氟乙烯滤膜", "不锈钢网罩"]
            },

            # 6 ───────── 露点
            "露点仪表": {
                "main_types": ["露点仪", "露点变送器"],
                "related_terms": [
                    "露点", "微量水分", "陶瓷传感芯片", "测量腔", "干燥剂"
                ],
                "installation_terms": [
                    "旁路取样", "常温取样", "保温", "遮光", "防冷凝"
                ],
                "materials": ["316L", "铝合金", "密封圈"]
            },

            # 7 ───────── 密度 / 重量
            "密度仪表": {
                "main_types": [
                    "振筒密度计", "科里奥利密度计", "在线密度变送器",
                    "称重传感器", "负荷传感器"
                ],
                "related_terms": [
                    "密度测量", "质量", "振筒", "密度计", "称重",
                    "剪切梁", "压式", "缓冲块"
                ],
                "installation_terms": [
                    "垂直受力", "减振支架", "零点标定", "支撑平台"
                ],
                "materials": ["不锈钢", "合金钢", "橡胶减振垫"]
            },

            # 8 ───────── 振动
            "振动仪表": {
                "main_types": ["加速度计", "速度传感器", "振动监测仪"],
                "related_terms": [
                    "振动", "加速度", "位移", "主灵敏轴",
                    "三轴座", "频响", "冲击"
                ],
                "installation_terms": [
                    "固紧螺钉", "粘贴", "磁吸", "减振", "温度补偿"
                ],
                "materials": ["钛合金壳体", "陶瓷剪切片"]
            },

            # 9 ───────── 转速 / 速度
            "转速仪表": {
                "main_types": ["转速探头", "测速齿轮", "霍尔传感器", "磁电速度计"],
                "related_terms": [
                    "转速", "速度", "脉冲", "霍尔开关", "磁电感应"
                ],
                "installation_terms": ["间隙", "同心度", "支架", "屏蔽"],
                "materials": ["不锈钢罩", "永磁体", "屏蔽线"]
            },

            # 10 ───────── 气体检测
            "气体检测仪表": {
                "main_types": [
                    "可燃气体探测器", "毒性气体探测器", "氧含量分析仪",
                    "红外气体分析仪"
                ],
                "related_terms": [
                    "气体检测", "探头", "扩散式", "泵吸式",
                    "标定罩", "报警", "安装高度"
                ],
                "installation_terms": [
                    "流量控制", "遮雨罩", "防尘", "防爆", "独立接地"
                ],
                "materials": ["铝合金壳体", "不锈钢防爆腔", "过滤片"]
            },

            # 11 ───────── 分析 / 成分
            "分析仪表": {
                "main_types": [
                    "气相色谱", "在线红外分析仪", "pH 计",
                    "电导率仪", "溶氧仪", "浊度计"
                ],
                "related_terms": [
                    "取样", "预处理", "代表性样品", "过滤器",
                    "排放管", "样品冷却器", "标定", "交叉敏感"
                ],
                "installation_terms": [
                    "取样探头", "伴热管线", "旁路取样",
                    "恒温", "冷凝", "排液"
                ],
                "materials": ["PFA 管", "316L", "玻璃电极", "隔膜"]
            },

            # 12 ───────── 控制设备
            "控制设备": {
                "main_types": [
                    "调节阀", "自力式调节阀", "电动执行机构",
                    "气动执行机构", "液动执行机构", "阀门定位器",
                    "电磁阀"
                ],
                "related_terms": [
                    "控制", "调节", "执行", "定位器",
                    "行程", "转矩", "开度", "信号", "联锁"
                ],
                "installation_terms": [
                    "安装方向", "介质流向", "连接方式",
                    "行程调整", "信号接线", "连杆", "支架", "减振"
                ],
                "materials": [
                    "阀体材料", "316L", "WC6", "密封件", "弹簧", "执行机构"
                ]
            },

            # 13 ───────── 通用
            "通用仪表": {
                "main_types": ["仪表", "传感器", "变送器", "计量器", "显示器"],
                "related_terms": [
                    "测量", "检测", "监测", "传感", "信号",
                    "显示", "报警", "输出", "联锁"
                ],
                "installation_terms": [
                    "安装位置", "安装要求", "固定方式",
                    "连接", "屏蔽", "接线", "接地", "防爆"
                ],
                "materials": [
                    "不锈钢", "铝合金", "工程塑料", "防护等级 IP65",
                    "IP67", "IP68"
                ]
            }
        }
    
    def _build_semantic_enhancer(self) -> Dict[str, List[str]]:
        """构建语义增强映射"""
        return {
            "安装": ["安装", "安装要求", "安装方法", "安装位置", "安装高度", "安装方向", "固定", "支撑"],
            "材料": ["材料", "材质", "选材", "材料要求", "管路材料", "阀门材料", "电缆"],
            "连接": ["连接", "接线", "配管", "配线", "接头", "法兰", "螺纹"],
            "保护": ["保护", "防护", "保护管", "保护套", "防腐", "防爆", "密封"],
            "维护": ["维护", "保养", "检修", "校准", "清洗", "更换"],
            "安全": ["安全", "安全要求", "注意事项", "防护措施", "接地", "绝缘"]
        }

    def enhance_query(self, query: str, instrument_type: str = None) -> List[str]:
        """查询增强：基于领域知识扩展查询"""
        enhanced_queries = [query]  # 保留原始查询
        
        # 1. 自动识别仪表类型（如果未提供）
        if not instrument_type:
            instrument_type = self._identify_instrument_type(query)
        
        # 2. 基于仪表类型添加相关词汇
        if instrument_type:
            vocab = self._get_instrument_vocabulary(instrument_type)
            if vocab:
                for main_type in vocab.get("main_types", []):
                    if main_type.lower() in query.lower():
                        for term in vocab.get("related_terms", [])[:3]:
                            enhanced_queries.append(f"{main_type} {term}")
                
                if any(keyword in query.lower() for keyword in ["安装", "安装要求", "安装方法"]):
                    for install_term in vocab.get("installation_terms", [])[:2]:
                        enhanced_queries.append(f"{instrument_type} {install_term}")
        
        # 3. 基于查询意图添加语义扩展
        for semantic_key, expansions in self.semantic_enhancer.items():
            if semantic_key in query:
                for expansion in expansions[:2]:
                    if expansion != semantic_key:
                        enhanced_query = query.replace(semantic_key, expansion)
                        enhanced_queries.append(enhanced_query)
        
        # 4. 去重并限制查询数量
        unique_queries = []
        seen = set()
        for q in enhanced_queries:
            if q.lower() not in seen:
                unique_queries.append(q)
                seen.add(q.lower())
        
        return unique_queries[:5]  # 最多返回5个查询

    def _identify_instrument_type(self, query: str) -> Optional[str]:
        """基于查询内容自动识别仪表类型"""
        query_lower = query.lower()
        
        for category, vocab in self.instrument_vocabulary.items():
            for main_type in vocab.get("main_types", []):
                if main_type.lower() in query_lower:
                    return main_type
            
            for related_term in vocab.get("related_terms", []):
                if related_term.lower() in query_lower:
                    return vocab["main_types"][0] if vocab["main_types"] else None
        
        return None
    
    def _get_instrument_vocabulary(self, instrument_type: str) -> Optional[Dict]:
        """获取特定仪表类型的词汇信息"""
        for category, vocab in self.instrument_vocabulary.items():
            if instrument_type in vocab.get("main_types", []):
                return vocab
        return None

    def advanced_search(self, query: str, instrument_type: str = None, top_k: int = 5) -> List[Dict]:
        """
        增强搜索：结合查询扩展和重排序
        
        Args:
            query: 查询字符串
            instrument_type: 仪表类型
            top_k: 返回结果数量
        
        Returns:
            重排序后的搜索结果
        """
        # 1. 查询增强
        enhanced_queries = self.enhance_query(query, instrument_type)
        
        # 2. 多查询检索
        all_results = []
        seen_content = set()
        
        for i, enhanced_query in enumerate(enhanced_queries):
            # 为不同查询设置不同的权重
            weight = 1.0 - (i * 0.1)  # 原始查询权重最高
            
            results = self.base_retriever.search_related_clauses(
                enhanced_query, 
                top_k=top_k * 3,  # 🎯 从2倍增加到3倍，获取更多候选结果供重排序
                min_similarity=0.6  # 降低初始阈值，后续重排序
            )
            
            for result in results:
                content = result['content']
                if content not in seen_content:
                    seen_content.add(content)
                    # 添加查询权重和来源信息
                    result['query_weight'] = weight
                    result['source_query'] = enhanced_query
                    all_results.append(result)
        
        # 3. 重排序
        reranked_results = self._rerank_results(all_results, query, instrument_type)
        
        return reranked_results[:top_k]
    
    def _rerank_results(self, results: List[Dict], original_query: str, instrument_type: str = None) -> List[Dict]:
        """结果重排序：基于多个因素重新计算相关性分数"""
        for result in results:
            content = result['content']
            original_score = result['score']
            query_weight = result.get('query_weight', 1.0)
            
            # 重新计算综合分数
            rerank_score = self._calculate_rerank_score(
                content, original_query, instrument_type, original_score, query_weight
            )
            
            result['rerank_score'] = rerank_score
            result['original_score'] = original_score
        
        # 按重排序分数排序
        results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return results
    
    def _calculate_rerank_score(self, content: str, query: str, instrument_type: str, 
                               original_score: float, query_weight: float) -> float:
        """
        计算重排序分数
        
        综合考虑：
        1. 原始向量相似度
        2. 查询权重
        3. 仪表类型匹配度
        4. 关键词匹配度
        5. 内容质量评分
        """
        content_lower = content.lower()
        query_lower = query.lower()
        
        # 1. 基础分数（原始相似度 * 查询权重）
        base_score = original_score * query_weight
        
        # 2. 仪表类型匹配加分
        type_bonus = 0.0
        if instrument_type:
            vocab = self._get_instrument_vocabulary(instrument_type)
            if vocab:
                # 精确匹配主要类型
                if instrument_type.lower() in content_lower:
                    type_bonus += 0.2
                
                # 匹配相关术语
                related_matches = sum(1 for term in vocab.get("related_terms", []) 
                                    if term.lower() in content_lower)
                type_bonus += min(related_matches * 0.05, 0.15)
        
        # 3. 查询关键词匹配加分
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        keyword_overlap = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0
        keyword_bonus = keyword_overlap * 0.15
        
        # 4. 内容质量评分
        quality_score = self._assess_content_quality(content, query)
        
        # 5. 反向惩罚：降低无关内容分数
        penalty = self._calculate_irrelevance_penalty(content, query, instrument_type)
        
        # 综合分数计算
        final_score = base_score + type_bonus + keyword_bonus + quality_score - penalty
        
        return max(0.0, min(1.0, final_score))  # 限制在[0,1]范围内
    
    def _assess_content_quality(self, content: str, query: str) -> float:
        """评估内容质量"""
        quality_score = 0.0
        
        # 长度适中性（太短或太长都减分）
        length = len(content)
        if 50 <= length <= 300:
            quality_score += 0.05
        elif length < 20:
            quality_score -= 0.1
        
        # 结构化程度（包含条款号、编号等）
        if re.search(r'第\s*\d+\.\d+\.\d+\s*条', content):
            quality_score += 0.1
        elif re.search(r'\d+[、．]\s*', content):
            quality_score += 0.05
        
        # 技术术语密度
        technical_terms = ["安装", "要求", "规定", "应", "宜", "不应", "必须", "禁止"]
        term_count = sum(1 for term in technical_terms if term in content)
        quality_score += min(term_count * 0.02, 0.1)
        
        return quality_score
    
    def _calculate_irrelevance_penalty(self, content: str, query: str, instrument_type: str) -> float:
        """计算无关内容的惩罚分数"""
        penalty = 0.0
        content_lower = content.lower()
        
        # 如果指定了仪表类型，检查是否包含其他不相关的仪表类型
        if instrument_type:
            other_instruments = []
            for category, vocab in self.instrument_vocabulary.items():
                for main_type in vocab.get("main_types", []):
                    if main_type != instrument_type:
                        other_instruments.append(main_type.lower())
            
            # 如果内容强烈指向其他仪表类型，增加惩罚
            other_type_mentions = sum(1 for other_type in other_instruments 
                                    if other_type in content_lower)
            if other_type_mentions >= 2:
                penalty += 0.3
            elif other_type_mentions == 1:
                penalty += 0.1
        
        # 过于通用的内容惩罚
        generic_patterns = [
            r'^[^。]{0,30}$',  # 过短且没有句号
            r'一般规定',
            r'总则',
            r'基本要求'
        ]
        
        for pattern in generic_patterns:
            if re.search(pattern, content_lower):
                penalty += 0.1
                break
        
        return penalty

    def intelligent_instrument_search(self, instrument_info: Dict) -> List[Dict]:
        """
        智能仪表搜索：基于表格中的仪表信息进行智能搜索
        对不同仪表类型具有良好的泛化性
        
        Args:
            instrument_info: 仪表信息字典，包含类型、测量范围、工艺条件等
        
        Returns:
            相关的安装规范列表
        """
        instrument_type = instrument_info.get('仪表类型', instrument_info.get('type', ''))
        measure_range = instrument_info.get('测量范围', instrument_info.get('range', ''))
        process_condition = instrument_info.get('工艺条件', instrument_info.get('condition', ''))
        
        # 构建智能查询
        search_queries = []
        
        # 1. 基础查询
        if instrument_type:
            search_queries.append(f"{instrument_type}安装")
            search_queries.append(f"{instrument_type}安装要求")
        
        # 2. 基于测量范围的查询
        if measure_range:
            # 提取温度、压力等关键信息
            if '℃' in measure_range or '°C' in measure_range:
                if '高温' in measure_range or any(temp in measure_range for temp in ['400', '500', '600']):
                    search_queries.append(f"{instrument_type}高温安装")
                if '低温' in measure_range or '-' in measure_range:
                    search_queries.append(f"{instrument_type}低温安装")
            
            if 'MPa' in measure_range or 'kPa' in measure_range:
                if any(pressure in measure_range for pressure in ['高压', '10', '20', '50']):
                    search_queries.append(f"{instrument_type}高压安装")
        
        # 3. 基于工艺条件的查询
        if process_condition:
            if '腐蚀' in process_condition:
                search_queries.append(f"{instrument_type}防腐材料")
            if '高温' in process_condition:
                search_queries.append(f"{instrument_type}高温保护")
            if '振动' in process_condition:
                search_queries.append(f"{instrument_type}防振安装")
        
        # 4. 执行搜索并合并结果
        all_results = []
        seen_content = set()
        
        for query in search_queries:
            results = self.advanced_search(query, instrument_type, top_k=3)
            for result in results:
                if result['content'] not in seen_content:
                    seen_content.add(result['content'])
                    result['search_query'] = query
                    all_results.append(result)
        
        # 按重排序分数排序
        all_results.sort(key=lambda x: x.get('rerank_score', x.get('score', 0)), reverse=True)
        
        return all_results[:5]  # 返回前5个最相关的结果
    
    def get_comprehensive_standards(self, instrument_type: str) -> Dict[str, List[Dict]]:
        """
        获取某仪表类型的综合安装规范信息（兼容接口）
        
        Args:
            instrument_type: 仪表类型
        
        Returns:
            包含安装方法、材料要求等分类信息的字典
        """
        result = {
            'instrument_type': instrument_type,
            'installation_methods': [],
            'material_requirements': [],
            'safety_requirements': [],
            'maintenance_requirements': []
        }
        
        try:
            # 搜索安装方法 - 🎯 增加到5条，供LLM筛选
            installation_results = self.advanced_search(f"{instrument_type}安装要求", instrument_type, top_k=5)
            for res in installation_results:
                # 转换为基础检索器兼容的格式
                result['installation_methods'].append({
                    'content': res['content'],
                    'score': res.get('rerank_score', res.get('score', 0)),
                    'query': f"{instrument_type}安装要求"
                })
            
            # 搜索材料要求 - 🎯 增加到3条，供LLM筛选
            material_results = self.advanced_search(f"{instrument_type}材料要求", instrument_type, top_k=3)
            for res in material_results:
                if any(keyword in res['content'] for keyword in ['材料', '阀门', '电缆', '管路']):
                    result['material_requirements'].append({
                        'content': res['content'],
                        'score': res.get('rerank_score', res.get('score', 0)),
                        'query': f"{instrument_type}材料要求"
                    })
            
            # 搜索安全要求 - 🎯 增加到3条，供LLM筛选
            safety_results = self.advanced_search(f"{instrument_type}安全要求", instrument_type, top_k=3)
            for res in safety_results:
                if any(keyword in res['content'] for keyword in ['安全', '防护', '注意']):
                    result['safety_requirements'].append({
                        'content': res['content'],
                        'score': res.get('rerank_score', res.get('score', 0)),
                        'query': f"{instrument_type}安全要求"
                    })
            
            # 搜索维护要求 - 🎯 增加到3条，供LLM筛选
            maintenance_results = self.advanced_search(f"{instrument_type}维护", instrument_type, top_k=3)
            for res in maintenance_results:
                if any(keyword in res['content'] for keyword in ['维护', '保养', '检修']):
                    result['maintenance_requirements'].append({
                        'content': res['content'],
                        'score': res.get('rerank_score', res.get('score', 0)),
                        'query': f"{instrument_type}维护"
                    })
            
            logger.info(f"为 {instrument_type} 生成综合标准信息: "
                       f"安装{len(result['installation_methods'])}条, "
                       f"材料{len(result['material_requirements'])}条, "
                       f"安全{len(result['safety_requirements'])}条, "
                       f"维护{len(result['maintenance_requirements'])}条")
        
        except Exception as e:
            logger.error(f"生成 {instrument_type} 综合标准信息失败: {str(e)}")
        
        return result

    def basic_retrieve(self, query: str, top_k: int = 5) -> List:
        """基础检索方法（不含重排序优化），用于对比实验"""
        try:
            # 使用基础检索器进行简单的相似度检索
            results = self.base_retriever.search_related_clauses(
                query, 
                top_k=top_k,
                min_similarity=0.5
            )
            
            # 转换为Document格式以保持接口一致性
            from langchain.schema import Document
            documents = []
            for result in results:
                doc = Document(
                    page_content=result['content'],
                    metadata={
                        'score': result['score'],
                        'source': result.get('source', 'unknown'),
                        'section': result.get('section', '')
                    }
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"基础检索失败: {e}")
            return []
    
    def enhanced_retrieve(self, query: str, top_k: int = 5) -> Dict:
        """增强检索方法（包含重排序优化）"""
        try:
            # 使用高级搜索（包含查询扩展和重排序）
            results = self.advanced_search(query, top_k=top_k)
            
            # 转换为统一格式
            documents = []
            for result in results:
                doc_info = {
                    'content': result['content'],
                    'score': result.get('rerank_score', result['score']),
                    'metadata': {
                        'original_score': result.get('original_score', result['score']),
                        'rerank_score': result.get('rerank_score', result['score']),
                        'source_query': result.get('source_query', query),
                        'source': result.get('source', 'unknown'),
                        'section': result.get('section', '')
                    }
                }
                documents.append(doc_info)
            
            return {
                'documents': documents,
                'query': query,
                'total_results': len(documents),
                'enhanced': True
            }
            
        except Exception as e:
            logger.error(f"增强检索失败: {e}")
            return {
                'documents': [],
                'query': query,
                'total_results': 0,
                'enhanced': False,
                'error': str(e)
            }

def test_enhanced_retriever():
    """测试增强检索器"""
    print("🚀 测试增强RAG检索器")
    print("=" * 50)
    
    try:
        # 初始化增强检索器
        enhanced_retriever = EnhancedRAGRetriever()
        
        # 测试1：基础查询增强
        print("\n📋 测试1：基础查询增强")
        query = "热电偶安装要求"
        enhanced_queries = enhanced_retriever.enhance_query(query)
        print(f"原始查询: {query}")
        print(f"增强查询: {enhanced_queries}")
        
        # 测试2：高级搜索
        print("\n📋 测试2：高级搜索对比")
        basic_results = enhanced_retriever.base_retriever.search_related_clauses(query, top_k=3)
        enhanced_results = enhanced_retriever.advanced_search(query, "热电偶", top_k=3)
        
        print(f"基础搜索结果数: {len(basic_results)}")
        print(f"增强搜索结果数: {len(enhanced_results)}")
        
        if enhanced_results:
            best_result = enhanced_results[0]
            print(f"最佳结果重排序分数: {best_result.get('rerank_score', 'N/A'):.3f}")
            print(f"原始相似度分数: {best_result.get('original_score', 'N/A'):.3f}")
        
        # 测试3：智能仪表搜索
        print("\n📋 测试3：智能仪表搜索")
        instrument_info = {
            '仪表类型': '热电偶',
            '测量范围': '0-800℃',
            '工艺条件': '高温腐蚀性介质'
        }
        
        intelligent_results = enhanced_retriever.intelligent_instrument_search(instrument_info)
        print(f"智能搜索结果数: {len(intelligent_results)}")
        
        for i, result in enumerate(intelligent_results[:2], 1):
            print(f"{i}. 查询: {result.get('search_query', 'N/A')}")
            print(f"   分数: {result.get('rerank_score', result.get('score', 0)):.3f}")
            print(f"   内容: {result['content'][:80]}...")
        
        print("\n✅ 增强检索器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_retriever()
 