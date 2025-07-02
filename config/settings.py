"""
项目配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 模型配置
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "shibing624/text2vec-base-chinese")

# 向量数据库配置
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./data/indexes/instrument_standards.index")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))

# 文件路径配置
STANDARDS_DATA_PATH = os.getenv("STANDARDS_DATA_PATH", "./data/standards/")
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "./data/uploads/")



def get_openai_config():
    """获取OpenAI配置"""
    return {
        "api_key": OPENAI_API_KEY,
        "base_url": OPENAI_BASE_URL,
        "model": LLM_MODEL
    }

def get_settings():
    """获取所有配置设置"""
    return {
        "openai_api_key": OPENAI_API_KEY,
        "openai_base_url": OPENAI_BASE_URL,
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "faiss_index_path": FAISS_INDEX_PATH,
        "vector_dimension": VECTOR_DIMENSION,
        "standards_data_path": STANDARDS_DATA_PATH,
        "upload_path": UPLOAD_PATH
    } 