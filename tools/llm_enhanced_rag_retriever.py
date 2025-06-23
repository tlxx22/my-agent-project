"""
基于LLM识别结果的智能RAG检索器
读取LLM识别的仪表类型文件，进行精准的查询增强
完全避免硬编码，基于文档内容自动适应
"""
import os
import sys
import json
import logging
from typing import List, Dict, Optional, Set
from collections import defaultdict

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.match_standard_clause import StandardClauseRetriever

logger = logging.getLogger(__name__)

class LLMEnhancedRAGRetriever:
    """基于LLM识别结果的智能RAG检索器"""
    
    def __init__(self, index_path: str = None, llm_types_path: str = None):
        """
        初始化LLM增强的RAG检索器
        
        Args:
            index_path: 向量索引文件路径
            llm_types_path: LLM识别的仪表类型文件路径
        """
        self.base_retriever = StandardClauseRetriever(index_path)
        self.llm_types_path = llm_types_path or "./data/llm_instrument_types.json"
        
        # LLM识别的仪表类型数据
        self.instrument_types = {}
        self.category_mapping = {}
        self.term_relationships = defaultdict(set)
        
        # 加载LLM识别的结果
        self._load_llm_identified_types()
    
    def _load_llm_identified_types(self):
        """加载LLM识别的仪表类型结果"""
        try:
            if os.path.exists(self.llm_types_path):
                with open(self.llm_types_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.instrument_types = data.get('instrument_types', {})
                
                if self.instrument_types:
                    # 构建类别映射
                    for instrument, info in self.instrument_types.items():
                        category = info.get('category', '其他')
                        if category not in self.category_mapping:
                            self.category_mapping[category] = []
                        self.category_mapping[category].append(instrument)
                    
                    # 构建术语关系
                    self._build_term_relationships()
                    
                    logger.info(f"✅ 成功加载LLM识别的 {len(self.instrument_types)} 种仪表类型")
                    logger.info(f"📋 涵盖类别: {list(self.category_mapping.keys())}")
                else:
                    logger.warning("⚠️ LLM识别结果为空")
            else:
                logger.warning(f"⚠️ LLM仪表类型文件不存在: {self.llm_types_path}")
                logger.info("💡 请先运行 'python tools/build_index.py' 生成LLM识别结果")
                
        except Exception as e:
            logger.error(f"❌ 加载LLM识别结果失败: {str(e)}")
    
    def _build_term_relationships(self):
        """构建术语关系网络"""
        # 基于LLM识别的仪表类型构建关系网络
        for instrument, info in self.instrument_types.items():
            category = info.get('category', '其他')
            
            # 同类别的仪表类型相关
            if category in self.category_mapping:
                for related_instrument in self.category_mapping[category]:
                    if related_instrument != instrument:
                        self.term_relationships[instrument].add(related_instrument)
    
    def intelligent_instrument_identification(self, query: str) -> Optional[str]:
        """
        智能识别查询中的仪表类型（基于LLM识别结果）
        """
        if not self.instrument_types:
            return None
        
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        # 精确匹配优先
        for instrument in self.instrument_types.keys():
            if instrument in query:
                score = len(instrument) / len(query) + 1.0
                if score > best_score:
                    best_score = score
                    best_match = instrument
        
        return best_match if best_score > 0.1 else None
    
    def generate_enhanced_queries(self, query: str, instrument_type: str = None) -> List[str]:
        """基于LLM识别结果生成增强查询"""
        enhanced_queries = [query]
        
        if not instrument_type:
            instrument_type = self.intelligent_instrument_identification(query)
        
        if not instrument_type or instrument_type not in self.instrument_types:
            return enhanced_queries
        
        instrument_info = self.instrument_types[instrument_type]
        category = instrument_info.get('category', '其他')
        
        # 基于同类别仪表扩展
        if category in self.category_mapping:
            category_instruments = self.category_mapping[category]
            for related_instrument in category_instruments[:2]:
                if related_instrument != instrument_type:
                    enhanced_query = f"{related_instrument} 安装"
                    if enhanced_query not in enhanced_queries:
                        enhanced_queries.append(enhanced_query)
        
        return enhanced_queries[:4]
    
    def advanced_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """执行高级搜索（集成LLM识别结果）"""
        if not self.base_retriever.is_loaded:
            self.base_retriever.load_index()
        
        # 智能识别仪表类型
        identified_type = self.intelligent_instrument_identification(query)
        
        # 生成增强查询
        enhanced_queries = self.generate_enhanced_queries(query, identified_type)
        
        # 收集所有搜索结果
        all_results = []
        
        for i, enhanced_query in enumerate(enhanced_queries):
            try:
                results = self.base_retriever.search_related_clauses(enhanced_query, top_k=top_k)
                
                for result in results:
                    result['enhanced_query'] = enhanced_query
                    result['identified_instrument'] = identified_type
                    
                    # 重新计算分数
                    original_score = result.get('score', 0)
                    priority_bonus = 1.0 / (i + 1)
                    result['enhanced_score'] = original_score * (1 + priority_bonus * 0.1)
                
                all_results.extend(results)
                
            except Exception as e:
                logger.warning(f"搜索失败: {str(e)}")
                continue
        
        # 去重和排序
        seen_contents = set()
        unique_results = []
        
        for result in all_results:
            content = result.get('content', '')
            content_hash = hash(content[:100])
            
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        sorted_results = sorted(unique_results, 
                              key=lambda x: x.get('enhanced_score', x.get('score', 0)), 
                              reverse=True)
        
        return sorted_results[:top_k]
    
    def get_llm_identification_summary(self) -> Dict:
        """获取LLM识别的仪表类型总结"""
        if not self.instrument_types:
            return {
                'status': 'not_loaded',
                'message': '尚未加载LLM识别结果，请先运行 build_index.py'
            }
        
        summary = {
            'status': 'loaded',
            'total_types': len(self.instrument_types),
            'categories': {},
            'top_instruments': []
        }
        
        # 按类别分组
        for instrument, info in self.instrument_types.items():
            category = info.get('category', '其他')
            if category not in summary['categories']:
                summary['categories'][category] = []
            summary['categories'][category].append({
                'name': instrument,
                'frequency': info.get('frequency', 0)
            })
        
        # 按频次排序
        sorted_instruments = sorted(
            self.instrument_types.items(),
            key=lambda x: x[1].get('frequency', 0),
            reverse=True
        )
        
        summary['top_instruments'] = [
            {
                'name': name,
                'category': info.get('category', '其他'),
                'frequency': info.get('frequency', 0)
            }
            for name, info in sorted_instruments[:10]
        ]
        
        return summary

def test_llm_enhanced_retriever():
    """测试LLM增强的RAG检索器"""
    print("🧪 测试LLM增强的RAG检索器")
    print("=" * 60)
    
    try:
        retriever = LLMEnhancedRAGRetriever()
        
        summary = retriever.get_llm_identification_summary()
        
        if summary['status'] == 'loaded':
            print(f"✅ LLM识别状态: 已加载")
            print(f"📊 识别仪表类型: {summary['total_types']}种")
            print(f"📋 涵盖类别: {list(summary['categories'].keys())}")
            
            print(f"\n🏆 识别的主要仪表类型:")
            for i, instrument in enumerate(summary['top_instruments'][:5], 1):
                print(f"   {i}. {instrument['name']} (类别: {instrument['category']}, 频次: {instrument['frequency']})")
        else:
            print(f"⚠️ LLM识别状态: {summary['message']}")
            return
        
        # 测试查询
        test_queries = [
            "热电偶安装要求",
            "压力变送器接线方法", 
            "电磁流量计安装位置"
        ]
        
        print(f"\n🔍 测试智能查询增强效果:")
        
        for query in test_queries:
            print(f"\n📝 查询: '{query}'")
            print("-" * 40)
            
            identified_type = retriever.intelligent_instrument_identification(query)
            enhanced_queries = retriever.generate_enhanced_queries(query, identified_type)
            results = retriever.advanced_search(query, top_k=3)
            
            print(f"🎯 识别仪表: {identified_type or '未识别'}")
            print(f"🔄 增强查询: {enhanced_queries}")
            print(f"📊 搜索结果: {len(results)}个")
        
        print(f"\n✅ 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    test_llm_enhanced_retriever()
 