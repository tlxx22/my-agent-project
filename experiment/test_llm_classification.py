"""
LLM分类效果测试脚本

测试LLM对仪表类型分类的准确性：
1. 从测试表格中提取原始分类信息
2. 移除分类信息，让LLM重新分类
3. 对比结果，计算准确率和分析偏差

修正版：对相同型号的仪表去重，避免重复测试
"""
import pandas as pd
import os
import logging
from typing import List, Dict, Tuple, Any
from collections import defaultdict, Counter
import json
import datetime

from tools.extract_excel_tables import extract_excel_tables
from tools.classify_instrument_type import extract_categories_from_table, classify_by_llm
from tools.parse_instrument_table import extract_and_parse_instrument_table

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMClassificationTester:
    """LLM分类效果测试器"""
    
    def __init__(self):
        self.test_files = [
            "data/uploads/k0104-01 （锅炉汽水系统） 1.xlsx",
            "data/uploads/k0104-02 锅炉燃烧系统仪表清单.xls", 
            "data/uploads/k0104-03 除氧供热系统仪表清单.xls",
            "data/uploads/k0104-04 锅炉燃气点火系统仪表清单1.xls"
        ]
        self.results = []
        
    def extract_original_classification(self, file_path: str) -> List[Dict]:
        """
        从Excel文件中提取原始分类信息
        """
        logger.info(f"正在提取 {file_path} 的原始分类...")
        
        try:
            # 提取表格
            tables = extract_excel_tables(file_path)
            if not tables:
                logger.warning(f"未能从 {file_path} 提取到表格")
                return []
            
            results = []
            
            for table_info in tables:
                logger.info(f"处理工作表: {table_info['sheet_name']}")
                
                df = table_info['data']
                if df.empty:
                    continue
                
                # 转换为列表格式用于分类提取
                table_data = []
                for _, row in df.iterrows():
                    row_data = [str(cell) if pd.notna(cell) else "" for cell in row]
                    table_data.append(row_data)
                
                # 提取分类信息
                categories = extract_categories_from_table(table_data)
                logger.info(f"提取到分类: {list(categories.keys())}")
                
                # 使用现有的解析工具解析表格数据
                try:
                    # 重要：如果是多工作表文件，需要指定正确的工作表
                    if table_info['sheet_name'] in ['封面', '概述']:
                        logger.info(f"跳过封面/概述工作表: {table_info['sheet_name']}")
                        continue
                    
                    parsed_df = extract_and_parse_instrument_table(df)
                    logger.info(f"解析到 {len(parsed_df)} 条仪表数据")
                    
                    # 为每条仪表数据添加原始分类
                    for idx, row in parsed_df.iterrows():
                        row_idx = row.get('_original_row', idx)
                        original_category = None
                        
                        # 根据行号找到对应的原始分类
                        for cat_name, row_indices in categories.items():
                            if row_idx in row_indices:
                                original_category = cat_name
                                break
                        
                        # 如果解析结果中已有分类信息，使用它
                        if pd.notna(row.get('仪表类型')) and row.get('仪表类型') != '未分类':
                            original_category = row.get('仪表类型')
                        
                        if original_category and pd.notna(row.get('型号')) and str(row.get('型号')).strip():
                            results.append({
                                'file': os.path.basename(file_path),
                                'sheet': table_info['sheet_name'],
                                'row_idx': row_idx,
                                '型号': str(row.get('型号', '')).strip(),
                                '规格': str(row.get('规格', '')).strip(),
                                '位号': str(row.get('位号', '')).strip(),
                                'original_category': original_category,
                                'llm_category': None  # 待填充
                            })
                
                except Exception as e:
                    logger.error(f"解析表格数据失败: {str(e)}")
                    continue
            
            logger.info(f"从 {file_path} 提取到 {len(results)} 条有分类的仪表数据")
            return results
            
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
            return []
    
    def deduplicate_by_model(self, data: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        根据型号去重，保留每个型号的第一次出现
        
        返回:
            (去重后的数据, 型号映射表)
        """
        logger.info(f"开始型号去重，原始数据 {len(data)} 条...")
        
        # 按型号分组
        model_groups = defaultdict(list)
        for item in data:
            model = item['型号']
            model_groups[model].append(item)
        
        # 每个型号只保留第一个
        unique_data = []
        model_mapping = {}  # 型号 -> (原始分类, 出现次数, 示例规格)
        
        for model, items in model_groups.items():
            # 选择第一个作为代表
            representative = items[0]
            unique_data.append(representative)
            
            # 统计同一型号的分类分布
            categories = [item['original_category'] for item in items]
            category_counts = Counter(categories)
            
            # 检查同一型号是否有不同分类（这种情况下需要注意）
            if len(set(categories)) > 1:
                logger.warning(f"型号 {model} 有多个分类: {dict(category_counts)}")
            
            # 选择最常见的分类作为该型号的标准分类
            most_common_category = category_counts.most_common(1)[0][0]
            representative['original_category'] = most_common_category
            
            # 收集所有规格信息
            specs = [item['规格'] for item in items if item['规格']]
            longest_spec = max(specs, key=len) if specs else representative['规格']
            representative['规格'] = longest_spec
            
            model_mapping[model] = {
                'category': most_common_category,
                'count': len(items),
                'spec': longest_spec,
                'all_categories': dict(category_counts)
            }
        
        logger.info(f"去重完成，保留 {len(unique_data)} 个唯一型号")
        logger.info(f"原始数据中共有 {len(model_groups)} 个不同型号")
        
        # 显示型号统计
        sorted_models = sorted(model_mapping.items(), key=lambda x: x[1]['count'], reverse=True)
        logger.info("型号出现次数统计（前10个）:")
        for model, info in sorted_models[:10]:
            logger.info(f"  {model}: {info['count']}次, 分类: {info['category']}")
        
        return unique_data, model_mapping
    
    def test_llm_classification(self, data: List[Dict]) -> List[Dict]:
        """
        使用LLM对仪表进行重新分类（批量模式）
        """
        logger.info(f"开始LLM批量分类测试，共 {len(data)} 个唯一型号...")
        
        # 构建批量分类的提示词
        instruments_info = []
        for i, item in enumerate(data):
            instruments_info.append({
                "index": i,
                "型号": item['型号'],
                "规格": item['规格'],
                "位号": item['位号']
            })
        
        try:
            from config.settings import get_settings
            settings = get_settings()
            
            if not settings.get("openai_api_key"):
                logger.warning("未配置OpenAI API Key，跳过LLM分类")
                for item in data:
                    item['llm_category'] = "无法识别"
                return data
            
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model=settings["llm_model"],
                api_key=settings["openai_api_key"],
                base_url=settings["openai_base_url"],
                temperature=0.1
            )
            
            # 构建批量分类提示词
            prompt = f"""
请对以下 {len(instruments_info)} 个仪表进行分类。每个仪表包含型号、规格和位号信息。

仪表信息列表：
{json.dumps(instruments_info, ensure_ascii=False, indent=2)}

请分析每个仪表的类型，常见类型包括：
- 温度仪表（如热电偶、热电阻、温度计等）
- 压力仪表（如压力表、压力变送器等）
- 流量仪表（如流量计、流量变送器等）
- 液位仪表（如液位计、液位变送器等）
- 调节阀门（如气动调节阀、电动调节阀等）
- 控制设备（如控制箱、控制器等）

重要要求：
1. 只有在非常确定的情况下才返回具体的仪表类型
2. 如果型号不常见、规格信息不足、或存在任何不确定性，请返回"无法识别"
3. 不要基于部分信息进行猜测
4. 必须返回JSON格式，包含每个仪表的分类结果

返回格式示例：
{{
  "results": [
    {{"index": 0, "category": "温度仪表"}},
    {{"index": 1, "category": "压力仪表"}},
    {{"index": 2, "category": "无法识别"}}
  ]
}}

请严格按照JSON格式返回，不要包含任何其他文字：
"""
            
            logger.info("发送批量分类请求到LLM...")
            response = llm.invoke(prompt)
            result_text = response.content.strip()
            
            logger.info(f"收到LLM响应，长度: {len(result_text)}")
            logger.debug(f"LLM响应内容: {result_text[:500]}...")
            
            # 解析JSON响应
            try:
                # 尝试提取JSON部分
                if "```json" in result_text:
                    json_start = result_text.find("```json") + 7
                    json_end = result_text.find("```", json_start)
                    result_text = result_text[json_start:json_end].strip()
                elif "{" in result_text and "}" in result_text:
                    json_start = result_text.find("{")
                    json_end = result_text.rfind("}") + 1
                    result_text = result_text[json_start:json_end]
                
                result_data = json.loads(result_text)
                results = result_data.get("results", [])
                
                # 应用分类结果
                classification_map = {item["index"]: item["category"] for item in results}
                
                for i, item in enumerate(data):
                    if i in classification_map:
                        item['llm_category'] = classification_map[i]
                        logger.info(f"分类成功: {item['型号']} -> {item['llm_category']}")
                    else:
                        item['llm_category'] = "无法识别"
                        logger.warning(f"未找到分类结果: {item['型号']}")
                
                logger.info(f"批量分类完成，成功分类 {len(classification_map)} 个仪表")
                
            except json.JSONDecodeError as e:
                logger.error(f"解析LLM返回的JSON失败: {str(e)}")
                logger.error(f"原始响应: {result_text}")
                # 回退到逐个处理
                logger.info("回退到逐个分类模式...")
                return self._fallback_individual_classification(data)
                
        except Exception as e:
            logger.error(f"LLM批量分类时出错: {str(e)}")
            # 回退到逐个处理
            return self._fallback_individual_classification(data)
        
        return data
    
    def _fallback_individual_classification(self, data: List[Dict]) -> List[Dict]:
        """
        回退方案：逐个分类（当批量分类失败时使用）
        """
        logger.info(f"开始逐个LLM分类，共 {len(data)} 个仪表...")
        
        from tools.classify_instrument_type import classify_by_llm
        
        for i, item in enumerate(data):
            logger.info(f"分类进度: {i+1}/{len(data)} - {item['型号']}")
            
            try:
                llm_result = classify_by_llm(
                    model=item['型号'],
                    spec=item['规格'],
                    context=f"位号: {item['位号']}"
                )
                item['llm_category'] = llm_result or "无法识别"
                
            except Exception as e:
                logger.error(f"LLM分类失败: {str(e)}")
                item['llm_category'] = "分类失败"
        
        return data
    
    def normalize_category(self, category: str) -> str:
        """
        标准化分类名称，便于对比
        """
        if not category or category in ["无法识别", "分类失败"]:
            return category
        
        category = category.strip()
        
        # 标准化映射
        mapping = {
            # 温度类
            "温度仪表": "温度仪表",
            "温度": "温度仪表", 
            "温度测量": "温度仪表",
            "温度传感器": "温度仪表",
            
            # 压力类
            "压力仪表": "压力仪表",
            "压力": "压力仪表",
            "压力测量": "压力仪表", 
            "压力传感器": "压力仪表",
            "压力变送器": "压力仪表",
            
            # 流量类
            "流量仪表": "流量仪表",
            "流量": "流量仪表",
            "流量测量": "流量仪表",
            "流量计": "流量仪表",
            
            # 液位类
            "液位仪表": "液位仪表", 
            "液位": "液位仪表",
            "水位": "液位仪表",
            "液位计": "液位仪表",
            
            # 控制类
            "调节阀门": "调节阀门",
            "调节阀": "调节阀门", 
            "阀门": "调节阀门",
            "控制阀": "调节阀门",
            
            # 控制设备
            "控制设备": "控制设备",
            "控制箱": "控制设备",
            "控制器": "控制设备",
            "DCS": "控制设备"
        }
        
        return mapping.get(category, category)
    
    def calculate_metrics(self, data: List[Dict], model_mapping: Dict) -> Dict:
        """
        计算分类准确率和其他指标
        """
        logger.info("计算分类指标...")
        
        # 过滤掉无法获得LLM结果的数据
        valid_data = [item for item in data if item.get('llm_category') and 
                     item['llm_category'] not in ['分类失败', None]]
        
        if not valid_data:
            return {"error": "没有有效的LLM分类结果"}
        
        # 标准化分类名称
        for item in valid_data:
            item['normalized_original'] = self.normalize_category(item['original_category'])
            item['normalized_llm'] = self.normalize_category(item['llm_category'])
        
        # 计算准确率（按型号）
        correct = 0
        total = len(valid_data)
        
        for item in valid_data:
            if item['normalized_original'] == item['normalized_llm']:
                correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        # 计算按实例数量加权的准确率
        weighted_correct = 0
        weighted_total = 0
        
        for item in valid_data:
            model = item['型号']
            count = model_mapping.get(model, {}).get('count', 1)
            weighted_total += count
            if item['normalized_original'] == item['normalized_llm']:
                weighted_correct += count
        
        weighted_accuracy = weighted_correct / weighted_total if weighted_total > 0 else 0
        
        # 统计原始分类分布（按型号）
        original_dist = Counter(item['normalized_original'] for item in valid_data)
        llm_dist = Counter(item['normalized_llm'] for item in valid_data)
        
        # 统计按实例数量加权的分布
        weighted_original_dist = defaultdict(int)
        weighted_llm_dist = defaultdict(int)
        
        for item in valid_data:
            model = item['型号']
            count = model_mapping.get(model, {}).get('count', 1)
            weighted_original_dist[item['normalized_original']] += count
            weighted_llm_dist[item['normalized_llm']] += count
        
        # 构建混淆矩阵
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        for item in valid_data:
            confusion_matrix[item['normalized_original']][item['normalized_llm']] += 1
        
        # 计算每个类别的指标
        category_metrics = {}
        all_categories = set(original_dist.keys()) | set(llm_dist.keys())
        
        for category in all_categories:
            tp = confusion_matrix[category][category]  # 真正例
            fp = sum(confusion_matrix[other][category] for other in all_categories if other != category)  # 假正例
            fn = sum(confusion_matrix[category][other] for other in all_categories if other != category)  # 假负例
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            category_metrics[category] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'support': original_dist[category]
            }
        
        return {
            'total_unique_models': total,
            'total_instances': weighted_total,
            'correct_predictions': correct,
            'weighted_correct_predictions': weighted_correct,
            'accuracy_by_model': accuracy,
            'accuracy_by_instance': weighted_accuracy,
            'original_distribution_by_model': dict(original_dist),
            'llm_distribution_by_model': dict(llm_dist),
            'original_distribution_by_instance': dict(weighted_original_dist),
            'llm_distribution_by_instance': dict(weighted_llm_dist),
            'confusion_matrix': dict(confusion_matrix),
            'category_metrics': category_metrics,
            'valid_data': valid_data,  # 包含详细数据用于分析
            'model_mapping': model_mapping  # 型号映射信息
        }
    
    def save_results(self, results: Dict, filename: str = None):
        """
        保存测试结果到文件
        """
        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"llm_classification_test_dedup_{timestamp}.json"
        
        # 移除DataFrame等不可序列化的对象
        serializable_results = {}
        for key, value in results.items():
            if key == 'valid_data':
                # 只保留基本信息
                serializable_results[key] = [
                    {k: v for k, v in item.items() if k != 'data'} 
                    for item in value
                ]
            elif isinstance(value, defaultdict):
                serializable_results[key] = dict(value)
            else:
                serializable_results[key] = value
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果已保存到: {filename}")
        return filename
    
    def print_summary(self, results: Dict):
        """
        打印测试结果摘要
        """
        print("\n" + "="*60)
        print("LLM分类效果测试结果（去重版）")
        print("="*60)
        
        if 'error' in results:
            print(f"错误: {results['error']}")
            return
        
        print(f"总唯一型号数: {results['total_unique_models']}")
        print(f"总实例数量: {results['total_instances']}")
        print(f"正确预测（按型号）: {results['correct_predictions']}")
        print(f"正确预测（按实例）: {results['weighted_correct_predictions']}")
        print(f"按型号准确率: {results['accuracy_by_model']:.2%}")
        print(f"按实例准确率: {results['accuracy_by_instance']:.2%}")
        
        print("\n原始分类分布（按型号）:")
        for category, count in results['original_distribution_by_model'].items():
            print(f"  {category}: {count}")
        
        print("\nLLM分类分布（按型号）:")
        for category, count in results['llm_distribution_by_model'].items():
            print(f"  {category}: {count}")
        
        print("\n原始分类分布（按实例）:")
        for category, count in results['original_distribution_by_instance'].items():
            print(f"  {category}: {count}")
        
        print("\nLLM分类分布（按实例）:")
        for category, count in results['llm_distribution_by_instance'].items():
            print(f"  {category}: {count}")
        
        print("\n各类别详细指标（按型号）:")
        print(f"{'类别':<15} {'精确率':<8} {'召回率':<8} {'F1分数':<8} {'样本数':<6}")
        print("-" * 50)
        
        for category, metrics in results['category_metrics'].items():
            print(f"{category:<15} {metrics['precision']:<8.2%} {metrics['recall']:<8.2%} "
                  f"{metrics['f1']:<8.2%} {metrics['support']:<6}")
        
        print("\n混淆矩阵 (原始 -> LLM):")
        confusion = results['confusion_matrix']
        all_cats = sorted(set(results['original_distribution_by_model'].keys()) | 
                         set(results['llm_distribution_by_model'].keys()))
        
        # 打印表头
        header = "原始\\预测"
        print(f"{header:<15}", end="")
        for cat in all_cats:
            print(f"{cat[:10]:<12}", end="")
        print()
        
        # 打印矩阵
        for orig_cat in all_cats:
            print(f"{orig_cat:<15}", end="")
            for pred_cat in all_cats:
                count = confusion.get(orig_cat, {}).get(pred_cat, 0)
                print(f"{count:<12}", end="")
            print()
        
        # 显示一些典型的分类结果
        print("\n典型分类结果示例:")
        valid_data = results['valid_data']
        correct_examples = [item for item in valid_data if item['normalized_original'] == item['normalized_llm']]
        incorrect_examples = [item for item in valid_data if item['normalized_original'] != item['normalized_llm']]
        
        if correct_examples:
            print("正确分类示例（前5个）:")
            for item in correct_examples[:5]:
                model_info = results['model_mapping'].get(item['型号'], {})
                print(f"  {item['型号']} -> {item['normalized_llm']} (正确, 出现{model_info.get('count', 1)}次)")
        
        if incorrect_examples:
            print("错误分类示例（前5个）:")
            for item in incorrect_examples[:5]:
                model_info = results['model_mapping'].get(item['型号'], {})
                print(f"  {item['型号']} -> 原始:{item['normalized_original']}, LLM:{item['normalized_llm']} (出现{model_info.get('count', 1)}次)")
    
    def run_test(self):
        """
        运行完整的测试流程
        """
        logger.info("开始LLM分类效果测试...")
        
        all_data = []
        
        # 从所有测试文件中提取数据
        for file_path in self.test_files:
            if os.path.exists(file_path):
                logger.info(f"处理文件: {file_path}")
                file_data = self.extract_original_classification(file_path)
                all_data.extend(file_data)
            else:
                logger.warning(f"文件不存在: {file_path}")
        
        if not all_data:
            logger.error("未能提取到任何测试数据")
            return
        
        logger.info(f"总共提取到 {len(all_data)} 条测试数据")
        
        # 按型号去重
        unique_data, model_mapping = self.deduplicate_by_model(all_data)
        
        # 使用LLM进行分类
        unique_data = self.test_llm_classification(unique_data)
        
        # 计算指标
        results = self.calculate_metrics(unique_data, model_mapping)
        
        # 打印结果
        self.print_summary(results)
        
        # 保存结果
        result_file = self.save_results(results)
        
        return results, result_file

def main():
    """主函数"""
    tester = LLMClassificationTester()
    results, result_file = tester.run_test()
    
    print(f"\n测试完成！详细结果已保存到: {result_file}")
    
    return results

if __name__ == "__main__":
    results = main() 