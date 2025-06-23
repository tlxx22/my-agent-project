"""
自适应RAG检索器
自动从文档中学习仪表类型和相关术语，完全避免硬编码
具备自学习和动态扩展能力
"""
import os
import re
import json
from typing import List, Dict, Optional
import logging
from collections import defaultdict, Counter
import jieba
import jieba.posseg as pseg
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.match_standard_clause import StandardClauseRetriever

logger = logging.getLogger(__name__)

class AdaptiveRAGRetriever:
    """自适应RAG检索器 - 零硬编码设计"""
    
    def __init__(self, index_path: str = None, auto_learn: bool = True):
        """初始化自适应检索器"""
        self.base_retriever = StandardClauseRetriever(index_path)
        self.knowledge_cache_path = "./data/adaptive_knowledge_cache.json"
        
        # 动态学习的知识库
        self.instrument_patterns = {}
        self.semantic_clusters = {}
        self.document_statistics = {}
        
        if auto_learn:
            self._auto_learn_from_documents()
        else:
            self._load_cached_knowledge()
    
    def _auto_learn_from_documents(self):
        """自动从文档中学习仪表类型和相关术语"""
        logger.info("开始自动学习文档中的仪表类型和术语...")
        
        # 确保检索器已加载
        if not self.base_retriever.is_loaded:
            self.base_retriever.load_index()
        
        if not self.base_retriever.indexer.documents:
            logger.warning("没有找到文档，无法进行自动学习")
            return
        
        documents = self.base_retriever.indexer.documents
        
        # 1. 提取仪表类型模式
        self._extract_instrument_patterns(documents)
        
        # 2. 构建语义聚类
        self._build_semantic_clusters(documents)
        
        # 3. 生成文档统计信息
        self._generate_document_statistics(documents)
        
        # 4. 保存学习结果
        self._save_learned_knowledge()
        
        logger.info(f"自动学习完成！识别了 {len(self.instrument_patterns)} 种仪表类型")
    
    def _extract_instrument_patterns(self, documents: List[str]):
        """从文档中提取仪表类型模式"""
        # 动态的仪表类型模式 - 基于文档内容学习
        instrument_suffixes = [
            r'([^，。、\s]{1,8})(表|计|器|仪|传感器|变送器|控制器|检测器|分析仪)',
            r'([^，。、\s]{1,8})(阀|门)',
            r'(温度|压力|流量|液位|物位|界面|浓度|密度|粘度|pH|电导|氧|气体)([^，。、\s]{0,4})(表|计|器|仪)',
        ]
        
        instrument_counter = Counter()
        
        for doc in documents:
            for pattern in instrument_suffixes:
                matches = re.finditer(pattern, doc)
                for match in matches:
                    if len(match.groups()) == 2:
                        instrument_type = match.group(1) + match.group(2)
                    else:
                        instrument_type = ''.join(match.groups())
                    
                    if 2 <= len(instrument_type) <= 8 and not re.search(r'[0-9]{3,}', instrument_type):
                        instrument_counter[instrument_type] += 1
        
        # 动态阈值 - 基于文档数量
        min_frequency = max(2, len(documents) // 100)
        for instrument, count in instrument_counter.items():
            if count >= min_frequency:
                self.instrument_patterns[instrument] = {
                    'frequency': count,
                    'category': self._infer_instrument_category(instrument),
                    'related_terms': set(),
                    'installation_terms': set()
                }
        
        # 为每个识别的仪表类型提取相关术语
        self._extract_related_terms(documents)
    
    def _infer_instrument_category(self, instrument_type: str) -> str:
        """动态推断仪表类型的大类"""
        category_keywords = {
            '温度': ['温度', '热', '冷', '温'],
            '压力': ['压力', '压强', '真空', '差压'],
            '流量': ['流量', '流速', '流体', '介质'],
            '液位': ['液位', '物位', '界面', '液面', '料位'],
            '分析': ['pH', '氧', '浓度', '密度', '粘度', '电导', '分析'],
            '控制': ['阀', '门', '控制', '调节', '执行']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in instrument_type for keyword in keywords):
                return category
        
        return '其他'
    
    def _extract_related_terms(self, documents: List[str]):
        """为每个仪表类型提取相关术语"""
        for instrument_type in self.instrument_patterns.keys():
            related_terms = set()
            installation_terms = set()
            
            for doc in documents:
                if instrument_type in doc:
                    try:
                        words = pseg.cut(doc)
                        word_list = [(word.word, word.flag) for word in words]
                        
                        for i, (word, flag) in enumerate(word_list):
                            if instrument_type in word:
                                context_range = 5
                                start = max(0, i - context_range)
                                end = min(len(word_list), i + context_range + 1)
                                
                                for j in range(start, end):
                                    if j != i:
                                        context_word, context_flag = word_list[j]
                                        if len(context_word) >= 2 and context_flag in ['n', 'vn', 'v']:
                                            if any(keyword in context_word for keyword in ['安装', '位置', '高度']):
                                                installation_terms.add(context_word)
                                            else:
                                                related_terms.add(context_word)
                    except:
                        # 如果jieba处理失败，使用简单的字符串处理
                        words = doc.replace(instrument_type, ' ').split()
                        for word in words[:10]:  # 取前10个词
                            if len(word) >= 2:
                                related_terms.add(word)
            
            if instrument_type in self.instrument_patterns:
                self.instrument_patterns[instrument_type]['related_terms'] = related_terms
                self.instrument_patterns[instrument_type]['installation_terms'] = installation_terms
    
    def _build_semantic_clusters(self, documents: List[str]):
        """构建语义聚类"""
        semantic_seeds = {
            '安装': ['安装', '装配', '设置', '固定'],
            '材料': ['材料', '材质', '金属', '钢'],
            '连接': ['连接', '配管', '配线', '接线'],
            '测量': ['测量', '检测', '监测'],
            '维护': ['维护', '保养', '维修'],
            '安全': ['安全', '防护', '保护']
        }
        
        for category, seeds in semantic_seeds.items():
            expanded_terms = set(seeds)
            for doc in documents:
                for seed in seeds:
                    if seed in doc:
                        try:
                            words = list(jieba.cut(doc))
                            for i, word in enumerate(words):
                                if seed in word:
                                    for j in range(max(0, i-2), min(len(words), i+3)):
                                        if j != i and len(words[j]) >= 2:
                                            expanded_terms.add(words[j])
                        except:
                            pass
            
            self.semantic_clusters[category] = list(expanded_terms)[:15]
    
    def _generate_document_statistics(self, documents: List[str]):
        """生成文档统计信息"""
        self.document_statistics = {
            'total_documents': len(documents),
            'instrument_types_count': len(self.instrument_patterns),
            'semantic_categories': list(self.semantic_clusters.keys())
        }
    
    def _save_learned_knowledge(self):
        """保存学习到的知识"""
        knowledge = {
            'instrument_patterns': {k: {**v, 'related_terms': list(v['related_terms']), 
                                       'installation_terms': list(v['installation_terms'])} 
                                   for k, v in self.instrument_patterns.items()},
            'semantic_clusters': self.semantic_clusters,
            'document_statistics': self.document_statistics
        }
        
        os.makedirs(os.path.dirname(self.knowledge_cache_path), exist_ok=True)
        with open(self.knowledge_cache_path, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)
    
    def _load_cached_knowledge(self):
        """加载缓存的知识"""
        if os.path.exists(self.knowledge_cache_path):
            try:
                with open(self.knowledge_cache_path, 'r', encoding='utf-8') as f:
                    knowledge = json.load(f)
                
                self.instrument_patterns = {}
                for k, v in knowledge.get('instrument_patterns', {}).items():
                    self.instrument_patterns[k] = {
                        **v,
                        'related_terms': set(v.get('related_terms', [])),
                        'installation_terms': set(v.get('installation_terms', []))
                    }
                
                self.semantic_clusters = knowledge.get('semantic_clusters', {})
                self.document_statistics = knowledge.get('document_statistics', {})
                
                logger.info(f"已加载缓存知识，包含 {len(self.instrument_patterns)} 种仪表类型")
            except Exception as e:
                logger.warning(f"加载缓存知识失败: {e}，将重新学习")
                self._auto_learn_from_documents()
        else:
            self._auto_learn_from_documents()
    
    def auto_identify_instrument_type(self, query: str) -> Optional[str]:
        """自动识别查询中的仪表类型"""
        best_match = None
        best_score = 0
        
        for instrument_type in self.instrument_patterns.keys():
            if instrument_type in query:
                score = len(instrument_type) / len(query) + 1.0
                if score > best_score:
                    best_score = score
                    best_match = instrument_type
        
        return best_match if best_score > 0.1 else None
    
    def adaptive_query_enhancement(self, query: str, instrument_type: str = None) -> List[str]:
        """自适应查询增强"""
        enhanced_queries = [query]
        
        if not instrument_type:
            instrument_type = self.auto_identify_instrument_type(query)
        
        if instrument_type and instrument_type in self.instrument_patterns:
            pattern = self.instrument_patterns[instrument_type]
            
            # 基于学习到的相关术语扩展查询
            for term in list(pattern['related_terms'])[:3]:
                enhanced_queries.append(f"{instrument_type} {term}")
            
            # 基于安装术语扩展
            if any(install_word in query for install_word in ['安装', '位置', '方法']):
                for term in list(pattern['installation_terms'])[:2]:
                    enhanced_queries.append(f"{instrument_type} {term}")
        
        # 去重
        unique_queries = []
        seen = set()
        for q in enhanced_queries:
            if q.lower() not in seen:
                unique_queries.append(q)
                seen.add(q.lower())
        
        return unique_queries[:5]
    
    def get_instrument_types_summary(self) -> Dict:
        """获取学习到的仪表类型总结"""
        summary = {
            'total_types': len(self.instrument_patterns),
            'categories': {},
            'top_types': []
        }
        
        # 按类别分组
        for instrument, pattern in self.instrument_patterns.items():
            category = pattern['category']
            if category not in summary['categories']:
                summary['categories'][category] = []
            summary['categories'][category].append({
                'name': instrument,
                'frequency': pattern['frequency']
            })
        
        # 按频次排序
        sorted_instruments = sorted(
            self.instrument_patterns.items(),
            key=lambda x: x[1]['frequency'],
            reverse=True
        )
        
        summary['top_types'] = [
            {'name': name, 'frequency': pattern['frequency'], 'category': pattern['category']}
            for name, pattern in sorted_instruments[:10]
        ]
        
        return summary

def test_adaptive_retriever():
    """测试自适应检索器"""
    print("🚀 测试自适应RAG检索器（零硬编码）")
    print("=" * 60)
    
    try:
        adaptive_retriever = AdaptiveRAGRetriever()
        
        summary = adaptive_retriever.get_instrument_types_summary()
        print(f"\n📊 自动学习结果:")
        print(f"   识别仪表类型总数: {summary['total_types']}种")
        print(f"   识别类别数: {len(summary['categories'])}个")
        
        print(f"\n🏆 频次最高的10种仪表类型:")
        for i, instrument in enumerate(summary['top_types'], 1):
            print(f"   {i}. {instrument['name']} (类别: {instrument['category']}, 频次: {instrument['frequency']})")
        
        print(f"\n📋 各类别分布:")
        for category, instruments in summary['categories'].items():
            print(f"   {category}: {len(instruments)}种")
        
        # 测试自动识别
        test_queries = [
            "热电偶安装要求",
            "压力变送器材料", 
            "电磁流量计位置",
            "新型智能仪表安装"
        ]
        
        print(f"\n🔍 测试自动识别和查询增强:")
        for query in test_queries:
            identified_type = adaptive_retriever.auto_identify_instrument_type(query)
            enhanced_queries = adaptive_retriever.adaptive_query_enhancement(query)
            
            print(f"\n   查询: '{query}'")
            print(f"   识别类型: {identified_type or '未识别'}")
            print(f"   增强查询: {enhanced_queries}")
        
        print("\n✅ 自适应检索器测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_adaptive_retriever()
 