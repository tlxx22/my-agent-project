"""
批量评估测试脚本 - 对15篇安装推荐进行综合评估
"""

import re
import os
from comprehensive_evaluation_metrics import integrate_comprehensive_metrics
from datetime import datetime
import json

def read_test_file_with_encoding(file_path):
    """尝试多种编码方式读取文件"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'cp936', 'unicode_escape']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✅ 成功使用 {encoding} 编码读取文件")
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"❌ 使用 {encoding} 编码时出错: {e}")
            continue
    
    # 如果所有编码都失败，尝试忽略错误
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        print("⚠️ 使用 utf-8 编码并忽略错误读取文件")
        return content
    except Exception as e:
        print(f"❌ 完全无法读取文件: {e}")
        return None

def parse_documents_from_content(content):
    """从文件内容中解析出不同质量等级的文档"""
    if not content:
        return []
    
    # 定义质量标识符的多种可能格式
    quality_patterns = [
        r'【高质量】',
        r'【中质量】', 
        r'【低质量】',
        r'\[高质量\]',
        r'\[中质量\]',
        r'\[低质量\]',
        r'高质量',
        r'中质量', 
        r'低质量'
    ]
    
    documents = []
    
    # 尝试按段落分割
    paragraphs = re.split(r'\n\s*\n', content)
    
    current_doc = ""
    current_quality = None
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # 检查是否包含质量标识
        quality_found = None
        for pattern in quality_patterns:
            if re.search(pattern, paragraph):
                if '高质量' in paragraph or '高质量' in pattern:
                    quality_found = '高质量'
                elif '中质量' in paragraph or '中质量' in pattern:
                    quality_found = '中质量'
                elif '低质量' in paragraph or '低质量' in pattern:
                    quality_found = '低质量'
                break
        
        if quality_found:
            # 保存之前的文档
            if current_doc and current_quality:
                documents.append({
                    'quality': current_quality,
                    'content': current_doc.strip()
                })
            
            # 开始新文档
            current_quality = quality_found
            current_doc = paragraph
        else:
            # 继续当前文档
            if current_doc:
                current_doc += "\n\n" + paragraph
            else:
                current_doc = paragraph
    
    # 保存最后一个文档
    if current_doc and current_quality:
        documents.append({
            'quality': current_quality,
            'content': current_doc.strip()
        })
    
    return documents

def create_sample_documents():
    """创建示例文档用于测试"""
    sample_docs = []
    
    # 高质量文档示例
    for i in range(1, 6):
        high_quality_doc = f"""
【高质量】温度仪表安装推荐方案 {i}

## 安装位置选择
温度仪表应安装在能够准确反映工艺温度的代表性位置。选择安装位置时应考虑以下因素：
- 测量准确性：选择能够真实反映被测介质温度的典型位置，避免靠近加热器、冷却器等热源
- 插入深度：确保传感器有足够的插入深度，一般不小于管径的1/3，避免管壁导热影响
- 安装高度：距离地面1.2-1.8米，便于观察和维护
- 环境条件：避开强腐蚀、强振动区域

## 安装方式与步骤
1. 前期准备：确认仪表型号、量程、精度等级，准备安装工具和材料
2. 开孔安装：在预定位置开孔，安装热电偶套管或直接安装传感器
3. 密封处理：使用合适密封材料，确保无泄漏
4. 电气连接：按照接线图正确连接信号线和电源线
5. 调试验收：进行零点和量程校准，验证测量精度

## 材料清单
- 温度传感器：Pt100，精度等级A级，-50~200°C
- 保护套管：不锈钢316L，长度200mm
- 密封件：PTFE密封圈，耐温250°C
- 信号电缆：4芯屏蔽电缆，2.5mm²
- 安装附件：法兰、螺栓、垫片等

## 安全要求
- 施工安全：断电施工，使用绝缘工具
- 防爆要求：选用防爆型仪表，符合现场防爆等级
- 人员防护：佩戴安全帽、绝缘手套
- 验收标准：精度误差≤±0.5%，绝缘电阻≥20MΩ
        """
        sample_docs.append({
            'quality': '高质量',
            'content': high_quality_doc.strip()
        })
    
    # 中质量文档示例
    for i in range(1, 6):
        medium_quality_doc = f"""
