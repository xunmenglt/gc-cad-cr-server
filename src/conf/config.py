import os
# 重要配置!!!
# huggingface 配置
HF_ENDPOINT="https://hf-mirror.com"
HF_HOME="/opt/data/private/liuteng/huggingface"

# 唯杰地图API配置
VJMAP_SERVICEURL="https://vjmap.com/server/api/v1"
VJMAP_ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJJRCI6MiwiVXNlcm5hbWUiOiJhZG1pbjEiLCJOaWNrTmFtZSI6ImFkbWluMSIsIkF1dGhvcml0eUlkIjoiYWRtaW4iLCJCdWZmZXJUaW1lIjo4NjQwMCwiZXhwIjo0ODEzMjY3NjM3LCJpc3MiOiJ2am1hcCIsIm5iZiI6MTY1OTY2NjYzN30.cDXCH2ElTzU2sQU36SNHWoTYTAc4wEkVIXmBAIzWh6M"

# 密钥配置
# OPENAI_API_KEY="sk-KlpauS6eTT1cuHck22BaBa8dA1A243569b6740E95c3426E9"
# OPENAI_API_BASE="https://www.gptapi.us/v1"
OPENAI_API_KEY="sk-rhvgwfnxzbxfrusvytxzgshqhzjozulxcvezicbazszrkauj"
OPENAI_API_BASE="https://api.siliconflow.cn/v1"

# VL大模型
VL_MODEL_NAME="Qwen/Qwen2.5-VL-72B-Instruct"

# 代理模型（用于生成真实值）
AGENT_MODEL_NAME="Qwen/Qwen2.5-7B-Instruct"

# 候选答案生成模型
CANDIDATES_GENERATION_MODEL_NAME="Qwen/Qwen2.5-7B-Instruct"

# httpx 配置
HTTPX_DEFAULT_TIMEOUT = 300.0

# 服务运行配置
## 服务运行端口
SERVER_PORT=9890
## 推理服务端口
INFERENCE_PORT=9899
## 各服务器默认绑定host。如改为"0.0.0.0"需要修改下方所有XX_SERVER的host
DEFAULT_BIND_HOST = "0.0.0.0"


# 抽取模型路径
IE_MODEL_PATH="http://localhost:9890/ie_server"

# OCR模型路径
OCR_MODEL_PATH="http://localhost:8777/ocr"

# 数据缓存目录
DATA_TMP_DIR= os.path.join(os.getcwd(),"data/tmp")

# 数据库默认存储路径
DB_ROOT_PATH = os.path.join(
    os.getcwd(),
    "data/sqlite_database/info.db"
)

# 文件系统存储地址
FILE_SYSTEM_ROOT_PATH = os.path.join(
    os.getcwd(),
    "data/file_system"
)

# 数据映射目录
FILE_SYSTEM_MAPPING_DIR = os.path.join(
    os.getcwd(),
    "data/file_system_mapping"
)

# 创建数据库和文件系统存储目录
os.makedirs(os.path.dirname(DB_ROOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(FILE_SYSTEM_ROOT_PATH), exist_ok=True)
os.makedirs(os.path.dirname(FILE_SYSTEM_MAPPING_DIR), exist_ok=True)
os.makedirs(DATA_TMP_DIR, exist_ok=True)

# 打印日志
print(f"HF_HOME: {HF_HOME}")
print(f"HF_ENDPOINT: {HF_ENDPOINT}")
print(f"VJMAP_SERVICEURL: {VJMAP_SERVICEURL}")
print(f"VJMAP_ACCESS_TOKEN: {VJMAP_ACCESS_TOKEN}")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
print(f"OPENAI_API_BASE: {OPENAI_API_BASE}")
print(f"VL_MODEL_NAME: {VL_MODEL_NAME}")
print(f"AGENT_MODEL_NAME: {AGENT_MODEL_NAME}")
print(f"CANDIDATES_GENERATION_MODEL_NAME: {CANDIDATES_GENERATION_MODEL_NAME}")
print(f"HTTPX_DEFAULT_TIMEOUT: {HTTPX_DEFAULT_TIMEOUT}")
print(f"SERVER_PORT: {SERVER_PORT}")
print(f"INFERENCE_PORT: {INFERENCE_PORT}")
print(f"DEFAULT_BIND_HOST: {DEFAULT_BIND_HOST}")
print(f"IE_MODEL_PATH: {IE_MODEL_PATH}")
print(f"OCR_MODEL_PATH: {OCR_MODEL_PATH}")
print(f"DATA_TMP_DIR: {DATA_TMP_DIR}")
print(f"DB_ROOT_PATH: {DB_ROOT_PATH}")
print(f"FILE_SYSTEM_ROOT_PATH: {FILE_SYSTEM_ROOT_PATH}")
print(f"FILE_SYSTEM_ROOT_PATH: {FILE_SYSTEM_ROOT_PATH}")
print("#"*50)


PROJECT_MAPPING={
    "a001深圳国际会展中心": ["a001深圳国际会展中心", "深圳国际会展中心","深圳国际会展中心配套04-02地块"],
    "b001中心区N1区学校": ["b001中心区N1区学校", "中心区N1区学校"],
    "b002合水口人才房学校": ["b002合水口人才房学校", "合水口人才房学校"],
    "b003松岗红星九年_贯制学校": ["b003松岗红星九年_贯制学校", "松岗红星九年_贯制学校","松岗红星九年 贯制学校"],
    "c001深业泰富银盈大厦": ["c001深业泰富银盈大厦", "深业泰富银盈大厦","深业泰富银盈大厦"],
    "c002深圳清华大学研究院新大楼": ["c002深圳清华大学研究院新大楼", "深圳清华大学研究院新大楼"],
    "d001罗湖区体育中心室内网球馆": ["d001罗湖区体育中心室内网球馆", "罗湖区体育中心室内网球馆"],
    "e001北京大学深圳医院深汕医院项目": ["e001北京大学深圳医院深汕医院项目", "北京大学深圳医院深汕医院项目","北京大学深圳医院深汕医院"],
    "f002深圳博物馆项目施工总承包": ["f002深圳博物馆项目施工总承包", "深圳博物馆项目施工总承包"],
    "h001龙华区大浪时尚酒店": ["h001龙华区大浪时尚酒店", "龙华区大浪时尚酒店"],
    "h002万科浪骑游艇会酒店": ["h002万科浪骑游艇会酒店", "万科浪骑游艇会酒店"],
    "j001坪深国际数字物流港项目施工总承包": ["j001坪深国际数字物流港项目施工总承包", "坪深国际数字物流港项目施工总承包","坪深国际数字物流港项目"]
}