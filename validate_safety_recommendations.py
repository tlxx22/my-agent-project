"""
智能体安全推荐有效性验证实验系统
从多个维度验证生成的安装推荐的质量和有效性
"""

import os
import re
import json
from typing import Dict, List, Tuple, Any
from datetime import datetime
import pandas as pd

class SafetyRecommendationValidator:
    """安全推荐验证器"""
    
    def __init__(self, recommendation_dir: str = "recommendation"):
        self.recommendation_dir = recommendation_dir
        self.results = []
        
        # 技术标准关键词库
        self.technical_standards = {
            "国标": ["GB/T", "GB", "国标", "国家标准"],
            "行业标准": ["JB/T", "HG/T", "SH/T", "YB/T"],
            "安全规范": ["安全", "防护", "防爆", "防腐", "防雷", "联锁", "报警"],
            "安装要求": ["安装位置", "安装方式", "连接方式", "固定方式"],
            "材料规格": ["材质", "规格", "型号", "技术参数", "压力等级"],
            "质量控制": ["检查", "测试", "验收", "质量控制"]
        }
        
        # 安全要点检查清单
        self.safety_checklist = {
            "风险识别": ["风险识别", "危险因素", "安全影响", "关键风险"],
            "防护措施": ["防护设备", "技术措施", "安全防护", "保护装置"],
            "安全系统": ["报警系统", "联锁", "监测", "故障"],
            "专项防护": ["防爆", "防腐", "防雷", "防火", "防毒"],
            "操作安全": ["操作规程", "维护安全", "检修安全", "人员防护"],
            "环境要求": ["环境条件", "温度", "湿度", "振动", "腐蚀"]
        }
        
        # 完整性检查项目
        self.completeness_items = [
            "安装位置选择",
            "安装方式与步骤", 
            "材料清单",
            "安全要求",
            "技术参数",
            "质量控制"
        ]

    def validate_all_recommendations(self) -> Dict[str, Any]:
        """验证所有推荐文件"""
        print("🔍 开始验证智能体生成的安全推荐...")
        
        # 获取所有推荐文件
        files = [f for f in os.listdir(self.recommendation_dir) 
                if f.endswith('.md')]
        
        print(f"📁 找到 {len(files)} 个推荐文件")
        
        validation_results = {
            "total_files": len(files),
            "validation_time": datetime.now().isoformat(),
            "individual_results": [],
            "summary_stats": {}
        }
        
        # 逐个验证文件
        for i, filename in enumerate(files, 1):
            print(f"\n📋 验证文件 {i}/{len(files)}: {filename}")
            
            file_path = os.path.join(self.recommendation_dir, filename)
            result = self.validate_single_file(file_path, filename)
            validation_results["individual_results"].append(result)
            
            # 显示进度
            score = result["overall_score"]
            print(f"   总体得分: {score:.1f}/100")
            print(f"   质量等级: {self.get_quality_level(score)}")
        
        # 计算汇总统计
        validation_results["summary_stats"] = self.calculate_summary_stats(
            validation_results["individual_results"]
        )
        
        return validation_results

    def validate_single_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """验证单个推荐文件"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                "filename": filename,
                "error": f"文件读取失败: {str(e)}",
                "overall_score": 0
            }
        
        # 提取基本信息
        basic_info = self.extract_basic_info(content, filename)
        
        # 多维度验证
        technical_score = self.validate_technical_accuracy(content)
        completeness_score = self.validate_completeness(content)
        safety_score = self.validate_safety_coverage(content)
        practicality_score = self.validate_practicality(content)
        compliance_score = self.validate_compliance(content)
        
        # 计算总体得分
        overall_score = (
            technical_score * 0.25 +
            completeness_score * 0.2 +
            safety_score * 0.3 +
            practicality_score * 0.15 +
            compliance_score * 0.1
        )
        
        return {
            "filename": filename,
            "basic_info": basic_info,
            "scores": {
                "technical_accuracy": technical_score,
                "completeness": completeness_score,
                "safety_coverage": safety_score,
                "practicality": practicality_score,
                "compliance": compliance_score
            },
            "overall_score": overall_score,
            "quality_level": self.get_quality_level(overall_score),
            "detailed_analysis": self.get_detailed_analysis(content)
        }

    def extract_basic_info(self, content: str, filename: str) -> Dict[str, str]:
        """提取推荐文件的基本信息"""
        info = {"filename": filename}
        
        # 提取仪表类型
        type_match = re.search(r'(\d{8}_\d{6})_(.+?)_安装推荐\.md', filename)
        if type_match:
            info["timestamp"] = type_match.group(1)
            info["instrument_type"] = type_match.group(2)
        
        # 提取型号
        model_match = re.search(r'\*\*仪表型号：\*\*\s*([^\n]+)', content)
        if model_match:
            info["model"] = model_match.group(1).strip()
        
        # 提取数量
        quantity_match = re.search(r'\*\*数量：\*\*\s*([^\n]+)', content)
        if quantity_match:
            info["quantity"] = quantity_match.group(1).strip()
        
        return info

    def validate_technical_accuracy(self, content: str) -> float:
        """验证技术准确性"""
        score = 0
        max_score = 100
        
        # 检查技术标准引用
        standards_found = 0
        for category, keywords in self.technical_standards.items():
            for keyword in keywords:
                if keyword in content:
                    standards_found += 1
                    break
        
        # 标准引用得分 (30分)
        standards_score = min(30, standards_found * 5)
        score += standards_score
        
        # 检查技术参数完整性 (40分)
        technical_keywords = ["规格", "材质", "压力", "温度", "直径", "长度"]
        param_score = sum(10 for keyword in technical_keywords if keyword in content)
        param_score = min(40, param_score)
        score += param_score
        
        # 检查专业术语使用 (30分)
        professional_terms = ["法兰", "密封", "接线", "防护等级", "耐压", "工艺"]
        term_score = sum(5 for term in professional_terms if term in content)
        term_score = min(30, term_score)
        score += term_score
        
        return min(100, score)

    def validate_completeness(self, content: str) -> float:
        """验证内容完整性"""
        score = 0
        
        # 检查必需章节
        for item in self.completeness_items:
            if item in content:
                score += 100 / len(self.completeness_items)
        
        return score

    def validate_safety_coverage(self, content: str) -> float:
        """验证安全覆盖率"""
        score = 0
        
        # 检查安全要点覆盖
        covered_categories = 0
        for category, keywords in self.safety_checklist.items():
            category_covered = any(keyword in content for keyword in keywords)
            if category_covered:
                covered_categories += 1
        
        score = (covered_categories / len(self.safety_checklist)) * 100
        return score

    def validate_practicality(self, content: str) -> float:
        """验证实用性"""
        score = 0
        
        # 检查具体操作步骤 (40分)
        step_indicators = ["步骤", "流程", "安装", "连接", "固定", "调试"]
        steps_score = sum(8 for indicator in step_indicators if indicator in content)
        steps_score = min(40, steps_score)
        score += steps_score
        
        # 检查具体尺寸和参数 (30分)
        dimension_patterns = [r'\d+mm', r'\d+m', r'Φ\d+', r'DN\d+', r'PN\d+']
        dimensions_found = sum(1 for pattern in dimension_patterns 
                             if re.search(pattern, content))
        dimensions_score = min(30, dimensions_found * 6)
        score += dimensions_score
        
        # 检查材料清单详细程度 (30分)
        material_keywords = ["型号", "规格", "数量", "材质", "标准"]
        material_score = sum(6 for keyword in material_keywords if keyword in content)
        material_score = min(30, material_score)
        score += material_score
        
        return min(100, score)

    def validate_compliance(self, content: str) -> float:
        """验证合规性"""
        score = 0
        
        # 检查国家标准引用 (50分)
        gb_patterns = [r'GB/T\s*\d+', r'GB\s*\d+']
        gb_found = any(re.search(pattern, content) for pattern in gb_patterns)
        if gb_found:
            score += 50
        
        # 检查行业规范 (30分)
        industry_patterns = [r'JB/T\s*\d+', r'HG/T\s*\d+', r'SH/T\s*\d+']
        industry_found = any(re.search(pattern, content) for pattern in industry_patterns)
        if industry_found:
            score += 30
        
        # 检查安全法规关键词 (20分)
        safety_compliance = ["安全生产", "职业健康", "环保", "消防", "防爆"]
        compliance_score = sum(4 for keyword in safety_compliance if keyword in content)
        score += min(20, compliance_score)
        
        return score

    def get_detailed_analysis(self, content: str) -> Dict[str, Any]:
        """获取详细分析"""
        analysis = {
            "word_count": len(content),
            "sections_count": len(re.findall(r'^#+\s+', content, re.MULTILINE)),
            "standards_mentioned": [],
            "safety_keywords_found": [],
            "technical_parameters": []
        }
        
        # 提取提到的标准
        gb_standards = re.findall(r'GB/?T?\s*\d+-?\d*', content)
        analysis["standards_mentioned"] = list(set(gb_standards))
        
        # 提取安全关键词
        safety_keywords = []
        for category, keywords in self.safety_checklist.items():
            found_keywords = [kw for kw in keywords if kw in content]
            safety_keywords.extend(found_keywords)
        analysis["safety_keywords_found"] = list(set(safety_keywords))
        
        # 提取技术参数
        param_patterns = [r'\d+°C', r'\d+MPa', r'DN\d+', r'Φ\d+mm']
        for pattern in param_patterns:
            params = re.findall(pattern, content)
            analysis["technical_parameters"].extend(params)
        
        return analysis

    def get_quality_level(self, score: float) -> str:
        """根据得分获取质量等级"""
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

    def calculate_summary_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """计算汇总统计"""
        if not results:
            return {}
        
        scores = [r["overall_score"] for r in results if "overall_score" in r]
        
        stats = {
            "average_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "quality_distribution": {}
        }
        
        # 质量等级分布
        levels = [self.get_quality_level(score) for score in scores]
        for level in ["优秀", "良好", "中等", "及格", "不合格"]:
            stats["quality_distribution"][level] = levels.count(level)
        
        return stats

    def generate_report(self, validation_results: Dict[str, Any]) -> str:
        """生成验证报告"""
        report = f"""