【中质量】压力仪表安装指南 {i}

## 安装位置
压力仪表应安装在能够准确测量工艺压力的位置：
- 选择压力稳定的直管段
- 距离弯头5倍管径以上
- 便于观察和维护的高度
- 避开振动和高温区域

## 安装步骤
1. 确认仪表规格和取压点位置
2. 安装取压阀门和压力表
3. 进行密封和接线
4. 校验和调试

## 所需材料
- 压力表：量程0-1.6MPa，精度1.6级
- 取压阀：球阀DN15
- 密封件：石墨垫片
- 连接管：不锈钢管φ14×2

## 安全注意事项
- 安装前确认系统无压力
- 使用合适的密封材料
- 定期检查和校验
        """
        sample_docs.append({
            'quality': '中质量', 
            'content': medium_quality_doc.strip()
        })
    
    # 低质量文档示例
    for i in range(1, 6):
        low_quality_doc = f"""
【低质量】仪表安装说明 {i}

安装位置：装在管道上
安装方法：用螺栓固定
材料：仪表、螺栓、垫片
注意安全。
        """
        sample_docs.append({
            'quality': '低质量',
            'content': low_quality_doc.strip()
        })
    
    return sample_docs

def evaluate_documents(documents):
    """对文档列表进行批量评估"""
    
    print("🚀 开始批量评估测试")
    print("=" * 80)
    
    # 统计结果
    results = []
    quality_stats = {'高质量': [], '中质量': [], '低质量': []}
    
    for i, doc in enumerate(documents, 1):
        print(f"\n📋 评估文档 {i}: {doc['quality']}")
        print("-" * 60)
        
        try:
            # 进行综合评估
            result = integrate_comprehensive_metrics(doc['content'])
            
            # 提取关键指标
            comprehensive_score = result['comprehensive_score']
            comprehensive_level = result['comprehensive_level']
            coverage_score = result['content_coverage']['overall_coverage_score']
            usability_score = result['usability_operability']['usability_score']
            quality_score = result['quality_review']['aggregated'].get('overall_quality_score', 0)
            
            # 保存结果
            doc_result = {
                'doc_index': i,
                'expected_quality': doc['quality'],
                'comprehensive_score': comprehensive_score,
                'comprehensive_level': comprehensive_level,
                'coverage_score': coverage_score,
                'usability_score': usability_score,
                'quality_score': quality_score,
                'content_preview': doc['content'][:100] + "..."
            }
            
            results.append(doc_result)
            quality_stats[doc['quality']].append(doc_result)
            
            # 显示评估结果
            print(f"🎯 综合得分: {comprehensive_score:.1f}/100 ({comprehensive_level})")
            print(f"📊 内容覆盖: {coverage_score:.1f}/100 (权重20%)")
            print(f"🔧 可用性: {usability_score:.1f}/100 (权重45%)")
            print(f"👨‍🔬 质量评审: {quality_score:.1f}/100 (权重35%)")
            
            # 权重贡献分析
            coverage_contrib = coverage_score * 0.20
            usability_contrib = usability_score * 0.45
            quality_contrib = quality_score * 0.35
            
            print(f"💡 权重贡献:")
            print(f"  📊 内容覆盖: {coverage_contrib:.1f}分")
            print(f"  🔧 可用性: {usability_contrib:.1f}分")
            print(f"  👨‍🔬 质量评审: {quality_contrib:.1f}分")
            
        except Exception as e:
            print(f"❌ 评估文档 {i} 时出错: {str(e)}")
            continue
    
    return results, quality_stats

def calculate_quality_level_stats(quality_stats):
    """计算各质量层级的统计指标"""
    
    print(f"\n📊 各质量层级统计分析")
    print("=" * 80)
    
    for quality_level, docs in quality_stats.items():
        if not docs:
            print(f"\n⚠️ {quality_level}文档：无有效数据")
            continue
            
        # 计算各指标的平均值
        avg_comprehensive = sum(doc['comprehensive_score'] for doc in docs) / len(docs)
        avg_coverage = sum(doc['coverage_score'] for doc in docs) / len(docs)
        avg_usability = sum(doc['usability_score'] for doc in docs) / len(docs)
        avg_quality = sum(doc['quality_score'] for doc in docs) / len(docs)
        
        # 加权平均综合得分验证
        weighted_avg = avg_coverage * 0.20 + avg_usability * 0.45 + avg_quality * 0.35
        
        print(f"\n📋 {quality_level}文档 (共{len(docs)}篇)")
        print("-" * 40)
        print(f"🎯 平均综合得分: {avg_comprehensive:.1f}/100")
        print(f"📊 平均内容覆盖: {avg_coverage:.1f}/100")
        print(f"🔧 平均可用性: {avg_usability:.1f}/100")
        print(f"👨‍🔬 平均质量评审: {avg_quality:.1f}/100")
        print(f"✅ 加权平均验证: {weighted_avg:.1f}/100")
        
        # 显示得分分布
        scores = [doc['comprehensive_score'] for doc in docs]
        print(f"📈 得分分布: 最高{max(scores):.1f}, 最低{min(scores):.1f}, 标准差{(sum((s-avg_comprehensive)**2 for s in scores)/len(scores))**0.5:.1f}")

def main():
    """主函数"""
    
    print("🔍 批量评估测试脚本")
    print("测试目标：evaluation recommendation_test/test.txt中的15篇安装推荐")
    print("评估指标：内容覆盖(20%) + 可用性(45%) + 质量评审(35%)")
    print("=" * 80)
    
    # 检查文件是否存在
    test_file_path = "recommendation_test/test.txt"
    
    if os.path.exists(test_file_path):
        print(f"📁 找到测试文件: {test_file_path}")
        
        # 尝试读取文件
        content = read_test_file_with_encoding(test_file_path)
        
        if content:
            # 解析文档
            documents = parse_documents_from_content(content)
            print(f"📄 解析出 {len(documents)} 篇文档")
            
            if len(documents) < 10:  # 如果解析出的文档太少，使用示例文档
                print("⚠️ 解析出的文档数量不足，使用示例文档进行测试")
                documents = create_sample_documents()
        else:
            print("❌ 无法读取测试文件，使用示例文档")
            documents = create_sample_documents()
    else:
        print(f"⚠️ 测试文件 {test_file_path} 不存在，使用示例文档")
        documents = create_sample_documents()
    
    print(f"📊 总共评估 {len(documents)} 篇文档")
    
    # 显示文档分布
    quality_count = {}
    for doc in documents:
        quality = doc['quality']
        quality_count[quality] = quality_count.get(quality, 0) + 1
    
    print("📈 文档质量分布:")
    for quality, count in quality_count.items():
        print(f"  {quality}: {count}篇")
    
    # 执行批量评估
    results, quality_stats = evaluate_documents(documents)
    
    # 计算质量层级统计
    calculate_quality_level_stats(quality_stats)
    
    # 保存结果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"batch_evaluation_results_{timestamp}.json"
    
    output_data = {
        "evaluation_time": timestamp,
        "total_documents": len(documents),
        "quality_distribution": quality_count,
        "evaluation_results": results,
        "quality_level_stats": {
            quality: {
                "count": len(docs),
                "avg_comprehensive": sum(doc['comprehensive_score'] for doc in docs) / len(docs) if docs else 0,
                "avg_coverage": sum(doc['coverage_score'] for doc in docs) / len(docs) if docs else 0,
                "avg_usability": sum(doc['usability_score'] for doc in docs) / len(docs) if docs else 0,
                "avg_quality": sum(doc['quality_score'] for doc in docs) / len(docs) if docs else 0
            }
            for quality, docs in quality_stats.items()
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 评估结果已保存到: {output_file}")
    print("\n🎉 批量评估测试完成!")

if __name__ == "__main__":
    main() 