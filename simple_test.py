#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化测试脚本 - 直接测试核心功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

def test_table_extraction():
    """测试表格提取"""
    print('=== 测试 1: 表格提取 ===')
    try:
        from tools.extract_excel_tables import extract_excel_tables
        
        tables = extract_excel_tables('data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx')
        print(f'✅ 提取到 {len(tables)} 个表格')
        
        if tables:
            table = tables[0]
            print(f'表格名称: {table["name"]}')
            print(f'数据行数: {len(table["data"])}')
            return table
        else:
            print('❌ 没有提取到表格')
            return None
            
    except Exception as e:
        print(f'❌ 表格提取失败: {str(e)}')
        return None

def test_table_parsing(table):
    """测试数据清洗和分类"""
    print('\n=== 测试 2: 数据清洗和表格分类 ===')
    try:
        from tools.parse_instrument_table import extract_and_parse_instrument_table
        
        parsed_df = extract_and_parse_instrument_table(table['data'])
        print(f'✅ 清洗后数据行数: {len(parsed_df)}')
        print('清洗后的列:', list(parsed_df.columns))
        
        if '仪表类型' in parsed_df.columns:
            print('\n✅ 发现仪表类型列，表格分类功能正常')
            type_counts = parsed_df['仪表类型'].value_counts()
            print('分类统计:')
            for type_name, count in type_counts.items():
                print(f'  - {type_name}: {count} 个')
            
            print('\n前5行清洗结果:')
            display_df = parsed_df[['位号', '型号', '仪表类型']].head(5)
            for i, row in display_df.iterrows():
                print(f'  {row["位号"]} | {row["型号"]} | {row["仪表类型"]}')
                
            return parsed_df
        else:
            print('❌ 缺少仪表类型列，表格分类失败')
            return None
            
    except Exception as e:
        print(f'❌ 数据清洗失败: {str(e)}')
        return None

def test_classification_logic(parsed_df):
    """测试分类逻辑"""
    print('\n=== 测试 3: 分类逻辑验证 ===')
    try:
        from tools.classify_instrument_type import classify_instrument_type
        
        # 测试几个示例
        test_cases = [
            ("WZP-630", "热电阻,分度号Pt100", "温度测量"),
            ("EJA430A", "压力变送器; 量程:0~10MPa", "压力测量"),
            ("未知型号", "未知规格", "测试")
        ]
        
        print("测试个别分类:")
        for model, spec, context in test_cases:
            result = classify_instrument_type(
                model=model,
                spec=spec,
                context=context,
                row_index=-1,
                table_categories=None,
                use_llm=False  # 不使用LLM
            )
            print(f"  {model} -> {result}")
            
        # 检查已分类的数据
        classified_count = len(parsed_df[parsed_df['仪表类型'] != "未分类"])
        unclassified_count = len(parsed_df[parsed_df['仪表类型'] == "未分类"])
        
        print(f'\n✅ 分类统计: 已分类 {classified_count} 个, 未分类 {unclassified_count} 个')
        
        if classified_count > 0:
            print("✅ 表格分类功能正常工作")
        else:
            print("⚠️ 没有识别到表格分类")
            
        return True
        
    except Exception as e:
        print(f'❌ 分类逻辑测试失败: {str(e)}')
        return False

def main():
    """主测试函数"""
    print("开始简化测试流程...")
    
    # 测试1: 表格提取
    table = test_table_extraction()
    if not table:
        return
    
    # 测试2: 数据清洗和分类
    parsed_df = test_table_parsing(table)
    if parsed_df is None:
        return
    
    # 测试3: 分类逻辑
    test_classification_logic(parsed_df)
    
    print('\n=== 所有测试完成 ===')

if __name__ == "__main__":
    main() 