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

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config.settings import FAISS_INDEX_PATH, VECTOR_DIMENSION, EMBEDDING_MODEL
except ImportError:
    # 如果无法导入配置，使用默认值
    FAISS_INDEX_PATH = "data/indexes/instrument_standards.index"
    VECTOR_DIMENSION = 384
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """文档向量索引构建器"""
    
    def __init__(self, model_name: str = None, dimension: int = None):
        """
        初始化索引构建器
        
        Args:
            model_name: 嵌入模型名称
            dimension: 向量维度
        """
        self.model_name = model_name or "all-MiniLM-L6-v2"  # 使用轻量级的多语言模型
        self.dimension = dimension or VECTOR_DIMENSION
        self.model = None
        self.index = None
        self.documents = []  # 存储原始文档内容
        self.metadata = []   # 存储文档元数据
        
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
        从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            提取的文本段落列表
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                text_chunks = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            # 按段落分割文本
                            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                            for para in paragraphs:
                                if len(para) > 50:  # 过滤太短的段落
                                    text_chunks.append(para)
                                    
                    except Exception as e:
                        logger.warning(f"提取第{page_num+1}页文本时出错: {str(e)}")
                        continue
                
                logger.info(f"从PDF文件 {pdf_path} 提取了 {len(text_chunks)} 个文本块")
                return text_chunks
                
        except Exception as e:
            logger.error(f"读取PDF文件失败: {str(e)}")
            return []
    
    def extract_text_from_txt(self, txt_path: str, encoding: str = 'utf-8') -> List[str]:
        """
        从文本文件中提取文本
        
        Args:
            txt_path: 文本文件路径
            encoding: 文件编码
        
        Returns:
            提取的文本段落列表
        """
        try:
            # 尝试不同的编码
            encodings = [encoding, 'utf-8', 'gbk', 'gb2312']
            
            for enc in encodings:
                try:
                    with open(txt_path, 'r', encoding=enc) as file:
                        content = file.read()
                        break
                except UnicodeDecodeError:
                    continue
            else:
                logger.error(f"无法使用任何编码读取文件: {txt_path}")
                return []
            
            # 按段落分割
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
            
            # 合并短行形成有意义的段落，分割长段落
            text_chunks = []
            current_chunk = ""
            
            for para in paragraphs:
                # 如果当前行很短（可能是标题或列表项），尝试与下一行合并
                if len(para) < 100 and len(current_chunk + para) < 500:
                    if current_chunk:
                        current_chunk += "\n" + para
                    else:
                        current_chunk = para
                else:
                    # 保存之前的块
                    if current_chunk and len(current_chunk.strip()) > 50:
                        text_chunks.append(current_chunk.strip())
                    
                    # 处理当前段落
                    if len(para) > 1000:  # 如果段落太长，按句子分割
                        sentences = para.split('。')
                        temp_chunk = ""
                        for sentence in sentences:
                            if len(temp_chunk + sentence) < 500:
                                temp_chunk += sentence + "。"
                            else:
                                if temp_chunk:
                                    text_chunks.append(temp_chunk)
                                temp_chunk = sentence + "。"
                        current_chunk = temp_chunk
                    else:
                        current_chunk = para
            
            # 添加最后的块
            if current_chunk and len(current_chunk.strip()) > 50:
                text_chunks.append(current_chunk.strip())
            
            logger.info(f"从文本文件 {txt_path} 提取了 {len(text_chunks)} 个文本块")
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