# 智能体安全推荐验证报告

**验证时间：** {validation_results['validation_time']}
**验证文件总数：** {validation_results['total_files']}

## 总体评估

### 平均得分：{validation_results['summary_stats']['average_score']:.1f}/100

### 质量分布：
"""
        
        for level, count in validation_results['summary_stats']['quality_distribution'].items():
            percentage = (count / validation_results['total_files']) * 100
            report += f"- {level}：{count}个文件 ({percentage:.1f}%)\n"
        
        report += f"""
### 最高得分：{validation_results['summary_stats']['max_score']:.1f}
### 最低得分：{validation_results['summary_stats']['min_score']:.1f}

## 详细结果

"""
        
        # 按得分排序显示详细结果
        sorted_results = sorted(validation_results['individual_results'], 
                              key=lambda x: x.get('overall_score', 0), reverse=True)
        
        for i, result in enumerate(sorted_results[:10], 1):  # 显示前10个
            if 'error' in result:
                report += f"{i}. {result['filename']} - 错误：{result['error']}\n"
            else:
                report += f"{i}. {result['filename']}\n"
                report += f"   总分：{result['overall_score']:.1f} ({result['quality_level']})\n"
                report += f"   技术准确性：{result['scores']['technical_accuracy']:.1f}\n"
                report += f"   完整性：{result['scores']['completeness']:.1f}\n"
                report += f"   安全覆盖：{result['scores']['safety_coverage']:.1f}\n"
                report += f"   实用性：{result['scores']['practicality']:.1f}\n"
                report += f"   合规性：{result['scores']['compliance']:.1f}\n\n"
        
        return report

def main():
    """主函数"""
    print("🚀 启动智能体安全推荐验证实验")
    
    # 检查recommendation目录
    if not os.path.exists("recommendation"):
        print("❌ recommendation目录不存在!")
        return
    
    try:
        # 创建验证器
        validator = SafetyRecommendationValidator()
        
        # 执行验证
        results = validator.validate_all_recommendations()
        
        # 生成报告
        report = validator.generate_report(results)
        
        # 保存结果
        with open("safety_validation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        with open("safety_validation_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        
        print("\n" + "="*60)
        print(report)
        print("="*60)
        
        print(f"\n✅ 验证完成!")
        print(f"📄 详细结果已保存到: safety_validation_results.json")
        print(f"📄 验证报告已保存到: safety_validation_report.md")
        
        # 显示关键指标
        avg_score = results['summary_stats']['average_score']
        print(f"\n🎯 关键指标：")
        print(f"   平均得分：{avg_score:.1f}/100")
        print(f"   验证结果：{'✅ 推荐质量优秀' if avg_score >= 80 else '⚠️ 推荐质量需要改进' if avg_score >= 60 else '❌ 推荐质量不合格'}")
        
    except Exception as e:
        print(f"❌ 验证过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
 
 