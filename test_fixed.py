#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
针对华辰锅炉汽水工作表的专门测试
"""

import pandas as pd
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

def test_specific_sheet():
    """直接测试华辰锅炉汽水工作表"""
    print('=== 直接测试华辰锅炉汽水工作表 ===')
    
    # 直接读取包含仪表数据的工作表
    df = pd.read_excel('data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx', 
                       sheet_name='华辰锅炉汽水', header=None)
    
    print(f'原始数据: {len(df)} 行, {len(df.columns)} 列')
    
    # 显示前10行，找到表头和分类信息
    print('\n前10行内容:')
    for i in range(min(10, len(df))):
        row_content = ' | '.join([str(cell) if pd.notna(cell) else '' for cell in df.iloc[i]])
        print(f'第{i+1}行: {row_content[:120]}...')
    
    # 测试数据清洗和分类
    print('\n=== 测试数据清洗和表格分类 ===')
    try:
        from tools.parse_instrument_table import extract_and_parse_instrument_table
        
        parsed_df = extract_and_parse_instrument_table(df)
        print(f'✅ 清洗后数据行数: {len(parsed_df)}')
        
        if len(parsed_df) > 0:
            print('清洗后的列:', list(parsed_df.columns))
            
            if '仪表类型' in parsed_df.columns:
                print('\n✅ 发现仪表类型列！')
                type_counts = parsed_df['仪表类型'].value_counts()
                print('分类统计:')
                for type_name, count in type_counts.items():
                    print(f'  - {type_name}: {count} 个')
                
                print('\n前10行清洗结果:')
                display_cols = ['位号', '型号', '仪表类型']
                available_cols = [col for col in display_cols if col in parsed_df.columns]
                
                if available_cols:
                    display_df = parsed_df[available_cols].head(10)
                    for i, row in display_df.iterrows():
                        row_str = ' | '.join([str(row[col]) for col in available_cols])
                        print(f'  {row_str}')
                else:
                    print('  无法显示：缺少位号/型号列')
                    print('  实际列:', list(parsed_df.columns))
                
                return parsed_df
            else:
                print('❌ 缺少仪表类型列')
                print('实际列:', list(parsed_df.columns))
                
                # 显示前几行数据供调试
                print('\n前5行原始清洗结果:')
                for i, row in parsed_df.head(5).iterrows():
                    print(f'  第{i+1}行: {dict(row)}')
        else:
            print('❌ 清洗后数据为空')
            
    except Exception as e:
        print(f'❌ 数据清洗失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

def test_classification_extraction():
    """测试分类信息提取"""
    print('\n=== 测试分类信息提取 ===')
    try:
        from tools.classify_instrument_type import extract_categories_from_table
        
        # 读取原始数据
        df = pd.read_excel('data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx', 
                           sheet_name='华辰锅炉汽水', header=None)
        
        # 转换为列表格式
        table_data = []
        for i, row in df.iterrows():
            table_data.append([str(cell) if pd.notna(cell) else '' for cell in row])
        
        # 提取分类信息
        categories = extract_categories_from_table(table_data)
        
        print(f'识别到 {len(categories)} 个分类:')
        for category_name, row_indices in categories.items():
            print(f'  - {category_name}: 行号 {row_indices}')
        
        return categories
        
    except Exception as e:
        print(f'❌ 分类提取失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return {}

def main():
    """主测试函数"""
    print("开始测试华辰锅炉汽水工作表...")
    
    # 测试分类信息提取
    categories = test_classification_extraction()
    
    # 测试完整数据清洗
    parsed_df = test_specific_sheet()
    
    print('\n=== 测试总结 ===')
    if categories:
        print(f'✅ 成功识别 {len(categories)} 个分类')
    else:
        print('❌ 分类识别失败')
        
    if parsed_df is not None and len(parsed_df) > 0:
        print(f'✅ 成功清洗 {len(parsed_df)} 行数据')
    else:
        print('❌ 数据清洗失败')

if __name__ == "__main__":
    main() 