import os
os.environ["CUDA_VISIBLE_DEVICES"] = "5"
import asyncio
import logging
import uvicorn
import json
from typing import List,Union,Optional,AsyncIterable,Awaitable
from fastapi import APIRouter,Body,Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from ie.global_pointer import BertForEffiGlobalPointer
from transformers import AutoTokenizer
from ie.inference import IEAPI
from utils.data import format_predictions
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from config import IE_MODEL_PATH,IE_SERVER_PORT,IE_SERVER_HOST,IE_MAX_CONCURRENT_REQUESTS

class IEItem(BaseModel):
    id: str
    instruction: str
    start: List[int]
    end: List[int]
    target: str
    
class IEResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: List[IEItem] = []
    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": [
                    {
                        "id": "96f0d13b-8211-4ee0-9674-fdba57841806",
                        "instruction": "找到文章中【公司】的【违法法规】？文章：【金融资产管理公司违反金融法律、行政法规的,由中国人民银行依照有关法律和《金融违法行为处罚办法》给予处罚;】",
                        "start": [
                            29
                        ],
                        "end": [
                            40
                        ],
                        "target": "违反金融法律、行政法规"
                    }
                ]
            }
        }
        


# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 全局变量存储模型实例
global_model = {}

# 并发控制配置
MAX_CONCURRENT_REQUESTS = 4  # 最大并发数
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)  # 并发信号量



def initialize_model(model_path: str):
    """初始化模型并缓存到全局变量"""
    logger.info("开始加载模型...")
    
    model_path = os.path.expanduser(model_path)

    try:
        # 初始化组件
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = BertForEffiGlobalPointer.from_pretrained(model_path)
        global_model.update({
            "tokenizer": tokenizer,
            "model": model
        })
        logger.info("模型加载成功")
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise RuntimeError(f"模型初始化失败: {str(e)}")

app = FastAPI(title="IE-Server API", version="1.0")


@app.on_event("startup")
async def startup_event():
    """服务启动时加载模型"""
    try:
        initialize_model(model_path)
        # 打印当前并发设置
        logger.info(f"服务启动完成，最大并发数设置为: {MAX_CONCURRENT_REQUESTS}")
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        raise
    
@app.post("/ie",response_model=IEResponse)
async def process_ie(
    text:str=Body(...,description="被抽取文本"),
    entity_type:str=Body(...,description="实体类型"),
    relation:str=Body("",description="实体之间的关系")
):
        async with request_semaphore:
            logger.info(f"开始处理IE请求 (当前并发数: {MAX_CONCURRENT_REQUESTS - request_semaphore._value}/{MAX_CONCURRENT_REQUESTS})")
            logger.info(f"请求参数: text={text}, entity_type={entity_type}, relation={relation}")

            try:
                model=global_model["model"]
                tokenizer=global_model["tokenizer"]
                hugie=IEAPI(model=model,tokenizer=tokenizer)
                predictions, topk_predictions,instruction=await asyncio.to_thread(
                    hugie.request,
                    text,
                    entity_type,
                    relation
                )
                item=format_predictions(predictions, topk_predictions,instruction)

                return JSONResponse(
                    content={
                        "code": 200,
                        "msg": "success",
                        "data": [item]
                    }
                )
            except Exception as e:
                logger.error(f"处理失败: {str(e)}")
                return JSONResponse(content={
                    "code": 500,
                    "msg": str(e),
                    "data": []
                    }
                )
if __name__ == "__main__":
    # 配置变量
    model_path=IE_MODEL_PATH
    server_port=IE_SERVER_PORT
    server_host=IE_SERVER_HOST
    
    # 从环境变量获取并发数设置，默认为10
    max_concurrent = int(os.getenv("MAX_CONCURRENT_REQUESTS", str(IE_MAX_CONCURRENT_REQUESTS)))
    MAX_CONCURRENT_REQUESTS = max_concurrent
    request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # 启动服务器
    uvicorn.run(
        app,
        host=server_host,
        port=server_port,
        # 调整uvicorn的工作线程数
        workers=1,  # 由于我们使用信号量控制并发，worker数保持为1
        limit_concurrency=MAX_CONCURRENT_REQUESTS+5,  # 设置稍大于我们的并发限制
        timeout_keep_alive=120  # 保持连接时间
    )
