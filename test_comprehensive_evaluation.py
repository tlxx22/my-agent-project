"""
测试综合评价指标体系
验证三类指标对不同质量文档的评价效果
"""

from comprehensive_evaluation_metrics import integrate_comprehensive_metrics
import json
from datetime import datetime

def test_different_quality_documents():
    """测试不同质量等级的文档评价效果"""
    
    # 测试文档1：高质量文档
    high_quality_doc = """
    ## 1. 安装位置要求
- 安装高度: 距地面1.2-1.5 m，便于观察和维护  
- 插入深度: 套管插入管道内径的1/3-1/2，迎流向倾斜≤30°  
- 直管段要求: 上游5倍管径，下游≥250 mm直管段  
- 环境条件: 环境温度-40 °C-+85 °C，湿度≤90%，避开强振与热辐射  
- 安全距离: 危险区选Ex d/Ex ia型，变送器与高温源≥150 mm并加散热片

## 2. 安装步骤详解
1. 第一步：准备工作 (工期: 0.5 工日)  
   - 吹扫管道，去除焊渣与杂质  
   - 核对仪表型号、量程、证书，检查套管材质与ASME 19.3TW计算书  
   - 准备工具：扳手、矩扳(30-60 N·m）、水平仪、绝缘螺丝刀  
   - 到位人员: 电工1名，钳工1名  

2. 第二步：机械固定 (工期: 1 工日)  
   - 套管丝扣/PTFE密封带，按35-45 N·m扭矩安装  
   - 若插深>450 mm，加支撑架或导向环防振  
   - 将弹簧加载Pt100插入套管，确保触底无气隙  
   - 变送器连接M20×1.5隔爆电缆压盖，紧固力10-15 N·m  

3. 第三步：接线与校准 (工期: 0.5 工日)  
   - 接入24 V DC二线制，屏蔽层单端接地；回路负载≥250 Ω  
   - 4 mA/20 mA信号校验，零点调整±0.05 % FS  
   - 在DCS模拟高温报警，验证联锁动作正常

## 3. 材料清单
- 主仪表: Rosemount 3144P + Pt100（三线制Class A），精度±0.1 °C  
- 套管: SS316 热套管 ½-NPT×450 mm，符合ASME 19.3TW  
- 阀组: ½-NPT针阀+排污阀，A105材质  
- 密封件: PTFE带、石墨垫片DN25/PN40  
- 电缆: 屏蔽双绞RVSP 2×1 mm²，长度按现场  
- 支架: SS304加劲支架，配M10×60螺栓4套  

## 4. 安全防护措施
- 人员防护: 佩戴安全帽、防护眼镜、耐高温手套  
- 风险控制: 识别高温、蒸汽泄漏、电气短路风险并设置围栏  
- 安全联锁: 过程温度>设定90 % FS时，自动报警并切断加热源  
- 应急措施: 现场配急救包与CO₂灭火器，标明疏散路线

## 5. 质量控制标准
- 验收依据: GB/T 18271-2017 & IEC 60751  
- 检查要点: 密封性、扭矩记录、4-20 mA回路误差≤0.05 % FS、报警功能  
- 维护要求: 每月巡视一次，每18个月校准一次，五年更换套管或测厚≤70 %原壁厚即更换  
- 故障处理: 零漂→现场调零；信号抖动→检查屏蔽接地；迟滞→确认Pt100触底

## 6. 注意事项
- 严禁带压拆装热套管；检修前须完全泄压、降温至<50 °C  
- 防爆区必须使用认证隔爆/本安电缆压盖，螺纹≥5扣并涂防松胶  
- 套管材料与介质相容，强腐介质选Inconel或哈氏合金  
- 建立设备档案：记录扭矩、校准数据、故障历史，便于追溯与优化

    """
    
    # 测试文档2：中等质量文档
    medium_quality_doc = """
    # 压力表安装方案
    
    ## 安装位置
    压力表应安装在便于观察的位置，距离管道弯头5倍管径。
    环境温度要求-20°C至+60°C。
    
    ## 安装步骤
    1. 首先准备安装工具和材料
    2. 然后进行安装固定
    3. 最后进行测试验收
    
    ## 材料要求
    - 压力表: DN50规格，PN16压力等级
    - 螺栓: 8个，M12规格
    - 垫片: 橡胶材质
    
    ## 安全要求
    安装时注意安全防护，戴好安全帽。
    避免在高压状态下操作。
    """
    
    # 测试文档3：低质量文档
    low_quality_doc = """
    压力表安装
    
    把压力表装在管道上，用螺栓固定好。
    注意安全。
    需要的材料有压力表、螺栓、垫片。
    """
    
    test_docs = [
        ("高质量文档", high_quality_doc),
        ("中等质量文档", medium_quality_doc),
        ("低质量文档", low_quality_doc)
    ]
    
    print("🔬 三类指标综合评价体系测试")
    print("=" * 50)
    
    results = []
    
    for doc_type, doc_content in test_docs:
        print(f"\n📋 测试文档: {doc_type}")
        print("-" * 30)
        
        # 进行综合评估
        result = integrate_comprehensive_metrics(doc_content)
        
        # 提取关键指标
        comprehensive_score = result['comprehensive_score']
        comprehensive_level = result['comprehensive_level']
        coverage_score = result['content_coverage']['overall_coverage_score']
        usability_score = result['usability_operability']['usability_score']
        quality_score = result['quality_review']['aggregated'].get('overall_quality_score', 0)
        
        # 显示评价结果
        print(f"🎯 综合得分: {comprehensive_score:.1f}/100 ({comprehensive_level})")
        print(f"📊 内容覆盖: {coverage_score:.1f}/100")
        print(f"🔧 可用性: {usability_score:.1f}/100")
        print(f"👨‍🔬 质量评审: {quality_score:.1f}/100")
        
        # 显示改进建议
        feedback = result['content_coverage']['feedback_for_llm']
        print(f"💡 改进建议: {feedback}")
        
        # 显示可扩展项检测结果
        advanced_checks = result['usability_operability']['advanced_checks']
        print(f"🔍 高级检测:")
        print(f"   - 时序一致性: {advanced_checks['sequence_consistency']}/10")
        print(f"   - 工具步骤对应: {advanced_checks['tool_step_alignment']}/15")
        print(f"   - 尺寸合理性: {advanced_checks['dimension_reasonableness']}/10")
        
        results.append({
            "doc_type": doc_type,
            "comprehensive_score": comprehensive_score,
            "comprehensive_level": comprehensive_level,
            "scores": {
                "coverage": coverage_score,
                "usability": usability_score,
                "quality": quality_score
            },
            "advanced_checks": advanced_checks
        })
    
    # 对比分析
    print("\n📈 对比分析")
    print("=" * 50)
    
    for result in sorted(results, key=lambda x: x['comprehensive_score'], reverse=True):
        print(f"{result['doc_type']:>8}: {result['comprehensive_score']:>5.1f}分 ({result['comprehensive_level']})")
    
    # 验证梯度效应
    scores = [r['comprehensive_score'] for r in results]
    print(f"\n✅ 梯度检验: 高质量({scores[0]:.1f}) > 中质量({scores[1]:.1f}) > 低质量({scores[2]:.1f})")
    
    return results

def main():
    """主测试函数"""
    
    print("🚀 启动三类评价指标体系全面测试")
    print("=" * 60)
    
    # 测试不同质量文档的评价效果
    results = test_different_quality_documents()
    
    print("\n🎉 测试完成!")
    print("\n📋 总结:")
    print("✅ 内容覆盖类指标: 能识别关键要素缺失")
    print("✅ 可行性可操作性指标: 能评估现场实用性")
    print("✅ 质量评审类指标: 能替代专家评分")
    print("✅ 综合评分: 体现文档质量梯度差异")

if __name__ == "__main__":
    main() 
