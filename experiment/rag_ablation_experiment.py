"""
RAG增强模块消融与对比实验
实验目的：比较智能重排序RAG vs 标准RAG vs 无RAG的性能差异
"""

import json
import random
import time
from datetime import datetime
from typing import List, Dict, Any
import os
import sys

# 导入项目模块
from comprehensive_evaluation_metrics import integrate_comprehensive_metrics
from tools.enhanced_rag_retriever import EnhancedRAGRetriever
from tools.generate_installation_recommendation import generate_installation_recommendation
from config.settings import get_openai_config
from langchain_openai import ChatOpenAI

class RAGAblationExperiment:
    """RAG消融实验类"""
    
    def __init__(self):
        # 初始化LLM
        openai_config = get_openai_config()
        self.llm = ChatOpenAI(
            model=openai_config["model"],
            openai_api_key=openai_config["api_key"],
            openai_api_base=openai_config["base_url"],
            temperature=0.1
        )
        self.enhanced_rag = EnhancedRAGRetriever()
        
        # 实验配置
        self.experiment_name = "RAG增强模块消融对比实验"
        self.total_samples = 10
        
        # 实验组配置
        self.experiment_groups = {
            "enhanced_rag": {
                "name": "智能重排序RAG",
                "description": "使用增强RAG检索器，包含智能重排序和多段拼接",
                "use_rag": True,
                "use_enhanced": True
            },
            "standard_rag": {
                "name": "标准RAG", 
                "description": "使用基础RAG检索，无重排序优化",
                "use_rag": True,
                "use_enhanced": False
            },
            "no_rag": {
                "name": "无RAG",
                "description": "仅使用LLM，不进行知识检索",
                "use_rag": False,
                "use_enhanced": False
            }
        }
        
        # 测试仪表样本
        self.test_instruments = [
            "温度变送器TT-101",
            "压力表PI-201", 
            "流量计FT-301",
            "液位计LT-401",
            "pH计AT-501",
            "电导率计CT-601",
            "氧分析仪OT-701",
            "热电偶TE-801",
            "压力变送器PT-901",
            "差压变送器DPT-111",
            "涡街流量计VFT-121",
            "电磁流量计EFT-131",
            "雷达液位计RLT-141",
            "超声波液位计ULT-151",
            "可燃气体检测器GT-161",
            "调节阀CV-171",
            "电磁阀SV-181",
            "安全阀PSV-191",
            "止回阀CV-201",
            "球阀BV-211"
        ]
        
        # 随机选择测试样本
        random.seed(42)  # 固定随机种子确保可重现
        self.selected_instruments = random.sample(self.test_instruments, self.total_samples)
        
        print(f"🔬 初始化{self.experiment_name}")
        print(f"📊 实验样本数: {self.total_samples}")
        print(f"🎯 实验组数: {len(self.experiment_groups)}")
        print(f"📋 选中的测试仪表: {', '.join(self.selected_instruments[:5])}...")

    def generate_recommendation_enhanced_rag(self, instrument_desc: str) -> str:
        """使用增强RAG生成推荐"""
        try:
            # 使用增强RAG检索器
            retrieval_result = self.enhanced_rag.enhanced_retrieve(
                query=instrument_desc,
                top_k=5
            )
            
            # 构建增强提示
            context_parts = []
            for doc in retrieval_result['documents']:
                context_parts.append(f"参考资料：{doc['content']}")
            
            enhanced_context = "\n\n".join(context_parts)
            
            # 多段拼接提示模板
            prompt = f"""
请基于以下参考资料，为仪表"{instrument_desc}"生成专业的安装推荐方案。

{enhanced_context}

要求：
1. 结合参考资料中的相关内容
2. 包含安装位置选择、安装步骤、材料清单、安全要求等
3. 内容专业、详细、可操作
4. 字数控制在800-1200字

请生成安装推荐：
"""
            
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            print(f"❌ 增强RAG生成失败: {e}")
            return f"增强RAG生成失败: {str(e)}"

    def generate_recommendation_standard_rag(self, instrument_desc: str) -> str:
        """使用标准RAG生成推荐"""
        try:
            # 使用基础检索（不含重排序）
            retrieval_result = self.enhanced_rag.basic_retrieve(
                query=instrument_desc,
                top_k=3  # 标准RAG使用较少的检索结果
            )
            
            # 简单拼接
            if retrieval_result and len(retrieval_result) > 0:
                context = "\n".join([doc.page_content for doc in retrieval_result])
            else:
                context = "未找到相关参考资料"
            
            # 标准RAG提示模板
            prompt = f"""
参考资料：
{context}

请为仪表"{instrument_desc}"生成安装推荐方案，包括安装位置、步骤、材料和安全要求。

安装推荐：
"""
            
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            print(f"❌ 标准RAG生成失败: {e}")
            return f"标准RAG生成失败: {str(e)}"

    def generate_recommendation_no_rag(self, instrument_desc: str) -> str:
        """不使用RAG生成推荐"""
        try:
            # 纯LLM提示
            prompt = f"""
请为仪表"{instrument_desc}"生成专业的安装推荐方案。

要求包含以下内容：
1. 安装位置选择原则
2. 具体安装步骤
3. 所需材料清单  
4. 安全注意事项

请基于您的专业知识生成详细的安装推荐：
"""
            
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            print(f"❌ 无RAG生成失败: {e}")
            return f"无RAG生成失败: {str(e)}"

    def run_single_experiment(self, instrument: str, group_key: str) -> Dict[str, Any]:
        """运行单个实验"""
        group_config = self.experiment_groups[group_key]
        
        print(f"  🔧 运行 {group_config['name']} - {instrument}")
        
        start_time = time.time()
        
        # 根据实验组配置生成推荐
        if group_key == "enhanced_rag":
            recommendation = self.generate_recommendation_enhanced_rag(instrument)
        elif group_key == "standard_rag":
            recommendation = self.generate_recommendation_standard_rag(instrument)
        else:  # no_rag
            recommendation = self.generate_recommendation_no_rag(instrument)
        
        generation_time = time.time() - start_time
        
        # 使用综合评估系统评估
        try:
            eval_start = time.time()
            evaluation_result = integrate_comprehensive_metrics(recommendation)
            eval_time = time.time() - eval_start
            
            # 提取关键指标
            result = {
                "instrument": instrument,
                "group": group_key,
                "group_name": group_config["name"],
                "recommendation": recommendation,
                "generation_time": round(generation_time, 2),
                "evaluation_time": round(eval_time, 2),
                "comprehensive_score": evaluation_result["comprehensive_score"],
                "comprehensive_level": evaluation_result["comprehensive_level"],
                "coverage_score": evaluation_result["content_coverage"]["overall_coverage_score"],
                "usability_score": evaluation_result["usability_operability"]["usability_score"],
                "quality_score": evaluation_result["quality_review"]["aggregated"].get("overall_quality_score", 0),
                "evaluation_success": True
            }
            
            print(f"    ✅ 完成 - 综合得分: {result['comprehensive_score']:.1f}")
            
        except Exception as e:
            print(f"    ❌ 评估失败: {e}")
            result = {
                "instrument": instrument,
                "group": group_key,
                "group_name": group_config["name"],
                "recommendation": recommendation,
                "generation_time": round(generation_time, 2),
                "evaluation_time": 0,
                "comprehensive_score": 0,
                "comprehensive_level": "评估失败",
                "coverage_score": 0,
                "usability_score": 0,
                "quality_score": 0,
                "evaluation_success": False,
                "error": str(e)
            }
        
        return result

    def run_full_experiment(self) -> Dict[str, Any]:
        """运行完整实验"""
        print(f"\n🚀 开始{self.experiment_name}")
        print("=" * 80)
        
        all_results = []
        group_stats = {group: [] for group in self.experiment_groups.keys()}
        
        # 对每个仪表运行所有实验组
        for i, instrument in enumerate(self.selected_instruments, 1):
            print(f"\n📋 测试样本 {i}/{self.total_samples}: {instrument}")
            print("-" * 60)
            
            for group_key in self.experiment_groups.keys():
                result = self.run_single_experiment(instrument, group_key)
                all_results.append(result)
                
                if result["evaluation_success"]:
                    group_stats[group_key].append(result)
        
        # 计算各组统计指标
        print(f"\n📊 实验结果统计分析")
        print("=" * 80)
        
        summary_stats = {}
        for group_key, results in group_stats.items():
            if not results:
                print(f"\n⚠️ {self.experiment_groups[group_key]['name']}: 无有效数据")
                continue
            
            # 计算平均值
            avg_comprehensive = sum(r["comprehensive_score"] for r in results) / len(results)
            avg_coverage = sum(r["coverage_score"] for r in results) / len(results)
            avg_usability = sum(r["usability_score"] for r in results) / len(results)
            avg_quality = sum(r["quality_score"] for r in results) / len(results)
            avg_gen_time = sum(r["generation_time"] for r in results) / len(results)
            
            # 计算标准差
            comp_scores = [r["comprehensive_score"] for r in results]
            std_comprehensive = (sum((x - avg_comprehensive) ** 2 for x in comp_scores) / len(comp_scores)) ** 0.5
            
            stats = {
                "group_name": self.experiment_groups[group_key]["name"],
                "sample_count": len(results),
                "avg_comprehensive": round(avg_comprehensive, 2),
                "avg_coverage": round(avg_coverage, 2),
                "avg_usability": round(avg_usability, 2),
                "avg_quality": round(avg_quality, 2),
                "avg_generation_time": round(avg_gen_time, 2),
                "std_comprehensive": round(std_comprehensive, 2),
                "min_score": min(comp_scores),
                "max_score": max(comp_scores)
            }
            
            summary_stats[group_key] = stats
            
            print(f"\n📈 {stats['group_name']} (样本数: {stats['sample_count']})")
            print(f"  🎯 平均综合得分: {stats['avg_comprehensive']} ± {stats['std_comprehensive']}")
            print(f"  📊 平均内容覆盖: {stats['avg_coverage']}")
            print(f"  🔧 平均可用性: {stats['avg_usability']}")
            print(f"  👨‍🔬 平均质量评审: {stats['avg_quality']}")
            print(f"  ⏱️ 平均生成时间: {stats['avg_generation_time']}秒")
            print(f"  📈 得分范围: {stats['min_score']:.1f} - {stats['max_score']:.1f}")
        
        # 组装完整结果
        experiment_result = {
            "experiment_info": {
                "name": self.experiment_name,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "total_samples": self.total_samples,
                "selected_instruments": self.selected_instruments,
                "experiment_groups": self.experiment_groups
            },
            "detailed_results": all_results,
            "summary_statistics": summary_stats,
            "performance_comparison": self.analyze_performance_comparison(summary_stats)
        }
        
        return experiment_result

    def analyze_performance_comparison(self, summary_stats: Dict) -> Dict:
        """分析性能对比"""
        if len(summary_stats) < 2:
            return {"analysis": "数据不足，无法进行对比分析"}
        
        # 提取各组的综合得分
        scores = {}
        for group_key, stats in summary_stats.items():
            scores[group_key] = stats["avg_comprehensive"]
        
        # 找出最佳和最差表现
        best_group = max(scores, key=scores.get)
        worst_group = min(scores, key=scores.get)
        
        # 计算改进幅度
        improvements = {}
        if "enhanced_rag" in scores:
            base_score = scores["enhanced_rag"]
            for group_key, score in scores.items():
                if group_key != "enhanced_rag":
                    improvement = ((base_score - score) / score) * 100 if score > 0 else 0
                    improvements[group_key] = round(improvement, 1)
        
        analysis = {
            "best_performing_group": {
                "group": best_group,
                "name": summary_stats[best_group]["group_name"],
                "score": scores[best_group]
            },
            "worst_performing_group": {
                "group": worst_group,
                "name": summary_stats[worst_group]["group_name"], 
                "score": scores[worst_group]
            },
            "performance_gap": round(scores[best_group] - scores[worst_group], 2),
            "improvements_over_baselines": improvements,
            "ranking": sorted(scores.items(), key=lambda x: x[1], reverse=True)
        }
        
        return analysis

    def save_results(self, results: Dict, filename: str = None):
        """保存实验结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rag_ablation_experiment_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 实验结果已保存到: {filename}")
        return filename

def main():
    """主函数"""
    print("🔬 RAG增强模块消融与对比实验")
    print("实验目的：比较智能重排序RAG vs 标准RAG vs 无RAG的性能差异")
    print("=" * 80)
    
    # 创建实验实例
    experiment = RAGAblationExperiment()
    
    # 运行实验
    results = experiment.run_full_experiment()
    
    # 保存结果
    experiment.save_results(results)
    
    # 显示核心结论
    print(f"\n🎉 实验完成！")
    print("📊 核心发现:")
    
    perf_analysis = results["performance_comparison"]
    if "best_performing_group" in perf_analysis:
        best = perf_analysis["best_performing_group"]
        worst = perf_analysis["worst_performing_group"]
        gap = perf_analysis["performance_gap"]
        
        print(f"  🏆 最佳方案: {best['name']} ({best['score']:.1f}分)")
        print(f"  📉 最差方案: {worst['name']} ({worst['score']:.1f}分)")
        print(f"  📈 性能差距: {gap:.1f}分")
        
        if "improvements_over_baselines" in perf_analysis:
            print("  💡 增强RAG相对改进:")
            for group, improvement in perf_analysis["improvements_over_baselines"].items():
                group_name = results["experiment_info"]["experiment_groups"][group]["name"]
                print(f"    vs {group_name}: +{improvement}%")

if __name__ == "__main__":
    main() 