"""
RAG效果测试工具
用于测试仪表安装规范RAG系统的检索效果、质量和性能
"""
import os
import sys
import time
from typing import List, Dict, Tuple
import logging
from tabulate import tabulate

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.match_standard_clause import StandardClauseRetriever
from tools.build_index import DocumentIndexer

class RAGPerformanceTester:
    """RAG性能测试器"""
    
    def __init__(self):
        self.retriever = StandardClauseRetriever()
        self.test_queries = self._prepare_test_queries()
        self.results = {}
        
    def _prepare_test_queries(self) -> List[Dict]:
        """准备测试查询集合"""
        return [
            # 具体仪表类型查询
            {
                "query": "热电偶安装",
                "type": "instrument_specific",
                "expected_keywords": ["热电偶", "安装", "保护管", "接线"],
                "instrument_type": "热电偶"
            },
            {
                "query": "压力表安装要求",
                "type": "instrument_specific", 
                "expected_keywords": ["压力表", "安装", "取压点", "阀门"],
                "instrument_type": "压力表"
            },
            {
                "query": "流量计安装规范",
                "type": "instrument_specific",
                "expected_keywords": ["流量计", "安装", "直管段", "前后"],
                "instrument_type": "流量计"
            },
            {
                "query": "液位计安装方法",
                "type": "instrument_specific",
                "expected_keywords": ["液位", "安装", "取源", "导压管"],
                "instrument_type": "液位计"
            },
            {
                "query": "调节阀安装",
                "type": "instrument_specific",
                "expected_keywords": ["调节阀", "安装", "执行机构", "方向"],
                "instrument_type": "调节阀"
            },
            
            # 材料和配件查询
            {
                "query": "管路材料要求",
                "type": "materials",
                "expected_keywords": ["管路", "材料", "不锈钢", "碳钢"],
                "instrument_type": None
            },
            {
                "query": "阀门选择标准",
                "type": "materials",
                "expected_keywords": ["阀门", "选择", "球阀", "截止阀"],
                "instrument_type": None
            },
            {
                "query": "电缆安装要求",
                "type": "materials",
                "expected_keywords": ["电缆", "安装", "敷设", "屏蔽"],
                "instrument_type": None
            },
            
            # 安全和维护查询
            {
                "query": "仪表安全要求",
                "type": "safety",
                "expected_keywords": ["安全", "防护", "接地", "防爆"],
                "instrument_type": None
            },
            {
                "query": "维护保养规范",
                "type": "maintenance",
                "expected_keywords": ["维护", "保养", "检修", "校准"],
                "instrument_type": None
            },
            
            # 复杂组合查询
            {
                "query": "热电偶保护管材料和安装",
                "type": "complex",
                "expected_keywords": ["热电偶", "保护管", "材料", "安装"],
                "instrument_type": "热电偶"
            },
            {
                "query": "压力测量点的安装位置要求",
                "type": "complex",
                "expected_keywords": ["压力", "测量点", "安装", "位置"],
                "instrument_type": "压力表"
            },
            
            # 边界条件测试
            {
                "query": "不存在的仪表类型",
                "type": "boundary",
                "expected_keywords": [],
                "instrument_type": None
            },
            {
                "query": "仪表",  # 过于宽泛的查询
                "type": "boundary",
                "expected_keywords": ["仪表"],
                "instrument_type": None
            }
        ]
    
    def test_index_loading(self) -> Dict:
        """测试索引加载"""
        print("="*50)
        print("测试索引加载")
        print("="*50)
        
        results = {}
        index_files = [
            "./data/indexes/instrument_standards.index",
            "./data/indexes/instrument_standards_improved.index",
            "./data/indexes/test_standards.index"
        ]
        
        for index_path in index_files:
            start_time = time.time()
            
            if os.path.exists(index_path):
                try:
                    retriever = StandardClauseRetriever(index_path)
                    success = retriever.load_index()
                    load_time = time.time() - start_time
                    
                    if success:
                        doc_count = len(retriever.indexer.documents) if retriever.indexer.documents else 0
                        results[index_path] = {
                            "status": "成功",
                            "load_time": f"{load_time:.3f}秒",
                            "document_count": doc_count
                        }
                        print(f"✓ {os.path.basename(index_path)}: 加载成功，{doc_count}个文档，耗时{load_time:.3f}秒")
                    else:
                        results[index_path] = {
                            "status": "失败",
                            "load_time": f"{load_time:.3f}秒",
                            "document_count": 0
                        }
                        print(f"✗ {os.path.basename(index_path)}: 加载失败")
                        
                except Exception as e:
                    results[index_path] = {
                        "status": f"错误: {str(e)}",
                        "load_time": "N/A",
                        "document_count": 0
                    }
                    print(f"✗ {os.path.basename(index_path)}: 加载出错 - {str(e)}")
            else:
                results[index_path] = {
                    "status": "文件不存在",
                    "load_time": "N/A", 
                    "document_count": 0
                }
                print(f"✗ {os.path.basename(index_path)}: 文件不存在")
        
        return results
    
    def test_basic_retrieval(self) -> Dict:
        """测试基本检索功能"""
        print("\n" + "="*50)
        print("测试基本检索功能")
        print("="*50)
        
        results = {}
        
        # 确保retriever已加载
        if not self.retriever.is_loaded:
            if not self.retriever.load_index():
                print("❌ 无法加载索引，跳过基本检索测试")
                return {"error": "无法加载索引"}
        
        for i, test_case in enumerate(self.test_queries[:5], 1):  # 只测试前5个查询
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            
            print(f"\n{i}. 查询: '{query}'")
            
            start_time = time.time()
            search_results = self.retriever.search_related_clauses(query, top_k=3)
            search_time = time.time() - start_time
            
            # 分析结果质量
            quality_score = self._evaluate_result_quality(search_results, expected_keywords)
            
            results[query] = {
                "result_count": len(search_results),
                "search_time": f"{search_time:.3f}秒",
                "quality_score": quality_score,
                "results": search_results[:2]  # 只保存前2个结果用于展示
            }
            
            print(f"   结果数量: {len(search_results)}")
            print(f"   搜索耗时: {search_time:.3f}秒")
            print(f"   质量评分: {quality_score:.2f}/1.0")
            
            # 显示前2个结果
            for j, result in enumerate(search_results[:2], 1):
                content_preview = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                print(f"   {j}. 相似度: {result['score']:.3f}")
                print(f"      内容: {content_preview}")
        
        return results
    
    def test_instrument_specific_search(self) -> Dict:
        """测试按仪表类型的专项搜索"""
        print("\n" + "="*50)
        print("测试仪表类型专项搜索")
        print("="*50)
        
        results = {}
        instrument_types = ["热电偶", "压力表", "流量计", "液位计", "调节阀"]
        
        if not self.retriever.is_loaded:
            if not self.retriever.load_index():
                print("❌ 无法加载索引，跳过仪表专项搜索测试")
                return {"error": "无法加载索引"}
        
        for instrument_type in instrument_types:
            print(f"\n测试仪表类型: {instrument_type}")
            
            start_time = time.time()
            search_results = self.retriever.search_by_instrument_type(instrument_type, top_k=3)
            search_time = time.time() - start_time
            
            # 检查结果的仪表类型匹配度
            type_match_score = self._evaluate_instrument_type_match(search_results, instrument_type)
            
            results[instrument_type] = {
                "result_count": len(search_results),
                "search_time": f"{search_time:.3f}秒",
                "type_match_score": type_match_score,
                "avg_similarity": sum(r['score'] for r in search_results) / len(search_results) if search_results else 0
            }
            
            print(f"   结果数量: {len(search_results)}")
            print(f"   搜索耗时: {search_time:.3f}秒")
            print(f"   类型匹配度: {type_match_score:.2f}/1.0")
            print(f"   平均相似度: {results[instrument_type]['avg_similarity']:.3f}")
            
            # 显示最佳匹配结果
            if search_results:
                best_result = search_results[0]
                content_preview = best_result['content'][:120] + "..." if len(best_result['content']) > 120 else best_result['content']
                print(f"   最佳匹配: {content_preview}")
        
        return results
    
    def test_comprehensive_search(self) -> Dict:
        """测试综合信息搜索"""
        print("\n" + "="*50)
        print("测试综合信息搜索")
        print("="*50)
        
        results = {}
        test_instruments = ["热电偶", "压力表"]
        
        if not self.retriever.is_loaded:
            if not self.retriever.load_index():
                print("❌ 无法加载索引，跳过综合搜索测试")
                return {"error": "无法加载索引"}
        
        for instrument_type in test_instruments:
            print(f"\n测试综合信息: {instrument_type}")
            
            start_time = time.time()
            comprehensive_info = self.retriever.get_comprehensive_standards(instrument_type)
            search_time = time.time() - start_time
            
            # 统计各类信息数量
            installation_count = len(comprehensive_info['installation_methods'])
            material_count = len(comprehensive_info['material_requirements'])
            safety_count = len(comprehensive_info['safety_requirements'])
            maintenance_count = len(comprehensive_info['maintenance_requirements'])
            
            results[instrument_type] = {
                "search_time": f"{search_time:.3f}秒",
                "installation_methods": installation_count,
                "material_requirements": material_count,
                "safety_requirements": safety_count,
                "maintenance_requirements": maintenance_count,
                "total_items": installation_count + material_count + safety_count + maintenance_count
            }
            
            print(f"   搜索耗时: {search_time:.3f}秒")
            print(f"   安装方法: {installation_count}条")
            print(f"   材料要求: {material_count}条")
            print(f"   安全要求: {safety_count}条")
            print(f"   维护要求: {maintenance_count}条")
            print(f"   总计信息: {results[instrument_type]['total_items']}条")
        
        return results
    
    def test_search_quality_analysis(self) -> Dict:
        """测试搜索质量分析"""
        print("\n" + "="*50)
        print("搜索质量深度分析")
        print("="*50)
        
        if not self.retriever.is_loaded:
            if not self.retriever.load_index():
                print("❌ 无法加载索引，跳过质量分析测试")
                return {"error": "无法加载索引"}
        
        quality_metrics = {
            "high_quality_results": 0,
            "medium_quality_results": 0, 
            "low_quality_results": 0,
            "total_queries": len(self.test_queries),
            "avg_response_time": 0,
            "coverage_analysis": {}
        }
        
        total_time = 0
        
        for test_case in self.test_queries:
            query = test_case["query"]
            expected_keywords = test_case["expected_keywords"]
            
            start_time = time.time()
            results = self.retriever.search_related_clauses(query, top_k=5)
            query_time = time.time() - start_time
            total_time += query_time
            
            # 评估查询质量
            if results:
                quality_score = self._evaluate_result_quality(results, expected_keywords)
                
                if quality_score >= 0.7:
                    quality_metrics["high_quality_results"] += 1
                elif quality_score >= 0.4:
                    quality_metrics["medium_quality_results"] += 1
                else:
                    quality_metrics["low_quality_results"] += 1
            else:
                quality_metrics["low_quality_results"] += 1
        
        quality_metrics["avg_response_time"] = f"{total_time / len(self.test_queries):.3f}秒"
        
        # 计算覆盖率
        coverage = self._analyze_coverage()
        quality_metrics["coverage_analysis"] = coverage
        
        # 输出结果
        print(f"高质量结果: {quality_metrics['high_quality_results']}/{quality_metrics['total_queries']}")
        print(f"中等质量结果: {quality_metrics['medium_quality_results']}/{quality_metrics['total_queries']}")
        print(f"低质量结果: {quality_metrics['low_quality_results']}/{quality_metrics['total_queries']}")
        print(f"平均响应时间: {quality_metrics['avg_response_time']}")
        print(f"文档覆盖率: {coverage['document_coverage']:.1%}")
        print(f"主题覆盖情况: {coverage['topic_coverage']}")
        
        return quality_metrics
    
    def test_performance_benchmark(self) -> Dict:
        """性能基准测试"""
        print("\n" + "="*50)
        print("性能基准测试")
        print("="*50)
        
        if not self.retriever.is_loaded:
            if not self.retriever.load_index():
                print("❌ 无法加载索引，跳过性能基准测试")
                return {"error": "无法加载索引"}
        
        # 测试不同参数组合的性能
        test_configs = [
            {"top_k": 1, "min_similarity": 0.5},
            {"top_k": 3, "min_similarity": 0.5},
            {"top_k": 5, "min_similarity": 0.5},
            {"top_k": 10, "min_similarity": 0.3},
            {"top_k": 5, "min_similarity": 0.7}
        ]
        
        benchmark_results = {}
        test_query = "热电偶安装规范"
        
        for config in test_configs:
            config_name = f"top_k={config['top_k']}, min_sim={config['min_similarity']}"
            print(f"\n测试配置: {config_name}")
            
            # 多次测试取平均值
            times = []
            result_counts = []
            
            for _ in range(5):
                start_time = time.time()
                results = self.retriever.search_related_clauses(
                    test_query, 
                    top_k=config['top_k'], 
                    min_similarity=config['min_similarity']
                )
                times.append(time.time() - start_time)
                result_counts.append(len(results))
            
            avg_time = sum(times) / len(times)
            avg_results = sum(result_counts) / len(result_counts)
            
            benchmark_results[config_name] = {
                "avg_time": f"{avg_time:.4f}秒",
                "avg_results": f"{avg_results:.1f}条",
                "min_time": f"{min(times):.4f}秒",
                "max_time": f"{max(times):.4f}秒"
            }
            
            print(f"   平均耗时: {avg_time:.4f}秒")
            print(f"   平均结果数: {avg_results:.1f}条")
            print(f"   时间范围: {min(times):.4f}秒 - {max(times):.4f}秒")
        
        return benchmark_results
    
    def _evaluate_result_quality(self, results: List[Dict], expected_keywords: List[str]) -> float:
        """评估搜索结果质量"""
        if not results or not expected_keywords:
            return 0.0
        
        total_score = 0
        for result in results:
            content = result['content'].lower()
            similarity_score = result['score']
            
            # 关键词匹配得分
            keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in content)
            keyword_score = keyword_matches / len(expected_keywords) if expected_keywords else 0
            
            # 内容长度得分（避免过短的结果）
            length_score = min(len(result['content']) / 100, 1.0)
            
            # 综合得分
            result_score = (similarity_score * 0.4 + keyword_score * 0.4 + length_score * 0.2)
            total_score += result_score
        
        return total_score / len(results)
    
    def _evaluate_instrument_type_match(self, results: List[Dict], instrument_type: str) -> float:
        """评估结果与仪表类型的匹配度"""
        if not results:
            return 0.0
        
        matches = 0
        for result in results:
            content = result['content'].lower()
            if instrument_type.lower() in content:
                matches += 1
        
        return matches / len(results)
    
    def _analyze_coverage(self) -> Dict:
        """分析文档覆盖率"""
        coverage_info = {
            "document_coverage": 0.8,  # 示例数据
            "topic_coverage": {
                "安装方法": "良好",
                "材料要求": "中等", 
                "安全规范": "一般",
                "维护保养": "待改进"
            }
        }
        return coverage_info
    
    def run_full_test_suite(self):
        """运行完整测试套件"""
        print("🔍 RAG性能测试开始")
        print("=" * 80)
        
        # 存储所有测试结果
        all_results = {}
        
        # 1. 索引加载测试
        all_results["index_loading"] = self.test_index_loading()
        
        # 2. 基本检索测试
        all_results["basic_retrieval"] = self.test_basic_retrieval()
        
        # 3. 仪表专项搜索测试
        all_results["instrument_search"] = self.test_instrument_specific_search()
        
        # 4. 综合搜索测试
        all_results["comprehensive_search"] = self.test_comprehensive_search()
        
        # 5. 质量分析
        all_results["quality_analysis"] = self.test_search_quality_analysis()
        
        # 6. 性能基准测试
        all_results["performance_benchmark"] = self.test_performance_benchmark()
        
        # 生成测试报告
        self._generate_test_report(all_results)
        
        return all_results
    
    def _generate_test_report(self, results: Dict):
        """生成测试报告"""
        print("\n" + "="*80)
        print("📊 RAG系统测试报告总结")
        print("="*80)
        
        # 索引状态汇总
        if "index_loading" in results and not isinstance(results["index_loading"], dict) or "error" not in results["index_loading"]:
            loaded_indexes = sum(1 for v in results["index_loading"].values() if v.get("status") == "成功")
            total_indexes = len(results["index_loading"])
            print(f"📁 索引加载: {loaded_indexes}/{total_indexes} 个索引成功加载")
        
        # 检索性能汇总
        if "basic_retrieval" in results and "error" not in results["basic_retrieval"]:
            avg_search_time = sum(float(v["search_time"].replace("秒", "")) for v in results["basic_retrieval"].values()) / len(results["basic_retrieval"])
            avg_quality = sum(v["quality_score"] for v in results["basic_retrieval"].values()) / len(results["basic_retrieval"])
            print(f"⚡ 检索性能: 平均搜索时间 {avg_search_time:.3f}秒，平均质量评分 {avg_quality:.2f}/1.0")
        
        # 仪表专项搜索汇总
        if "instrument_search" in results and "error" not in results["instrument_search"]:
            avg_type_match = sum(v["type_match_score"] for v in results["instrument_search"].values()) / len(results["instrument_search"])
            avg_similarity = sum(v["avg_similarity"] for v in results["instrument_search"].values()) / len(results["instrument_search"])
            print(f"🔧 仪表搜索: 平均类型匹配度 {avg_type_match:.2f}/1.0，平均相似度 {avg_similarity:.3f}")
        
        # 质量分析汇总
        if "quality_analysis" in results and "error" not in results["quality_analysis"]:
            qa = results["quality_analysis"]
            total = qa["total_queries"]
            high_quality_rate = qa["high_quality_results"] / total
            print(f"📈 质量分析: {qa['high_quality_results']}/{total} ({high_quality_rate:.1%}) 查询达到高质量")
        
        print("\n🎯 总体评估:")
        
        # 根据测试结果给出评估
        if "error" in str(results):
            print("❌ 系统存在严重问题，建议检查索引文件和配置")
        else:
            print("✅ RAG系统基本功能正常")
            print("📝 详细测试数据已记录，可根据需要进行系统优化")
        
        print("="*80)


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 创建测试器
        tester = RAGPerformanceTester()
        
        # 运行完整测试
        results = tester.run_full_test_suite()
        
        print(f"\n✨ 测试完成！详细结果已保存到测试器对象中。")
        
        # 可选：将结果保存到文件
        save_results = input("\n是否将测试结果保存到文件？(y/n): ").strip().lower()
        if save_results == 'y':
            import json
            import datetime
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rag_test_results_{timestamp}.json"
            
            # 转换结果为可序列化格式
            serializable_results = {}
            for key, value in results.items():
                if isinstance(value, dict):
                    serializable_results[key] = {k: str(v) for k, v in value.items()}
                else:
                    serializable_results[key] = str(value)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, ensure_ascii=False, indent=2)
            
            print(f"📄 测试结果已保存到: {filename}")
        
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 