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
        """构建仪表领域词汇表和语义关系（从LLM识别结果动态生成）"""
        try:
            # 从LLM识别结果中获取仪表类型
            llm_types = self._load_llm_instrument_types()
            
            if not llm_types:
                logger.warning("⚠️ 未找到LLM识别的仪表类型，使用基本词汇表")
                return self._build_basic_vocabulary()
            
            # 基于LLM识别的类型动态构建词汇表
            vocabulary = {}
            
            for instrument_type, info in llm_types.items():
                category = info.get('category', '其他')
                
                # 为每个仪表类型生成相关词汇
                vocab_entry = {
                    "main_types": [instrument_type],  # 以LLM识别的类型为主
                    "related_terms": self._generate_related_terms(instrument_type, category),
                    "installation_terms": self._generate_installation_terms(instrument_type, category),
                    "materials": self._generate_material_terms(instrument_type, category)
                }
                
                vocabulary[instrument_type] = vocab_entry
            
            logger.info(f"🤖 基于LLM识别结果构建了 {len(vocabulary)} 种仪表的词汇表")
            return vocabulary
            
        except Exception as e:
            logger.warning(f"⚠️ 动态构建词汇表失败: {str(e)}，使用基本词汇表")
            return self._build_basic_vocabulary()
    
    def _load_llm_instrument_types(self) -> Dict:
        """加载LLM识别的仪表类型"""
        try:
            import json
            llm_types_file = "./data/llm_instrument_types.json"
            
            if os.path.exists(llm_types_file):
                with open(llm_types_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('instrument_types', {})
            
            return {}
            
        except Exception as e:
            logger.warning(f"加载LLM仪表类型失败: {str(e)}")
            return {}
    
    def _generate_related_terms(self, instrument_type: str, category: str) -> List[str]:
        """基于仪表类型和类别动态生成相关术语"""
        base_terms = []
        instrument_lower = instrument_type.lower()
        
        # 基于类别生成通用术语
        if category == '温度':
            base_terms.extend(["测温", "感温", "温度传感器", "保护管", "测温点"])
        elif category == '压力':
            base_terms.extend(["压力测量", "取压", "压力传感", "取压点", "导压管"])
        elif category == '流量':
            base_terms.extend(["流量测量", "流速", "流体", "介质流动", "流向"])
        elif category == '液位' or category == '物位':
            base_terms.extend(["液位测量", "物位", "界面", "液位范围"])
        elif category == '控制':
            base_terms.extend(["控制", "调节", "执行", "定位器"])
        
        # 基于具体类型名称生成特定术语
        if '热电偶' in instrument_lower:
            base_terms.extend(["热电偶", "PT100", "K型", "接线盒"])
        elif '压力' in instrument_lower:
            base_terms.extend(["膜片", "弹簧管", "三阀组", "缓冲器"])
        elif '流量' in instrument_lower:
            base_terms.extend(["直管段", "上游", "下游", "管道中心"])
        elif '液位' in instrument_lower:
            base_terms.extend(["浮子", "浮球", "导向管", "取源管"])
        elif '电磁' in instrument_lower:
            base_terms.extend(["电磁", "电极", "衬里", "法兰"])
        elif '差压' in instrument_lower:
            base_terms.extend(["差压", "压差", "膜片"])
        elif '浮球' in instrument_lower:
            base_terms.extend(["浮球", "浮子", "导波杆"])
        
        return list(set(base_terms))  # 去重
    
    def _generate_installation_terms(self, instrument_type: str, category: str) -> List[str]:
        """生成安装相关术语"""
        installation_terms = ["安装位置", "安装高度", "安装方向", "固定", "支撑"]
        
        instrument_lower = instrument_type.lower()
        
        # 基于仪表类型添加特定安装术语
        if '温度' in category.lower() or '热电偶' in instrument_lower:
            installation_terms.extend(["插入深度", "保护套", "接线盒"])
        elif '压力' in category.lower() or '压力' in instrument_lower:
            installation_terms.extend(["取压点", "导压管", "三阀组"])
        elif '流量' in category.lower() or '流量' in instrument_lower:
            installation_terms.extend(["直管段", "上游", "下游", "管道中心"])
        elif '液位' in category.lower() or '液位' in instrument_lower:
            installation_terms.extend(["垂直安装", "导向管", "液位范围"])
        elif '阀' in instrument_lower or '控制' in category.lower():
            installation_terms.extend(["阀门方向", "流向", "连接方式"])
        
        return list(set(installation_terms))
    
    def _generate_material_terms(self, instrument_type: str, category: str) -> List[str]:
        """生成材料相关术语"""
        base_materials = ["不锈钢", "碳钢", "金属套管"]
        
        instrument_lower = instrument_type.lower()
        
        # 基于仪表类型添加特定材料
        if '温度' in category.lower():
            base_materials.extend(["陶瓷", "金属套管", "保护管"])
        elif '压力' in category.lower():
            base_materials.extend(["不锈钢管", "铜管", "聚四氟乙烯"])
        elif '流量' in category.lower():
            base_materials.extend(["衬里", "电极", "法兰"])
        elif '液位' in category.lower():
            base_materials.extend(["浮筒", "导波杆", "缆绳"])
        elif '阀' in instrument_lower:
            base_materials.extend(["阀体材料", "密封材料", "弹簧"])
        
        return list(set(base_materials))
    
    def _build_basic_vocabulary(self) -> Dict[str, Dict]:
        """基本词汇表（备用方案）"""
        return {
            "通用仪表": {
                "main_types": ["仪表", "传感器", "变送器", "计量器"],
                "related_terms": ["测量", "检测", "监测", "传感", "信号"],
                "installation_terms": ["安装位置", "安装要求", "固定方式", "连接"],
                "materials": ["不锈钢", "金属", "材料选择"]
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
                top_k=top_k * 2,  # 获取更多候选结果
                min_similarity=0.4  # 降低初始阈值，后续重排序
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
 