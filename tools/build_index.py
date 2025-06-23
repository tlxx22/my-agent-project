"""
向量索引构建工具
用于构建仪表安装规范的向量数据库索引
"""
import os
import sys
import pickle
import json
import re
from typing import List, Dict, Optional
import logging
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime
from pathlib import Path
import argparse
from collections import Counter
import fitz  # PyMuPDF

# 配置常量
FAISS_INDEX_PATH = "./data/indexes/instrument_standards.index"

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置项现在由DocumentIndexer类内部管理

logger = logging.getLogger(__name__)

class InstrumentTypeClassifier:
    """LLM驱动的仪表类型智能识别器"""
    
    def __init__(self):
        self.identified_types = {}
        self.classification_cache = {}
    
    def analyze_documents_with_llm(self, documents: List[str]) -> Dict[str, Dict]:
        """
        使用智能分析识别文档中的主要仪表类型
        
        Args:
            documents: 文档文本列表
        
        Returns:
            识别出的仪表类型字典
        """
        logger.info("🤖 启动智能识别仪表类型...")
        logger.info(f"📚 分析文档数量: {len(documents)} 个文档块")
        
        # 合并所有文档文本进行分析（不限制数量）
        combined_text = "\n".join(documents)  # 分析所有文档块
        
        # 设计LLM分析prompt
        analysis_prompt = f"""
请分析以下仪表安装规范文档，识别出文档中提到的**具体仪表类型**。

要求：
1. 只识别具体的仪表设备名称，如"热电偶"、"压力变送器"、"电磁流量计"等
2. **排除通用词汇**，如"仪表"、"设备"、"装置"等
3. 每种仪表类型需要在文档中出现至少3次
4. 优先识别完整的仪表名称（如"电磁流量计"而不是"流量计"）
5. 返回JSON格式，包含仪表类型、出现频次、所属类别

文档内容：
{combined_text}

请以JSON格式返回，格式如下：
{{
    "instrument_types": {{
        "热电偶": {{
            "category": "温度",
            "frequency": 15,
            "description": "用于温度测量的传感器"
        }},
        "压力变送器": {{
            "category": "压力", 
            "frequency": 12,
            "description": "用于压力信号变送的仪表"
        }}
    }}
}}
"""
        
        try:
            # 尝试使用LLM进行分析
            result = self._call_llm_for_analysis(analysis_prompt)
            
            if result and "instrument_types" in result:
                logger.info(f"✅ LLM成功识别了 {len(result['instrument_types'])} 种仪表类型")
                
                # 验证和过滤结果
                filtered_types = self._filter_and_validate_types(result['instrument_types'], documents)
                
                return filtered_types
            else:
                logger.warning("⚠️ LLM分析结果格式不正确，无法识别仪表类型")
                return {}
                
        except Exception as e:
            logger.warning(f"⚠️ LLM分析失败: {str(e)}，无法识别仪表类型")
            return {}
    
    def _call_llm_for_analysis(self, prompt: str) -> Dict:
        """
        调用LLM进行分析
        
        Args:
            prompt: 分析提示词
        
        Returns:
            LLM分析结果
        """
        # 这里可以集成不同的LLM服务
        # 比如OpenAI API、Azure OpenAI、本地LLM等
        
        try:
            # 首先尝试使用config中配置的LLM
            from config.settings import get_openai_config
            llm_config = get_openai_config()
            
            # 检查是否有有效的API key
            if llm_config.get('api_key'):
                logger.info(f"🤖 使用OpenAI API: {llm_config.get('model', 'gpt-4o-mini')}")
                return self._call_openai_llm(prompt, llm_config)
            else:
                logger.warning("⚠️ OpenAI API key未配置，使用本地分析")
                return self._call_local_llm(prompt)
                
        except ImportError:
            logger.info("未找到LLM配置，尝试本地分析")
            return self._call_local_llm(prompt)
    
    def _call_openai_llm(self, prompt: str, config: Dict) -> Dict:
        """调用OpenAI API"""
        try:
            from openai import OpenAI
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=config.get('api_key'),
                base_url=config.get('base_url', 'https://api.openai.com/v1')
            )
            
            logger.info(f"📡 调用OpenAI API - 模型: {config.get('model', 'gpt-4o-mini')}")
            
            response = client.chat.completions.create(
                model=config.get('model', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "你是一个专业的工业仪表识别专家。请仔细分析文档内容，识别出具体的仪表类型，避免通用词汇如'仪表'、'设备'等。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content
            logger.info(f"✅ OpenAI API调用成功，响应长度: {len(result_text)} 字符")
            
            # 解析JSON响应
            import json
            try:
                return json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON解析失败: {e}")
                logger.info(f"原始响应: {result_text[:500]}...")
                # 尝试提取JSON内容
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    raise
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            raise
    
    def _call_local_llm(self, prompt: str) -> Dict:
        """本地LLM备用方案（现在直接返回空，因为我们有OpenAI API）"""
        logger.warning("⚠️ 没有可用的LLM配置，无法进行仪表类型识别")
        return {
            'instrument_types': {}
        }
    
    def _filter_and_validate_types(self, types_dict: Dict, documents: List[str]) -> Dict:
        """
        过滤LLM识别的仪表类型（只过滤通用词汇，直接接受LLM结果）
        
        Args:
            types_dict: LLM识别的仪表类型字典
            documents: 原始文档列表（不再使用）
        
        Returns:
            过滤后的仪表类型字典
        """
        filtered_types = {}
        
        # 通用词汇黑名单
        blacklist = {
            '仪表', '设备', '装置', '器件', '元件', '部件', '系统', '控制', 
            '测量', '检测', '监测', '传感', '执行', '调节', '安装', '配置'
        }
        
        for instrument_name, info in types_dict.items():
            # 只过滤通用词汇，其他全部接受
            if instrument_name.lower() in blacklist:
                logger.info(f"🚫 过滤通用词汇: {instrument_name}")
                continue
            
            # 直接接受LLM识别的结果，不进行任何频次检查
            filtered_types[instrument_name] = {
                'category': info.get('category', '其他'),
                'frequency': info.get('frequency', 1),  # 使用LLM估计的频次
                'description': info.get('description', ''),
                'llm_confidence': info.get('frequency', 0)  # LLM估计的频次
            }
            logger.info(f"✅ 接受LLM识别: {instrument_name} (类别: {info.get('category', '其他')})")
        
        return filtered_types
    
    def save_classification_results(self, types_dict: Dict, save_path: str = "./data/llm_instrument_types.json"):
        """
        保存LLM识别的仪表类型结果
        
        Args:
            types_dict: 识别结果字典
            save_path: 保存路径
        """
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 添加元数据
            result_data = {
                'instrument_types': types_dict,
                'metadata': {
                    'total_types': len(types_dict),
                    'generation_time': str(datetime.now()),
                    'method': 'llm_analysis'
                }
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📁 仪表类型识别结果已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"保存识别结果失败: {str(e)}")

class DocumentIndexer:
    """文档向量索引构建器"""
    
    def __init__(self, model_name: str = None, dimension: int = None):
        """
        初始化文档索引器
        
        Args:
            model_name: 嵌入模型名称，默认使用中文优化模型
            dimension: 向量维度（自动从模型获取）
        """
        # 使用对中文支持更好的embedding模型
        self.model_name = model_name or "shibing624/text2vec-base-chinese"
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []
        
        # 添加仪表类型分类器
        self.instrument_classifier = InstrumentTypeClassifier()
        
    def _load_model(self):
        """加载嵌入模型"""
        if self.model is None:
            try:
                logger.info(f"加载嵌入模型: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("嵌入模型加载成功")
            except Exception as e:
                logger.error(f"加载嵌入模型失败: {str(e)}")
                # 备用方案：使用更通用的模型
                try:
                    self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    logger.info("使用备用嵌入模型")
                except Exception as e2:
                    logger.error(f"备用模型也加载失败: {str(e2)}")
                    raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        从PDF文件中提取文本，支持多种提取方法
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本段落列表
        """
        text_chunks = []
        
        try:
            # 方法1：使用PyPDF2提取
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            # 按用户要求：以\n为分段标准，保持原始段落结构
                            paragraphs = text.split('\n')
                            
                            for paragraph in paragraphs:
                                paragraph = paragraph.strip()
                                # 只要不是空行，且有一定长度，就作为一个文本块
                                if paragraph and len(paragraph) > 10:  # 最小长度要求降低
                                    text_chunks.append(paragraph)
                                    
                    except Exception as e:
                        logger.warning(f"提取第{page_num+1}页文本时出错: {str(e)}")
                        continue
                
            # 如果PyPDF2提取效果不好，尝试其他方法
            if len(text_chunks) < 5:  # 如果提取的文本块太少
                logger.warning(f"PyPDF2提取效果不佳，尝试其他方法...")
                text_chunks = self._try_alternative_pdf_extraction(pdf_path)
                
                logger.info(f"从PDF文件 {pdf_path} 提取了 {len(text_chunks)} 个文本块")
                return text_chunks
                
        except Exception as e:
            logger.error(f"读取PDF文件失败: {str(e)}")
            return []
    
    def _try_alternative_pdf_extraction(self, pdf_path: str) -> List[str]:
        """
        尝试其他PDF文本提取方法
        """
        text_chunks = []
        
        try:
            # 尝试使用pdfplumber（如果可用）
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            # 按用户要求：以\n为分段标准
                            paragraphs = text.split('\n')
                            for para in paragraphs:
                                para = para.strip()
                                if para and len(para) > 10:
                                    text_chunks.append(para)
                logger.info(f"使用pdfplumber提取了 {len(text_chunks)} 个文本块")
                return text_chunks
            except ImportError:
                logger.info("pdfplumber未安装，跳过")
            
            # 尝试使用pymupdf（如果可用）
            try:
                import fitz  # pymupdf
                doc = fitz.open(pdf_path)
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    if text:
                        # 按用户要求：以\n为分段标准
                        paragraphs = text.split('\n')
                        for para in paragraphs:
                            para = para.strip()
                            if para and len(para) > 10:
                                text_chunks.append(para)
                doc.close()
                logger.info(f"使用pymupdf提取了 {len(text_chunks)} 个文本块")
                return text_chunks
            except ImportError:
                logger.info("pymupdf未安装，跳过")
                
        except Exception as e:
            logger.warning(f"备用PDF提取方法失败: {str(e)}")
        
        return text_chunks
    
    def extract_text_from_txt(self, file_path: str) -> List[str]:
        """从TXT文件中提取文本块"""
        text_chunks = []
        
        try:
            # 尝试不同编码读取文件
            encodings = ['utf-8', 'gbk', 'gb2312']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read().strip()
                        break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"无法使用任何编码读取文件: {file_path}")
                return []
            
            if not content:
                return []
            
            # 检查是否是仪表安装规范文档（通过文件名和内容特征判断）
            is_instrument_standard = (
                '仪表安装规范' in os.path.basename(file_path) or 
                '第 1.0.1 条本规范适用于工业自动化仪表' in content[:200]
            )
            
            if is_instrument_standard:
                # 对于仪表安装规范，使用多级标题智能分割
                import re
                
                # 定义多级标题的正则模式（按重要性排序）
                hierarchical_patterns = [
                    (r'第\s*\d+\.\d+\.\d+\s*条', '条款'),          # 第 1.0.1 条 (最重要)
                    (r'第\s*\d+\.\d+\s*条', '条款'),             # 第 1.1 条
                    (r'第\s*\d+\s*条', '条款'),                  # 第 1 条
                    (r'[一二三四五六七八九十]{1,2}\.', '一级标题'),   # 一. 二. 等
                    (r'[一二三四五六七八九十]{1,2}、', '一级标题'),   # 一、二、等  
                    (r'\d+\.', '二级标题'),                     # 1. 2. 等
                    (r'\d+、', '二级标题'),                     # 1、2、等
                    (r'\(\d+\)', '三级标题'),                   # (1) (2) 等
                    (r'[一二三四五六七八九十]{1,2}\)', '三级标题'), # 一) 二) 等
                    (r'[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]', '四级标题'), # ① ② 等
                ]
                
                # 同时应用所有正则，找出所有可能的分割点
                all_splits = []
                
                for pattern, level_name in hierarchical_patterns:
                    try:
                        # 找出该模式的所有匹配位置
                        for match in re.finditer(pattern, content):
                            all_splits.append({
                                'start': match.start(),
                                'end': match.end(),
                                'title': match.group(),
                                'level': level_name,
                                'pattern': pattern
                            })
                    except Exception as e:
                        logger.warning(f"正则模式 {pattern} 执行失败: {e}")
                        continue
                
                if all_splits:
                    # 按位置排序所有分割点
                    all_splits.sort(key=lambda x: x['start'])
                    
                    logger.info(f"🔍 找到 {len(all_splits)} 个多级标题分割点")
                    
                    # 提取各个段落
                    for i, split_info in enumerate(all_splits):
                        # 确定段落内容的范围
                        content_start = split_info['end']
                        
                        # 找到下一个分割点
                        if i + 1 < len(all_splits):
                            content_end = all_splits[i + 1]['start']
                        else:
                            content_end = len(content)
                        
                        # 提取段落内容
                        section_content = content[content_start:content_end].strip()
                        
                        if section_content:
                            # 组合完整段落
                            full_section = f"[{split_info['level']}] {split_info['title']} {section_content}"
                            
                            # 过滤掉太短的段落
                            if len(section_content) > 20:
                                text_chunks.append(full_section)
                    
                    logger.info(f"✅ 多级标题分割完成，提取了 {len(text_chunks)} 个结构化段落")
                
                else:
                    # 如果没有找到任何结构化标题，回退到段落分割
                    logger.info("未找到结构化标题，使用段落分割")
                    paragraphs = content.split('\n\n')
                    for paragraph in paragraphs:
                        paragraph = paragraph.strip()
                        if paragraph and len(paragraph) > 30:
                            text_chunks.append(paragraph)
                    
                    logger.info(f"段落分割提取了 {len(text_chunks)} 个段落")
            else:
                # 对于其他文档，保持原有的按段落分割逻辑
                paragraphs = content.split('\n')
                for paragraph in paragraphs:
                    paragraph = paragraph.strip()
                    if paragraph and len(paragraph) > 10:
                        text_chunks.append(paragraph)
                        
                logger.info(f"从文本文件 {file_path} 提取了 {len(text_chunks)} 个文本块")
            
            return text_chunks
            
        except Exception as e:
            logger.error(f"读取文本文件失败: {str(e)}")
            return []
    
    def process_documents(self, file_paths: List[str]) -> List[Dict]:
        """
        处理多个文档文件
        
        Args:
            file_paths: 文档文件路径列表
        
        Returns:
            处理后的文档信息列表
        """
        all_documents = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                continue
            
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.pdf':
                text_chunks = self.extract_text_from_pdf(file_path)
            elif file_ext in ['.txt', '.md']:
                text_chunks = self.extract_text_from_txt(file_path)
            else:
                logger.warning(f"不支持的文件格式: {file_path}")
                continue
            
            # 为每个文本块添加元数据
            for i, chunk in enumerate(text_chunks):
                doc_info = {
                    'content': chunk,
                    'source_file': file_path,
                    'chunk_id': i,
                    'file_type': file_ext
                }
                all_documents.append(doc_info)
        
        logger.info(f"总共处理了 {len(all_documents)} 个文档块")
        return all_documents
    
    def build_index(self, file_paths: List[str], index_path: str = None) -> bool:
        """
        构建向量索引（增强版：包含LLM仪表类型识别）
        
        Args:
            file_paths: 文档文件路径列表
            index_path: 索引保存路径
        
        Returns:
            是否构建成功
        """
        try:
            # 加载模型
            self._load_model()
            
            # 处理文档
            documents = self.process_documents(file_paths)
            if not documents:
                logger.error("没有找到有效的文档内容")
                return False
            
            # 提取文本内容
            texts = [doc['content'] for doc in documents]
            
            # 🤖 新增：LLM智能识别仪表类型
            logger.info("🤖 启动LLM智能识别仪表类型...")
            instrument_types = self.instrument_classifier.analyze_documents_with_llm(texts)
            
            if instrument_types:
                # 保存识别结果
                self.instrument_classifier.save_classification_results(instrument_types)
                logger.info(f"✅ LLM成功识别了 {len(instrument_types)} 种具体仪表类型")
                
                # 显示识别结果
                print(f"\n🎯 LLM识别的仪表类型:")
                for instrument, info in instrument_types.items():
                    print(f"   • {instrument} (类别: {info['category']}, 频次: {info['frequency']})")
            else:
                logger.warning("⚠️ 未能识别出仪表类型")
            
            # 生成嵌入向量
            logger.info("开始生成文档嵌入向量...")
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            # 创建FAISS索引
            logger.info("创建FAISS索引...")
            self.index = faiss.IndexFlatIP(embeddings.shape[1])  # 使用内积作为相似度度量
            
            # 标准化向量以使用余弦相似度
            faiss.normalize_L2(embeddings)
            
            # 添加向量到索引
            self.index.add(embeddings.astype(np.float32))
            
            # 保存文档和元数据
            self.documents = texts
            self.metadata = documents
            
            # 保存索引到文件
            if index_path is None:
                index_path = FAISS_INDEX_PATH
            
            self.save_index(index_path)
            
            logger.info(f"成功构建向量索引，包含 {len(texts)} 个文档块")
            return True
            
        except Exception as e:
            logger.error(f"构建向量索引失败: {str(e)}")
            return False
    
    def save_index(self, index_path: str):
        """
        保存索引到文件
        
        Args:
            index_path: 索引文件路径
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # 保存FAISS索引
            faiss.write_index(self.index, index_path)
            
            # 保存文档和元数据
            metadata_path = index_path.replace('.index', '_metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadata': self.metadata,
                    'model_name': self.model_name
                }, f)
            
            logger.info(f"索引已保存到: {index_path}")
            
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
            raise
    
    def load_index(self, index_path: str) -> bool:
        """
        从文件加载索引
        
        Args:
            index_path: 索引文件路径
        
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(index_path):
                logger.error(f"索引文件不存在: {index_path}")
                return False
            
            # 加载FAISS索引
            self.index = faiss.read_index(index_path)
            
            # 加载文档和元数据
            metadata_path = index_path.replace('.index', '_metadata.pkl')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.metadata = data['metadata']
                    self.model_name = data.get('model_name', self.model_name)
            
            # 加载模型
            self._load_model()
            
            logger.info(f"成功加载索引，包含 {len(self.documents)} 个文档块")
            return True
            
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}")
            return False

def build_index_from_files(file_paths: List[str], index_path: str = None) -> bool:
    """
    从文件列表构建向量索引的便捷函数
    
    Args:
        file_paths: 文档文件路径列表
        index_path: 索引保存路径
    
    Returns:
        是否构建成功
    """
    indexer = DocumentIndexer()
    return indexer.build_index(file_paths, index_path)

def scan_and_list_documents():
    """
    扫描并列出data/standards目录中的所有文档文件
    不创建任何硬编码的示例文件
    """
    import glob
    
    # 动态确定项目根目录和data/standards路径
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)  # tools目录
    
    # 从tools目录向上找到项目根目录
    project_root = os.path.dirname(current_dir)  # 项目根目录
    standards_dir = os.path.join(project_root, "data", "standards")
    
    # 如果上面的路径不存在，尝试其他可能的位置
    if not os.path.exists(standards_dir):
        # 尝试当前工作目录下的data/standards
        cwd_standards = os.path.join(os.getcwd(), "data", "standards")
        if os.path.exists(cwd_standards):
            standards_dir = cwd_standards
        else:
            # 向上搜索包含data目录的目录
            search_dir = current_dir
            while search_dir != os.path.dirname(search_dir):
                test_data_dir = os.path.join(search_dir, "data", "standards")
                if os.path.exists(test_data_dir):
                    standards_dir = test_data_dir
                    break
                search_dir = os.path.dirname(search_dir)
    
    print(f"扫描目录: {standards_dir}")
    
    if not os.path.exists(standards_dir):
        print(f"目录不存在: {standards_dir}")
        return []
    
    # 扫描所有支持的文档文件
    supported_extensions = ['*.pdf', '*.PDF', '*.txt', '*.TXT', '*.md', '*.MD']
    all_files = []
    
    for extension in supported_extensions:
        pattern = os.path.join(standards_dir, extension)
        found_files = glob.glob(pattern)
        all_files.extend(found_files)
    
    all_files = sorted(list(set(all_files)))
    
    if all_files:
        print(f"找到 {len(all_files)} 个文档文件:")
        for file_path in all_files:
            try:
                file_size = os.path.getsize(file_path) / 1024
                print(f"  - {os.path.basename(file_path)} ({file_size:.1f} KB)")
            except Exception as e:
                print(f"  - {os.path.basename(file_path)} (无法获取大小)")
    else:
        print("未找到任何文档文件")
        
        # 列出目录中的所有文件
        try:
            all_items = os.listdir(standards_dir)
            if all_items:
                print("目录中现有的文件:")
                for item in all_items:
                    print(f"  - {item}")
            else:
                print("目录为空")
        except Exception as e:
            print(f"无法列出目录内容: {str(e)}")
    
    return all_files

def rebuild_rag_index():
    """重新构建RAG向量索引的便捷函数 - 动态搜索所有PDF文件"""
    import glob
    
    # 动态确定项目根目录和data/standards路径
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)  # tools目录
    
    # 从tools目录向上找到项目根目录（包含contest1等）
    project_root = os.path.dirname(current_dir)  # 项目根目录
    standards_dir = os.path.join(project_root, "data", "standards")
    
    # 如果上面的路径不存在，尝试其他可能的位置
    if not os.path.exists(standards_dir):
        # 尝试当前工作目录下的data/standards
        cwd_standards = os.path.join(os.getcwd(), "data", "standards")
        if os.path.exists(cwd_standards):
            standards_dir = cwd_standards
        else:
            # 向上搜索包含data目录的目录
            search_dir = current_dir
            while search_dir != os.path.dirname(search_dir):
                test_data_dir = os.path.join(search_dir, "data", "standards")
                if os.path.exists(test_data_dir):
                    standards_dir = test_data_dir
                    break
                search_dir = os.path.dirname(search_dir)
    
    print(f"扫描目录: {standards_dir}")
    
    if not os.path.exists(standards_dir):
        print(f"错误: 标准文档目录不存在: {standards_dir}")
        print(f"请确保 data/standards/ 目录存在且包含PDF文件")
        return False
    
    # 动态搜索所有支持的文档文件（绝不硬编码文件名）
    supported_extensions = ['*.pdf', '*.PDF', '*.txt', '*.TXT', '*.md', '*.MD']
    all_files = []
    
    print("正在扫描所有文档文件...")
    for extension in supported_extensions:
        pattern = os.path.join(standards_dir, extension)
        found_files = glob.glob(pattern)
        all_files.extend(found_files)
    
    # 去重并排序
    all_files = sorted(list(set(all_files)))
    
    if not all_files:
        print(f"错误: 在目录 {standards_dir} 中未找到任何文档文件")
        print("支持的文件格式: PDF, TXT, MD")
        
        # 列出目录中的所有文件（用于调试）
        try:
            all_items = os.listdir(standards_dir)
            if all_items:
                print(f"目录中现有的文件:")
                for item in all_items:
                    item_path = os.path.join(standards_dir, item)
                    if os.path.isfile(item_path):
                        file_size = os.path.getsize(item_path) / 1024
                        print(f"  - {item} ({file_size:.1f} KB)")
            else:
                print("目录为空")
        except Exception as e:
            print(f"无法列出目录内容: {str(e)}")
        
        return False
    
    print(f"找到 {len(all_files)} 个文档文件:")
    total_size = 0
    for file_path in all_files:
        try:
            file_size = os.path.getsize(file_path) / 1024  # KB
            total_size += file_size
            print(f"  - {os.path.basename(file_path)} ({file_size:.1f} KB)")
        except Exception as e:
            print(f"  - {os.path.basename(file_path)} (无法获取大小: {str(e)})")
    
    print(f"总计: {total_size:.1f} KB")
    
    # 构建向量索引
    print(f"\n开始构建向量索引...")
    indexer = DocumentIndexer()
    success = indexer.build_index(all_files)
    
    if success:
        print(f"✅ 成功: 向量索引构建成功！")
        print(f"📊 统计: 索引包含 {len(indexer.documents)} 个文档块")
        print(f"💾 保存: 索引已保存到: data/indexes/instrument_standards.index")
        print(f"\n🎉 完成: 智能体现在可以自动检索这些文档内容了！")
        return True
    else:
        print(f"❌ 失败: 向量索引构建失败")
        return False

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description='向量索引构建工具（集成LLM仪表类型识别）')
    parser.add_argument('--list', action='store_true', 
                        help='仅列出data/standards目录中的文档文件，不构建索引')
    parser.add_argument('--mode', choices=['test', 'rebuild'], default='rebuild',
                        help='运行模式: test(使用示例数据) 或 rebuild(使用用户PDF)')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    if args.list:
        # 仅扫描并列出文档文件
        print("扫描data/standards目录中的文档文件...")
        files = scan_and_list_documents()
        if files:
            print(f"\n可用于构建索引的文件: {len(files)} 个")
        else:
            print("\n未找到可用的文档文件")
            print("请将PDF、TXT或MD格式的文档放入data/standards目录")
    else:
        # 默认模式：构建向量索引 + LLM仪表类型识别
        print("🚀 启动智能向量索引构建（集成LLM仪表类型识别）")
        print(f"📅 开始时间: {datetime.now()}")
        success = rebuild_rag_index()
        
        if success:
            print(f"\n🎉 完成时间: {datetime.now()}")
            print("✅ 索引构建成功，包含以下功能:")
            print("   1. 📚 文档向量化索引")
            print("   2. 🤖 LLM智能仪表类型识别")
            print("   3. 📁 结果文件保存")
            print("\n💡 现在可以使用自适应RAG系统进行智能查询了！")
        else:
            print(f"\n❌ 完成时间: {datetime.now()}")
            print("构建失败的可能原因:")
            print("1. data/standards/ 目录不存在")
            print("2. 目录中没有PDF、TXT或MD文件")
            print("3. LLM配置问题（将使用备用方案）")
            sys.exit(1) 