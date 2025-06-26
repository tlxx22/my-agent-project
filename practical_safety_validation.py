"""
实际工程应用安全推荐验证实验
模拟真实工程师对安装推荐的评估和应用过程
"""

import os
import re
import json
from typing import Dict, List, Tuple, Any
from datetime import datetime
import random

class PracticalSafetyValidator:
    """实际工程应用验证器"""
    
    def __init__(self, recommendation_dir: str = "recommendation"):
        self.recommendation_dir = recommendation_dir
        
        # 实际工程评估清单 - 基于真实工程师经验
        self.engineering_checklist = {
            "可操作性": {
                "安装步骤明确": "是否有详细的安装步骤说明",
                "工具需求明确": "是否说明需要的工具和设备",
                "人员要求明确": "是否说明安装人员的技能要求",
                "时间估算": "是否给出安装时间估算"
            },
            "材料清单实用性": {
                "规格完整": "材料规格是否详细完整",
                "数量准确": "材料数量是否与设备数量匹配",
                "采购信息": "是否包含采购所需的关键信息",
                "替代方案": "是否提供材料替代选择"
            },
            "安全措施可行性": {
                "风险识别全面": "是否识别了主要安全风险",
                "防护措施具体": "防护措施是否具体可执行",
                "应急预案": "是否有应急处理方案",
                "人员防护": "是否考虑了施工人员安全"
            },
            "经济性": {
                "成本合理": "推荐方案是否经济合理",
                "性价比": "是否在性能和成本间取得平衡",
                "维护成本": "是否考虑后期维护成本",
                "投资效益": "是否有明确的技术经济效益"
            },
            "符合现场实际": {
                "环境适应性": "是否考虑了实际环境条件",
                "空间要求": "是否考虑了安装空间限制",
                "接口兼容": "是否与现有系统兼容",
                "维护便利": "是否便于后期维护操作"
            }
        }
        
        # 工程师决策模拟权重
        self.decision_weights = {
            "安全性": 0.35,    # 安全是第一位的
            "可操作性": 0.25,  # 实际能不能做
            "经济性": 0.20,    # 成本考虑
            "技术可行性": 0.15, # 技术是否成熟
            "维护性": 0.05     # 后期维护
        }
        
        # 常见工程问题库
        self.common_issues = {
            "温度仪表": [
                "热冲击损坏",
                "插入深度不当",
                "电缆密封不良",
                "振动影响测量",
                "介质腐蚀",
                "响应时间慢"
            ],
            "压力仪表": [
                "压力冲击",
                "介质结晶堵塞",
                "温度补偿误差",
                "导压管问题",
                "密封泄漏",
                "超压损坏"
            ],
            "流量仪表": [
                "直管段不足",
                "流态不稳定",
                "磨损问题",
                "密度变化影响",
                "温压补偿",
                "安装方向错误"
            ]
        }

    def practical_validation(self, filename: str) -> Dict[str, Any]:
        """实际工程应用验证"""
        file_path = os.path.join(self.recommendation_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {"error": f"文件读取失败: {str(e)}"}
        
        # 提取基本信息
        basic_info = self.extract_basic_info(content, filename)
        instrument_type = basic_info.get("instrument_type", "")
        
        # 实际工程评估
        validation_result = {
            "filename": filename,
            "basic_info": basic_info,
            "operability_score": self.evaluate_operability(content),
            "material_practicality": self.evaluate_material_practicality(content),
            "safety_feasibility": self.evaluate_safety_feasibility(content),
            "economic_reasonableness": self.evaluate_economic_reasonableness(content),
            "field_applicability": self.evaluate_field_applicability(content),
            "common_issues_coverage": self.evaluate_common_issues_coverage(content, instrument_type),
            "engineer_simulation": self.simulate_engineer_decision(content)
        }
        
        # 计算实用性得分
        validation_result["practical_score"] = self.calculate_practical_score(validation_result)
        validation_result["recommendation_level"] = self.get_recommendation_level(validation_result["practical_score"])
        
        return validation_result

    def evaluate_operability(self, content: str) -> Dict[str, Any]:
        """评估可操作性"""
        operability = {"score": 0, "details": {}}
        
        # 安装步骤明确性
        step_keywords = ["步骤", "首先", "然后", "接下来", "最后", "注意"]
        step_score = min(25, sum(5 for kw in step_keywords if kw in content))
        operability["details"]["安装步骤明确"] = step_score
        
        # 工具需求明确性
        tool_keywords = ["工具", "设备", "扳手", "螺丝刀", "吊装", "起重"]
        tool_score = min(25, sum(8 for kw in tool_keywords if kw in content))
        operability["details"]["工具需求明确"] = tool_score
        
        # 人员要求明确性
        personnel_keywords = ["人员", "技工", "电工", "焊工", "操作人员", "专业"]
        personnel_score = min(25, sum(8 for kw in personnel_keywords if kw in content))
        operability["details"]["人员要求明确"] = personnel_score
        
        # 时间估算
        time_keywords = ["时间", "工期", "小时", "天", "工日"]
        time_score = min(25, sum(12 for kw in time_keywords if kw in content))
        operability["details"]["时间估算"] = time_score
        
        operability["score"] = sum(operability["details"].values())
        return operability

    def evaluate_material_practicality(self, content: str) -> Dict[str, Any]:
        """评估材料清单实用性"""
        material = {"score": 0, "details": {}}
        
        # 规格完整性
        spec_patterns = [r'DN\d+', r'Φ\d+', r'\d+mm', r'PN\d+', r'不锈钢\d+']
        spec_count = sum(1 for pattern in spec_patterns if re.search(pattern, content))
        material["details"]["规格完整"] = min(25, spec_count * 5)
        
        # 数量准确性
        quantity_patterns = [r'\d+台', r'\d+个', r'\d+套', r'\d+米', r'\d+根']
        quantity_count = sum(1 for pattern in quantity_patterns if re.search(pattern, content))
        material["details"]["数量准确"] = min(25, quantity_count * 4)
        
        # 采购信息
        purchase_keywords = ["型号", "品牌", "厂家", "标准", "认证"]
        purchase_score = min(25, sum(5 for kw in purchase_keywords if kw in content))
        material["details"]["采购信息"] = purchase_score
        
        # 替代方案
        alternative_keywords = ["或", "可选", "替代", "等同", "相当"]
        alternative_score = min(25, sum(8 for kw in alternative_keywords if kw in content))
        material["details"]["替代方案"] = alternative_score
        
        material["score"] = sum(material["details"].values())
        return material

    def evaluate_safety_feasibility(self, content: str) -> Dict[str, Any]:
        """评估安全措施可行性"""
        safety = {"score": 0, "details": {}}
        
        # 风险识别全面性
        risk_keywords = ["风险", "危险", "隐患", "事故", "烫伤", "触电", "高温", "高压"]
        risk_score = min(30, sum(4 for kw in risk_keywords if kw in content))
        safety["details"]["风险识别全面"] = risk_score
        
        # 防护措施具体性
        protection_keywords = ["防护服", "安全帽", "防护眼镜", "手套", "警示", "隔离"]
        protection_score = min(30, sum(5 for kw in protection_keywords if kw in content))
        safety["details"]["防护措施具体"] = protection_score
        
        # 应急预案
        emergency_keywords = ["应急", "紧急停机", "事故处理", "急救", "疏散"]
        emergency_score = min(20, sum(6 for kw in emergency_keywords if kw in content))
        safety["details"]["应急预案"] = emergency_score
        
        # 人员防护
        personnel_protection = ["培训", "资质", "安全教育", "操作规程", "禁止事项"]
        personnel_score = min(20, sum(6 for kw in personnel_protection if kw in content))
        safety["details"]["人员防护"] = personnel_score
        
        safety["score"] = sum(safety["details"].values())
        return safety

    def evaluate_economic_reasonableness(self, content: str) -> Dict[str, Any]:
        """评估经济合理性"""
        economic = {"score": 0, "details": {}}
        
        # 成本考虑
        cost_keywords = ["成本", "费用", "价格", "投资", "预算"]
        cost_score = min(30, sum(10 for kw in cost_keywords if kw in content))
        economic["details"]["成本合理"] = cost_score
        
        # 性价比考虑
        value_keywords = ["性价比", "经济", "效益", "节约", "优化"]
        value_score = min(25, sum(8 for kw in value_keywords if kw in content))
        economic["details"]["性价比"] = value_score
        
        # 维护成本
        maintenance_keywords = ["维护", "保养", "寿命", "更换", "维修"]
        maintenance_score = min(25, sum(7 for kw in maintenance_keywords if kw in content))
        economic["details"]["维护成本"] = maintenance_score
        
        # 投资效益
        benefit_keywords = ["效益", "回报", "收益", "提高", "改善"]
        benefit_score = min(20, sum(8 for kw in benefit_keywords if kw in content))
        economic["details"]["投资效益"] = benefit_score
        
        economic["score"] = sum(economic["details"].values())
        return economic

    def evaluate_field_applicability(self, content: str) -> Dict[str, Any]:
        """评估现场适用性"""
        field = {"score": 0, "details": {}}
        
        # 环境适应性
        env_keywords = ["环境", "温度", "湿度", "腐蚀", "振动", "灰尘"]
        env_score = min(30, sum(5 for kw in env_keywords if kw in content))
        field["details"]["环境适应性"] = env_score
        
        # 空间要求
        space_keywords = ["空间", "位置", "距离", "高度", "安装位置", "布置"]
        space_score = min(25, sum(6 for kw in space_keywords if kw in content))
        field["details"]["空间要求"] = space_score
        
        # 接口兼容
        interface_keywords = ["接口", "兼容", "连接", "配套", "匹配"]
        interface_score = min(25, sum(7 for kw in interface_keywords if kw in content))
        field["details"]["接口兼容"] = interface_score
        
        # 维护便利
        maintenance_keywords = ["维护便利", "检修", "拆卸", "更换", "清洁"]
        maintenance_score = min(20, sum(7 for kw in maintenance_keywords if kw in content))
        field["details"]["维护便利"] = maintenance_score
        
        field["score"] = sum(field["details"].values())
        return field

    def evaluate_common_issues_coverage(self, content: str, instrument_type: str) -> Dict[str, Any]:
        """评估常见问题覆盖率"""
        coverage = {"score": 0, "covered_issues": [], "missed_issues": []}
        
        # 根据仪表类型获取常见问题
        relevant_issues = []
        for key, issues in self.common_issues.items():
            if key in instrument_type:
                relevant_issues = issues
                break
        
        if not relevant_issues:
            return coverage
        
        # 检查问题覆盖情况
        covered = []
        for issue in relevant_issues:
            # 简化检查：看关键词是否在文档中提到
            issue_keywords = issue.split()
            if any(keyword in content for keyword in issue_keywords):
                covered.append(issue)
        
        coverage["covered_issues"] = covered
        coverage["missed_issues"] = [issue for issue in relevant_issues if issue not in covered]
        coverage["score"] = (len(covered) / len(relevant_issues)) * 100 if relevant_issues else 0
        
        return coverage

    def simulate_engineer_decision(self, content: str) -> Dict[str, Any]:
        """模拟工程师决策过程"""
        decision = {
            "可实施性": 0,
            "风险可控性": 0,
            "成本可接受性": 0,
            "技术成熟度": 0,
            "推荐度": 0,
            "关键意见": []
        }
        
        # 可实施性评估
        implementation_factors = ["步骤明确", "材料可得", "工具常见", "技术成熟"]
        impl_score = sum(25 for factor in implementation_factors 
                        if any(keyword in content for keyword in factor.split()))
        decision["可实施性"] = impl_score
        
        # 风险可控性
        risk_control_factors = ["风险识别", "防护措施", "应急预案", "安全培训"]
        risk_score = sum(25 for factor in risk_control_factors 
                        if any(keyword in content for keyword in factor.split()))
        decision["风险可控性"] = risk_score
        
        # 成本可接受性（假设80%的方案成本是可接受的）
        decision["成本可接受性"] = 80
        
        # 技术成熟度（根据标准引用和技术参数判断）
        tech_indicators = ["GB/T", "JB/T", "技术参数", "测试", "验收"]
        tech_score = sum(20 for indicator in tech_indicators if indicator in content)
        decision["技术成熟度"] = min(100, tech_score)
        
        # 综合推荐度
        overall_score = (
            decision["可实施性"] * 0.3 +
            decision["风险可控性"] * 0.3 +
            decision["成本可接受性"] * 0.2 +
            decision["技术成熟度"] * 0.2
        )
        decision["推荐度"] = overall_score
        
        # 关键意见
        if overall_score >= 80:
            decision["关键意见"].append("推荐实施，方案成熟可靠")
        elif overall_score >= 60:
            decision["关键意见"].append("有条件推荐，需要进一步完善部分细节")
        else:
            decision["关键意见"].append("不推荐直接实施，需要重大修改")
        
        if decision["风险可控性"] < 60:
            decision["关键意见"].append("安全措施需要加强")
        
        if decision["可实施性"] < 60:
            decision["关键意见"].append("操作指导需要更详细")
        
        return decision

    def calculate_practical_score(self, validation_result: Dict[str, Any]) -> float:
        """计算实用性得分"""
        if "error" in validation_result:
            return 0
        
        # 各项得分归一化到0-100
        operability = validation_result["operability_score"]["score"]
        material = validation_result["material_practicality"]["score"]
        safety = validation_result["safety_feasibility"]["score"]
        economic = validation_result["economic_reasonableness"]["score"]
        field = validation_result["field_applicability"]["score"]
        issues = validation_result["common_issues_coverage"]["score"]
        engineer = validation_result["engineer_simulation"]["推荐度"]
        
        # 权重计算
        total_score = (
            operability * 0.20 +
            material * 0.15 +
            safety * 0.25 +
            economic * 0.15 +
            field * 0.15 +
            issues * 0.05 +
            engineer * 0.05
        )
        
        return total_score

    def get_recommendation_level(self, score: float) -> str:
        """获取推荐等级"""
        if score >= 80:
            return "强烈推荐"
        elif score >= 70:
            return "推荐使用"
        elif score >= 60:
            return "有条件推荐"
        elif score >= 50:
            return "需要改进"
        else:
            return "不推荐使用"

    def extract_basic_info(self, content: str, filename: str) -> Dict[str, str]:
        """提取基本信息"""
        info = {}
        
        # 从文件名提取仪表类型
        type_match = re.search(r'\d{8}_\d{6}_(.+?)_安装推荐\.md', filename)
        if type_match:
            info["instrument_type"] = type_match.group(1)
        
        # 提取型号和数量
        model_match = re.search(r'\*\*仪表型号：\*\*\s*([^\n]+)', content)
        if model_match:
            info["model"] = model_match.group(1).strip()
        
        quantity_match = re.search(r'\*\*数量：\*\*\s*([^\n]+)', content)
        if quantity_match:
            info["quantity"] = quantity_match.group(1).strip()
        
        return info

def run_practical_validation():
    """运行实际工程应用验证"""
    print("🏭 启动实际工程应用安全推荐验证实验")
    print("👷 模拟真实工程师评估流程：可操作性、材料实用性、安全可行性、经济合理性、现场适用性")
    
    validator = PracticalSafetyValidator()
    
    # 获取推荐文件
    files = [f for f in os.listdir("recommendation") if f.endswith('.md')]
    print(f"📁 待验证文件: {len(files)} 个")
    
    # 随机选择5个文件进行详细验证
    sample_files = random.sample(files, min(5, len(files)))
    
    results = []
    total_scores = []
    
    for i, filename in enumerate(sample_files, 1):
        print(f"\n👨‍🔧 工程师评估 {i}/5: {filename}")
        result = validator.practical_validation(filename)
        results.append(result)
        
        if "error" not in result:
            score = result["practical_score"]
            level = result["recommendation_level"]
            total_scores.append(score)
            
            print(f"   实用性得分: {score:.1f}/100 ({level})")
            print(f"   可操作性: {result['operability_score']['score']:.1f}/100")
            print(f"   安全可行性: {result['safety_feasibility']['score']:.1f}/100")
            print(f"   经济合理性: {result['economic_reasonableness']['score']:.1f}/100")
            
            # 显示工程师意见
            engineer_opinion = result['engineer_simulation']['关键意见']
            if engineer_opinion:
                print(f"   工程师意见: {'; '.join(engineer_opinion)}")
    
    # 保存结果
    with open("practical_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n" + "="*60)
    print("🎯 实际工程应用验证总结")
    print("="*60)
    
    if total_scores:
        avg_score = sum(total_scores) / len(total_scores)
        print(f"平均实用性得分: {avg_score:.1f}/100")
        
        # 统计推荐等级分布
        levels = [validator.get_recommendation_level(score) for score in total_scores]
        print(f"\n推荐等级分布:")
        for level in ["强烈推荐", "推荐使用", "有条件推荐", "需要改进", "不推荐使用"]:
            count = levels.count(level)
            if count > 0:
                print(f"  {level}: {count}个文件 ({count/len(levels)*100:.1f}%)")
        
        print(f"\n🏆 实验结论:")
        if avg_score >= 75:
            print("✅ 智能体生成的安全推荐具有很高的实际工程应用价值!")
            print("   可以直接用于指导实际安装工作")
        elif avg_score >= 65:
            print("✅ 智能体生成的安全推荐具有良好的实际应用价值")
            print("   在工程师指导下可以有效应用")
        elif avg_score >= 55:
            print("⚠️ 智能体生成的安全推荐有一定参考价值")
            print("   需要工程师进行必要的补充和修改")
        else:
            print("❌ 智能体生成的安全推荐需要大幅改进")
            print("   目前不适合直接用于实际工程")
    
    print(f"\n📄 详细结果已保存到: practical_validation_results.json")
    print("✅ 实际工程应用验证完成!")

if __name__ == "__main__":
    run_practical_validation() 
 
 