#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复后的完整工作流程
"""

from tools.extract_excel_tables import extract_excel_tables
from tools.parse_instrument_table import extract_and_parse_instrument_table
from tools.langgraph_tools import classify_instrument_types
import pandas as pd
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

def test_complete_workflow():
    """测试完整工作流程"""
    
    # 1. 测试表格提取
    print('=== 步骤1: 表格提取 ===')
    try:
        tables = extract_excel_tables('data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx')
        print(f'✅ 提取到 {len(tables)} 个表格')
        
        if not tables:
            print('❌ 没有提取到表格')
            return
        
        table = tables[0]
        print(f'表格名称: {table["name"]}')
        print(f'数据行数: {len(table["data"])}')
        print('前3行数据:')
        print(table['data'].head(3))
        
    except Exception as e:
        print(f'❌ 表格提取失败: {str(e)}')
        return
    
    # 2. 测试数据清洗和表格分类
    print('\n=== 步骤2: 数据清洗和表格分类 ===')
    try:
        parsed_df = extract_and_parse_instrument_table(table['data'])
        print(f'✅ 清洗后数据行数: {len(parsed_df)}')
        print('清洗后的列:', list(parsed_df.columns))
        
        if '仪表类型' in parsed_df.columns:
            print('\n✅ 发现仪表类型列，表格分类功能正常')
            type_counts = parsed_df['仪表类型'].value_counts()
            print('分类统计:')
            for type_name, count in type_counts.items():
                print(f'  - {type_name}: {count} 个')
            
            print('\n前10行清洗结果:')
            display_df = parsed_df[['位号', '型号', '仪表类型']].head(10)
            for i, row in display_df.iterrows():
                print(f'  {row["位号"]} | {row["型号"]} | {row["仪表类型"]}')
        else:
            print('❌ 缺少仪表类型列，表格分类失败')
            return
            
    except Exception as e:
        print(f'❌ 数据清洗失败: {str(e)}')
        return
    
    # 3. 测试LLM补充分类
    print('\n=== 步骤3: LLM补充分类测试 ===')
    try:
        # 准备测试数据
        parsed_data = {
            "columns": list(parsed_df.columns),
            "data": parsed_df.to_dict('records'),
            "row_count": len(parsed_df)
        }
        
        result = classify_instrument_types(parsed_data, use_llm=False)  # 先不使用LLM测试
        
        if result["success"]:
            print('✅ LLM补充分类功能正常')
            print(f'处理结果: {result["message"]}')
            
            # 检查分类结果
            classified_df = pd.DataFrame(result["classified_data"]["data"])
            final_type_counts = classified_df['仪表类型'].value_counts()
            print('\n最终分类统计:')
            for type_name, count in final_type_counts.items():
                print(f'  - {type_name}: {count} 个')
        else:
            print(f'❌ LLM补充分类失败: {result["message"]}')
            
    except Exception as e:
        print(f'❌ LLM补充分类测试失败: {str(e)}')
    
    print('\n=== 测试完成 ===')

if __name__ == "__main__":
    test_complete_workflow() 