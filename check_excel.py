#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查Excel文件结构
"""

import pandas as pd

def check_excel_structure():
    """检查Excel文件的工作表结构"""
    
    # 读取Excel文件的所有工作表
    xl_file = pd.ExcelFile('data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx')

    print('Excel文件中的工作表:')
    for i, sheet_name in enumerate(xl_file.sheet_names):
        print(f'{i+1}. {sheet_name}')

    # 检查每个工作表的内容
    for sheet_name in xl_file.sheet_names:
        print(f'\n--- 检查工作表 "{sheet_name}" ---')
        df = pd.read_excel(xl_file, sheet_name=sheet_name, header=None)
        print(f'行数: {len(df)}')
        print(f'列数: {len(df.columns)}')

        # 查找包含"仪表"、"位号"、"型号"等关键字的行
        keywords = ['仪表', '位号', '型号', '数量', '规格', '温度', '压力', '流量', '液位']
        found_keywords = []
        
        for i in range(min(20, len(df))):  # 只检查前20行
            row_content = ' '.join([str(cell) for cell in df.iloc[i] if pd.notna(cell)])
            row_keywords = [kw for kw in keywords if kw in row_content]
            if row_keywords:
                found_keywords.extend(row_keywords)
                print(f'第{i+1}行发现关键字 {row_keywords}: {row_content[:100]}...')

        if found_keywords:
            print(f'此工作表可能包含仪表数据，发现关键字: {set(found_keywords)}')
        else:
            print('此工作表可能不包含仪表数据')
            
        # 显示前几行内容
        print('\n前5行内容:')
        for i in range(min(5, len(df))):
            row_content = ' | '.join([str(cell) if pd.notna(cell) else '' for cell in df.iloc[i]])
            print(f'第{i+1}行: {row_content[:150]}...')

if __name__ == "__main__":
    check_excel_structure() 