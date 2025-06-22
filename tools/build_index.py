"""
向量索引构建工具
用于构建仪表安装规范的向量数据库索引
"""
import os
import sys
import pickle
from typing import List, Dict, Optional
import logging
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# 配置常量
FAISS_INDEX_PATH = "./data/indexes/instrument_standards.index"

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置项现在由DocumentIndexer类内部管理

logger = logging.getLogger(__name__)

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
                # 对于仪表安装规范，按条款号分割
                import re
                
                # 支持多种编号格式的正则表达式
                patterns = [
                    r'第\s*\d+\.\d+\.\d+\s*条',  # 第 1.0.1 条
                    r'[一二三四五六七八九十]{1,2}\.?\s*',  # 一. 或 一
                    r'[一二三四五六七八九十]{1,2}、\s*',  # 一、
                    r'\d+\.?\s*',  # 1. 或 1
                    r'\d+、\s*',  # 1、
                    r'\(\d+\)\s*',  # (1)
                    r'[一二三四五六七八九十]{1,2}\)\s*',  # 一)
                    r'[一二三四五六七八九十]{1,2}\)、\s*',  # 一)、
                    r'①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳',  # ①②③等
                ]
                
                # 先尝试最精确的"第 X.X.X 条"格式
                clause_pattern = r'第\s*\d+\.\d+\.\d+\s*条'
                clause_matches = re.findall(clause_pattern, content)
                
                if len(clause_matches) > 10:  # 如果找到足够多的条款，使用条款分割
                    # 分割文档
                    clauses = re.split(clause_pattern, content)
                    
                    # 重新组合，每个条款包含条款号和内容
                    for i, clause_content in enumerate(clauses):
                        if i == 0:
                            # 第一部分是条款号之前的内容（如果有的话）
                            if clause_content.strip():
                                text_chunks.append(clause_content.strip())
                        else:
                            # 组合条款号和内容
                            if i-1 < len(clause_matches):
                                clause_title = clause_matches[i-1]
                                full_clause = f"{clause_title} {clause_content.strip()}"
                                if len(full_clause) > 20:  # 最小长度过滤
                                    text_chunks.append(full_clause)
                    
                    logger.info(f"按条款分割仪表规范文档 {file_path}，提取了 {len(text_chunks)} 个条款")
                else:
                    # 如果没有足够的"第 X.X.X 条"格式，尝试其他编号格式
                    logger.info(f"未找到足够的标准条款格式，尝试其他编号格式")
                    
                    # 尝试按其他编号格式分割
                    best_split = []
                    best_pattern = None
                    
                    for pattern in patterns[1:]:  # 跳过第一个已经试过的模式
                        try:
                            matches = re.findall(pattern, content)
                            if len(matches) > 5:  # 如果找到足够多的匹配
                                splits = re.split(pattern, content)
                                if len(splits) > len(best_split):
                                    best_split = splits
                                    best_pattern = pattern
                                    best_matches = matches
                        except:
                            continue
                    
                    if best_split and len(best_split) > 3:
                        # 使用找到的最佳分割方式
                        for i, section_content in enumerate(best_split):
                            if i == 0:
                                if section_content.strip():
                                    text_chunks.append(section_content.strip())
                            else:
                                if i-1 < len(best_matches):
                                    section_title = best_matches[i-1]
                                    full_section = f"{section_title} {section_content.strip()}"
                                    if len(full_section) > 20:
                                        text_chunks.append(full_section)
                        
                        logger.info(f"按编号格式 '{best_pattern}' 分割文档 {file_path}，提取了 {len(text_chunks)} 个段落")
                    else:
                        # 如果所有编号格式都不适用，回退到段落分割
                        paragraphs = content.split('\n')
                        for paragraph in paragraphs:
                            paragraph = paragraph.strip()
                            if paragraph and len(paragraph) > 50:  # 对于复杂文档提高最小长度
                                text_chunks.append(paragraph)
                        
                        logger.info(f"使用段落分割文档 {file_path}，提取了 {len(text_chunks)} 个段落")
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
        构建向量索引
        
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
    
    parser = argparse.ArgumentParser(description='向量索引构建工具')
    parser.add_argument('--list', action='store_true', 
                        help='仅列出data/standards目录中的文档文件，不构建索引')
    
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
        # 默认模式：构建向量索引 - 使用用户的真实PDF文件
        print("🔍 正在扫描data/standards目录中的文档文件...")
        success = rebuild_rag_index()
        if not success:
            print("\n❌ 构建失败的可能原因:")
            print("1. data/standards/ 目录不存在")
            print("2. 目录中没有PDF、TXT或MD文件")
            print("3. 文件无法读取或格式不支持")
            print("\n💡 建议:")
            print("- 将您的PDF文档放入data/standards目录")
            print("- 运行 'python tools/build_index.py --list' 查看当前文件")
            sys.exit(1) 