"""
安装规范检索工具
从向量数据库中检索与仪表类型相关的规范段落
"""
import os
import pickle
from typing import List, Dict, Tuple, Optional
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tools.build_index import DocumentIndexer

# 配置常量
FAISS_INDEX_PATH = "./data/indexes/instrument_standards.index"

logger = logging.getLogger(__name__)

class StandardClauseRetriever:
    """标准规范检索器"""
    
    def __init__(self, index_path: str = None):
        """
        初始化检索器
        
        Args:
            index_path: 向量索引文件路径
        """
        self.index_path = index_path or FAISS_INDEX_PATH
        self.indexer = DocumentIndexer()
        self.is_loaded = False
        
    def load_index(self) -> bool:
        """
        加载向量索引
        
        Returns:
            是否加载成功
        """
        if self.is_loaded:
            return True
        
        if not os.path.exists(self.index_path):
            logger.error(f"索引文件不存在: {self.index_path}")
            return False
        
        success = self.indexer.load_index(self.index_path)
        self.is_loaded = success
        return success
    
    def search_related_clauses(self, query: str, top_k: int = 5, min_similarity: float = 0.5) -> List[Dict]:
        """
        搜索与查询相关的规范条款
        
        Args:
            query: 查询字符串
            top_k: 返回最相关的k个结果
            min_similarity: 最小相似度阈值(降低到0.5以提高召回率)
        
        Returns:
            相关条款列表，每个条款包含content, score, metadata
        """
        if not self.is_loaded:
            if not self.load_index():
                return []
        
        try:
            # 对查询进行嵌入
            query_embedding = self.indexer.model.encode([query])
            
            # 标准化查询向量
            faiss.normalize_L2(query_embedding)
            
            # 在索引中搜索更多候选结果
            search_k = min(top_k * 4, 30)  # 🎯 从3倍增加到4倍，最大从20增加到30，获取更多候选结果进行质量过滤
            scores, indices = self.indexer.index.search(query_embedding.astype(np.float32), search_k)
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 无效索引
                    continue
                
                if score < min_similarity:  # 相似度太低
                    continue
                
                content = self.indexer.documents[idx]
                
                # 质量过滤：排除明显不相关的内容
                if self._is_low_quality_match(content, query):
                    continue
                
                result = {
                    'content': content,
                    'score': float(score),
                    'metadata': self.indexer.metadata[idx],
                    'rank': i + 1
                }
                results.append(result)
                
                # 达到目标数量就停止
                if len(results) >= top_k:
                    break
            
            logger.info(f"查询 '{query}' 找到 {len(results)} 个相关条款")
            return results
            
        except Exception as e:
            logger.error(f"搜索规范条款时出错: {str(e)}")
            return []
    
    def _is_low_quality_match(self, content: str, query: str) -> bool:
        """
        判断是否为低质量匹配
        
        Args:
            content: 匹配的内容
            query: 查询词
        
        Returns:
            True表示低质量，应该过滤
        """
        # 过滤过短的内容
        if len(content.strip()) < 15:
            return True
        
        # 过滤只有标题没有实质内容的条款
        title_only_patterns = [
            r'^[一二三四五六七八九十\d+]+[、．\.\s]*[^。！？]*$',  # 只有编号和短标题
            r'^第\s*\d+\.\d+\.\d+\s*条\s*[^。！？]{0,20}$',  # 只有条款号和短标题
            r'^[^。！？]{0,30}$',  # 内容太短，可能只是标题片段
        ]
        
        for pattern in title_only_patterns:
            import re
            if re.match(pattern, content.strip()):
                return True
        
        # 过滤明显不相关的内容（通过关键词检查）
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 更严格的仪表类型匹配检查
        instrument_type_map = {
            '温度': ['温度', '热电偶', '热电阻', '温度计', '感温'],
            '压力': ['压力', '压力表', '压力变送器', '压力取源'],
            '流量': ['流量', '流量计', '流量变送器', '转子流量', '电磁流量'],
            '液位': ['液位', '液位计', '液位变送器', '浮筒', '浮简', '物位'],
            '控制': ['控制', '控制箱', '控制柜', '电动门', '调节阀'],
            '调节阀': ['调节阀', '执行机构', '阀体', '气动'],
            '电动门': ['电动门', '控制箱', '联锁', '开关']
        }
        
        # 确定查询的仪表类型
        query_type = None
        for inst_type, keywords in instrument_type_map.items():
            if any(kw in query_lower for kw in keywords):
                query_type = inst_type
                break
        
        # 如果确定了查询类型，检查内容是否匹配
        if query_type:
            type_keywords = instrument_type_map[query_type]
            content_matches_type = any(kw in content_lower for kw in type_keywords)
            
            # 检查是否包含其他仪表类型（交叉污染）
            other_types = [t for t in instrument_type_map.keys() if t != query_type]
            has_cross_contamination = False
            
            for other_type in other_types:
                other_keywords = instrument_type_map[other_type]
                # 如果内容强烈指向其他仪表类型，则认为是交叉污染
                other_matches = sum(1 for kw in other_keywords if kw in content_lower)
                if other_matches >= 2:  # 包含2个或以上其他类型关键词
                    has_cross_contamination = True
                    break
            
            # 如果不匹配目标类型，或者有严重交叉污染，则过滤
            if not content_matches_type or has_cross_contamination:
                return True
            
            # 额外检查：如果查询是具体仪表类型，内容却是通用条款，也过滤
            if query_type in ['温度', '压力', '流量', '液位']:
                generic_phrases = ['仪表安装', '安装规则', '通用要求', '一般规定']
                if any(phrase in content_lower for phrase in generic_phrases) and len(content) < 100:
                    return True
        
        return False
    
    def search_by_instrument_type(self, instrument_type: str, top_k: int = 5) -> List[Dict]:
        """
        根据仪表类型搜索相关安装规范
        
        Args:
            instrument_type: 仪表类型（如：热电偶、压力表等）
            top_k: 返回结果数量
        
        Returns:
            相关规范条款列表
        """
        # 优化查询策略：更精确的查询词组合
        queries = [
            f"{instrument_type}安装",
            f"{instrument_type}安装要求",
            f"{instrument_type}安装方法", 
            f"{instrument_type}安装位置",
            f"{instrument_type}安装规范"
        ]
        
        all_results = []
        seen_contents = set()  # 避免重复结果
        
        for query in queries:
            # 每个查询最多取2个结果，提高精度  
            results = self.search_related_clauses(query, top_k=2, min_similarity=0.5)
            
            for result in results:
                content = result['content']
                if content not in seen_contents:
                    seen_contents.add(content)
                    result['query'] = query
                    all_results.append(result)
        
        # 按相似度分数排序
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 返回前top_k个结果
        return all_results[:top_k]
    
    def search_installation_materials(self, instrument_type: str, top_k: int = 3) -> List[Dict]:
        """
        搜索与仪表类型相关的安装材料要求
        
        Args:
            instrument_type: 仪表类型
            top_k: 返回结果数量
        
        Returns:
            材料要求条款列表
        """
        material_queries = [
            f"{instrument_type}安装材料",
            f"{instrument_type}管路材料",
            f"{instrument_type}阀门选择",
            f"{instrument_type}电缆要求",
            "管路材料要求",
            "阀门选择标准",
            "电缆安装要求"
        ]
        
        all_results = []
        seen_contents = set()
        
        for query in material_queries:
            results = self.search_related_clauses(query, top_k=2)
            
            for result in results:
                content = result['content']
                if content not in seen_contents and any(keyword in content for keyword in ['材料', '阀门', '电缆', '管路']):
                    seen_contents.add(content)
                    result['query'] = query
                    all_results.append(result)
        
        # 按相似度排序
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        return all_results[:top_k]
    
    def get_comprehensive_standards(self, instrument_type: str) -> Dict[str, List[Dict]]:
        """
        获取某仪表类型的综合安装规范信息
        
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
        
        # 搜索安装方法
        installation_results = self.search_by_instrument_type(instrument_type, top_k=3)
        result['installation_methods'] = installation_results
        
        # 搜索材料要求
        material_results = self.search_installation_materials(instrument_type, top_k=3)
        result['material_requirements'] = material_results
        
        # 搜索安全要求
        safety_queries = [f"{instrument_type}安全要求", "安全注意事项", "防护要求"]
        for query in safety_queries:
            safety_results = self.search_related_clauses(query, top_k=2)
            for res in safety_results:
                if any(keyword in res['content'] for keyword in ['安全', '防护', '注意']):
                    result['safety_requirements'].append(res)
                    break
        
        # 搜索维护要求
        maintenance_queries = [f"{instrument_type}维护", "维护保养", "检修要求"]
        for query in maintenance_queries:
            maintenance_results = self.search_related_clauses(query, top_k=2)
            for res in maintenance_results:
                if any(keyword in res['content'] for keyword in ['维护', '保养', '检修']):
                    result['maintenance_requirements'].append(res)
                    break
        
        return result

def match_standard_clause(instrument_type: str, query_type: str = "installation", top_k: int = 5) -> List[str]:
    """
    匹配标准条款的便捷函数
    
    Args:
        instrument_type: 仪表类型
        query_type: 查询类型 ("installation", "materials", "safety", "maintenance")
        top_k: 返回结果数量
    
    Returns:
        匹配的文本段落列表
    """
    retriever = StandardClauseRetriever()
    
    if query_type == "installation":
        results = retriever.search_by_instrument_type(instrument_type, top_k)
    elif query_type == "materials":
        results = retriever.search_installation_materials(instrument_type, top_k)
    else:
        # 自定义查询
        query = f"{instrument_type}{query_type}"
        results = retriever.search_related_clauses(query, top_k)
    
    # 返回文本内容列表
    return [result['content'] for result in results]

def search_standards_by_keywords(keywords: List[str], top_k: int = 5) -> List[Dict]:
    """
    基于关键词搜索标准规范
    
    Args:
        keywords: 关键词列表
        top_k: 返回结果数量
    
    Returns:
        搜索结果列表
    """
    retriever = StandardClauseRetriever()
    
    # 组合关键词为查询
    query = " ".join(keywords)
    
    return retriever.search_related_clauses(query, top_k)

def match_standards_for_instruments(instruments_df) -> List[str]:
    """
    为仪表DataFrame批量匹配标准条款
    
    Args:
        instruments_df: 包含仪表信息的DataFrame，需包含'仪表类型'列
    
    Returns:
        匹配标准列表，与输入DataFrame行对应
    """
    retriever = StandardClauseRetriever()
    matched_standards = []
    
    for _, row in instruments_df.iterrows():
        instrument_type = row.get('仪表类型', '未知仪表')
        
        try:
            # 搜索该仪表类型的安装规范
            results = retriever.search_by_instrument_type(instrument_type, top_k=1)
            
            if results:
                # 取最匹配的标准条款
                best_match = results[0]['content']
                # 截取前100字符作为简要描述
                if len(best_match) > 100:
                    best_match = best_match[:100] + "..."
                matched_standards.append(best_match)
            else:
                matched_standards.append("未找到匹配的安装标准")
                
        except Exception as e:
            logger.error(f"匹配标准时出错 ({instrument_type}): {str(e)}")
            matched_standards.append("标准匹配失败")
    
    return matched_standards

def get_installation_summary(instrument_type: str) -> str:
    """
    获取仪表安装要求摘要
    
    Args:
        instrument_type: 仪表类型
    
    Returns:
        安装要求摘要文本
    """
    retriever = StandardClauseRetriever()
    comprehensive_info = retriever.get_comprehensive_standards(instrument_type)
    
    summary_parts = [f"# {instrument_type}安装规范摘要\n"]
    
    # 安装方法
    if comprehensive_info['installation_methods']:
        summary_parts.append("## 安装方法")
        for i, method in enumerate(comprehensive_info['installation_methods'][:2], 1):
            summary_parts.append(f"{i}. {method['content'][:200]}...")
        summary_parts.append("")
    
    # 材料要求
    if comprehensive_info['material_requirements']:
        summary_parts.append("## 材料要求")
        for i, material in enumerate(comprehensive_info['material_requirements'][:2], 1):
            summary_parts.append(f"{i}. {material['content'][:200]}...")
        summary_parts.append("")
    
    # 安全要求
    if comprehensive_info['safety_requirements']:
        summary_parts.append("## 安全要求")
        for i, safety in enumerate(comprehensive_info['safety_requirements'][:1], 1):
            summary_parts.append(f"{i}. {safety['content'][:200]}...")
    
    return "\n".join(summary_parts)

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 首先确保有索引文件（如果没有则构建）
    from tools.build_index import create_sample_standards_data, build_index_from_files
    
    if not os.path.exists(FAISS_INDEX_PATH):
        print("索引文件不存在，正在创建示例索引...")
        sample_file = create_sample_standards_data()
        build_index_from_files([sample_file])
    
    # 测试检索功能
    retriever = StandardClauseRetriever()
    
    test_instrument_types = ["热电偶", "压力表", "流量计"]
    
    for instrument_type in test_instrument_types:
        print(f"\n{'='*50}")
        print(f"测试检索: {instrument_type}")
        print('='*50)
        
        # 测试基本检索
        results = retriever.search_by_instrument_type(instrument_type, top_k=2)
        print(f"\n{instrument_type}相关规范 ({len(results)}条):")
        for i, result in enumerate(results, 1):
            print(f"{i}. 相似度: {result['score']:.3f}")
            print(f"   内容: {result['content'][:100]}...")
        
        # 测试综合信息检索
        comprehensive = retriever.get_comprehensive_standards(instrument_type)
        print(f"\n{instrument_type}综合信息:")
        print(f"- 安装方法: {len(comprehensive['installation_methods'])}条")
        print(f"- 材料要求: {len(comprehensive['material_requirements'])}条")
        print(f"- 安全要求: {len(comprehensive['safety_requirements'])}条")
    
    print("\n安装规范检索工具已就绪") 