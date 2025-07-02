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

# 仪表类型映射配置
INSTRUMENT_TYPE_MAPPING = {
    "WRN": "热电偶",
    "WZP": "热电阻", 
    "WZC": "热电阻",
    "Y": "压力表",
    "YX": "电接点压力表",
    "YE": "膜盒压力表",
    "PT": "压力变送器",
    "TT": "温度变送器",
    "FT": "流量变送器",
    "LT": "液位变送器"
}

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
        "upload_path": UPLOAD_PATH,
        "instrument_type_mapping": INSTRUMENT_TYPE_MAPPING
    } 