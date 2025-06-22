"""
测试RAG功能是否正常工作
"""
import logging
from tools.match_standard_clause import StandardClauseRetriever

logging.basicConfig(level=logging.INFO)

def test_rag_functionality():
    """测试RAG检索功能"""
    
    print("开始测试RAG功能...")
    
    # 初始化检索器
    retriever = StandardClauseRetriever()
    
    # 检查索引是否存在
    if not retriever.load_index():
        print("错误: 无法加载向量索引，请先运行: python tools/build_index.py --mode rebuild")
        return False
    
    print(f"成功: 加载了包含 {len(retriever.indexer.documents)} 个文档块的索引")
    
    # 测试不同仪表类型的检索
    test_instruments = [
        "热电偶",
        "压力表", 
        "流量计",
        "液位计",
        "温度变送器"
    ]
    
    for instrument in test_instruments:
        print(f"\n{'='*50}")
        print(f"测试检索: {instrument}")
        print('='*50)
        
        # 检索安装规范
        results = retriever.search_by_instrument_type(instrument, top_k=2)
        
        if results:
            print(f"找到 {len(results)} 条相关规范:")
            for i, result in enumerate(results, 1):
                print(f"{i}. 相似度: {result['score']:.3f}")
                print(f"   来源: {result['metadata']['source_file']}")
                print(f"   内容: {result['content'][:150]}...")
        else:
            print(f"未找到 {instrument} 的相关规范")
    
    # 测试综合检索
    print(f"\n{'='*50}")
    print("测试综合检索功能")
    print('='*50)
    
    comprehensive = retriever.get_comprehensive_standards("热电偶")
    print(f"热电偶综合规范信息:")
    print(f"- 安装方法: {len(comprehensive['installation_methods'])} 条")
    print(f"- 材料要求: {len(comprehensive['material_requirements'])} 条")
    print(f"- 安全要求: {len(comprehensive['safety_requirements'])} 条")
    print(f"- 维护要求: {len(comprehensive['maintenance_requirements'])} 条")
    
    print(f"\n完成: RAG功能测试完成")
    return True

if __name__ == "__main__":
    test_rag_functionality() 