def create_sample_standards_data():
    """
    创建示例的标准规范数据（仅在文件不存在时创建）
    """
    sample_data = """
# 工业自动化仪表安装设计规范（示例内容）

## 第一章 总则

1.1 为规范工业自动化仪表的安装设计，确保仪表系统的安全、可靠、经济运行，制定本规范。

1.2 本规范适用于新建、扩建和改建工程中工业自动化仪表的安装设计。

## 第二章 温度仪表安装

2.1 热电偶安装要求
热电偶应安装在工艺要求的测温位置，插入深度应满足工艺要求。热电偶保护管应有足够的机械强度，材质应与被测介质相容。

2.2 热电阻安装要求  
热电阻的安装位置应代表被测介质的温度，避免受到辐射热的影响。PT100热电阻应采用三线制或四线制接线。

2.3 温度变送器安装
温度变送器应安装在便于维护的位置，避免振动和强电磁干扰。接线盒应有良好的密封性能。

## 第三章 压力仪表安装

3.1 压力表安装位置
压力表应安装在便于观察和维护的位置，表盘中心高度宜为1.2-1.6米。压力表前应设置三通旋塞或针型阀。

3.2 压力变送器安装
压力变送器应安装在无振动、无冲击、温度变化小的地方。测量蒸汽压力时应设置凝液管。

3.3 压力管路要求
压力管路应有适当的坡度，避免积液或积气。管路材质应耐压且与介质相容。

## 第四章 流量仪表安装

4.1 孔板流量计安装
孔板前直管段长度不小于10D，后直管段不小于5D。孔板应垂直安装，开孔方向正确。

4.2 涡轮流量计安装
涡轮流量计前后应有足够的直管段，前15D后5D。应设置过滤器保护涡轮叶片。

## 第五章 液位仪表安装

5.1 磁翻板液位计安装
磁翻板液位计应垂直安装，与容器壁间距不小于100mm。连接法兰应水平，密封良好。

5.2 液位变送器安装
液位变送器应安装在无振动的支架上，电缆应有防护措施。测量腐蚀性介质时应选择耐腐蚀材质。

## 第六章 安装材料要求

6.1 管路材料
仪表管路应选用无缝钢管，壁厚满足承压要求。不锈钢管适用于腐蚀性介质。

6.2 阀门选择
截止阀用于切断，球阀用于频繁操作，针型阀用于精细调节。阀门材质应与介质相容。

6.3 电缆要求
仪表电缆应选用阻燃型，在腐蚀环境中应加装保护套管。信号电缆应与动力电缆分开敷设。
    """
    
    # 确保目录存在
    standards_dir = "./data/standards/"
    os.makedirs(standards_dir, exist_ok=True)
    
    # 保存示例数据
    sample_file = os.path.join(standards_dir, "仪表安装规范示例.txt")
    
    # 只在文件不存在时创建
    if not os.path.exists(sample_file):
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write(sample_data)
        logger.info(f"已创建示例规范文件: {sample_file}")
    else:
        logger.info(f"示例规范文件已存在: {sample_file}")
    
    return sample_file

def rebuild_rag_index():
    """重新构建RAG向量索引的便捷函数"""
    import glob
    
    # 扫描标准文档目录
    if __name__ == "__main__":
        # 从tools目录运行时
        standards_dir = "../data/standards/"
    else:
        # 从其他地方导入时
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        standards_dir = os.path.join(project_root, "data", "standards")
    
    if not os.path.exists(standards_dir):
        print(f"错误: 标准文档目录不存在: {standards_dir}")
        return False
    
    # 查找所有支持的文档文件
    file_patterns = [
        os.path.join(standards_dir, "*.pdf"),
        os.path.join(standards_dir, "*.txt"), 
        os.path.join(standards_dir, "*.md")
    ]
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(pattern))
    
    if not all_files:
        print(f"错误: 在目录 {standards_dir} 中未找到任何文档文件")
        return False
    
    print(f"找到 {len(all_files)} 个文档文件:")
    for file_path in all_files:
        file_size = os.path.getsize(file_path) / 1024  # KB
        print(f"  - {os.path.basename(file_path)} ({file_size:.1f} KB)")
    
    # 构建向量索引
    print(f"\n开始构建向量索引...")
    indexer = DocumentIndexer()
    success = indexer.build_index(all_files)
    
    if success:
        print(f"成功: 向量索引构建成功！")
        print(f"统计: 索引包含 {len(indexer.documents)} 个文档块")
        print(f"保存: 索引已保存到: data/indexes/instrument_standards.index")
        print(f"\n完成: 智能体现在可以自动检索这些文档内容了！")
        return True
    else:
        print(f"失败: 向量索引构建失败")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='向量索引构建工具')
    parser.add_argument('--mode', choices=['test', 'rebuild'], default='test',
                        help='运行模式: test=创建示例数据测试, rebuild=重建完整索引')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    if args.mode == 'rebuild':
        # 重建完整RAG索引
        success = rebuild_rag_index()
        if not success:
            print("重建索引失败，切换到测试模式")
            args.mode = 'test'
    
    if args.mode == 'test':
        # 测试模式：使用示例数据
        sample_file = create_sample_standards_data()
        
        print("开始构建向量索引...")
        indexer = DocumentIndexer()
        success = indexer.build_index([sample_file])
        
        if success:
            print("向量索引构建成功！")
            print(f"索引包含 {len(indexer.documents)} 个文档块")
        else:
            print("向量索引构建失败")
        
        print("\n向量索引构建工具已就绪") 