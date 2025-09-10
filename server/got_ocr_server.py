import os
os.environ["CUDA_VISIBLE_DEVICES"] = "6"
import argparse
import logging
import re
import string
from io import BytesIO
from typing import Optional,Literal
import asyncio  # 新增导入

import torch
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from transformers import (AutoTokenizer, CLIPImageProcessor, CLIPVisionModel,
                          StoppingCriteria, TextStreamer)

from GOT.demo.process_results import punctuation_dict, svg_to_html
from GOT.model import *
from GOT.model.plug.blip_process import BlipImageEvalProcessor
from GOT.utils.conversation import SeparatorStyle, conv_templates
from GOT.utils.utils import KeywordsStoppingCriteria, disable_torch_init
from config import OCR_MODEL_PATH,OCR_SERVER_PORT,OCR_SERVER_HOST,OCR_MAX_CONCURRENT_REQUESTS,OCR_DEFAULT_BIND_HOST

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量存储模型实例
global_model = {}
DEFAULT_IMAGE_TOKEN = "<image>"
DEFAULT_IMAGE_PATCH_TOKEN = '<imgpad>'
DEFAULT_IM_START_TOKEN = '<img>'
DEFAULT_IM_END_TOKEN = '</img>'
translation_table = str.maketrans(punctuation_dict)

# 并发控制配置
MAX_CONCURRENT_REQUESTS = 4  # 最大并发数
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)  # 并发信号量

class OCRRequest(BaseModel):
    type:  Literal["ocr","format"]= "ocr"
    box: Optional[str] = None
    color: Optional[str] = None
    render: bool = False


class OCRItem(BaseModel):
    text: str
    html_path: Optional[str] = None
    error: Optional[str] = None

class OCRResponse(BaseModel):
    code:int=200,
    msg:str="success",
    data:OCRItem=[]
    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": 
                    {
                        "text": "识别的文本",
                        "html_path": "./results/demo.html"
                    }
            }
        }
    

def initialize_model(model_path: str):
    """初始化模型并缓存到全局变量"""
    logger.info("开始加载模型...")
    
    disable_torch_init()
    model_path = os.path.expanduser(model_path)

    try:
        # 初始化组件
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = GOTQwenForCausalLM.from_pretrained(
            model_path,
            low_cpu_mem_usage=True,
            device_map='cuda',
            use_safetensors=True,
            pad_token_id=151643
        ).eval().to(dtype=torch.bfloat16)
        
        image_processor = BlipImageEvalProcessor(image_size=1024)
        image_processor_high = BlipImageEvalProcessor(image_size=1024)

        global_model.update({
            "tokenizer": tokenizer,
            "model": model,
            "processor": image_processor,
            "processor_high": image_processor_high
        })
        logger.info("模型加载成功")
    except Exception as e:
        logger.error(f"模型加载失败: {str(e)}")
        raise RuntimeError(f"模型初始化失败: {str(e)}")

app = FastAPI(title="GOT-OCR API", version="1.0")

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

async def process_image_file(file: UploadFile):
    """处理上传的图片文件"""
    try:
        content = await file.read()
        image = Image.open(BytesIO(content)).convert('RGB')
        return image
    except Exception as e:
        logger.error(f"图片处理失败: {str(e)}")
        raise HTTPException(status_code=400, detail="无效的图片文件")

def generate_output(
    image: Image.Image,
    request_params: OCRRequest
) -> str:
    """执行模型推理"""
    conv_mode = "mpt"
    conv = conv_templates[conv_mode].copy()
    tokenizer = global_model["tokenizer"]
    
    # 构建查询字符串
    w, h = image.size
    qs = 'OCR with format: ' if request_params.type == 'format' else 'OCR: '

    if request_params.box:
        bbox = eval(request_params.box)
        # 边界框处理逻辑...
        qs = f"{bbox} {qs}"

    if request_params.color:
        qs = f"[{request_params.color}] {qs}"

    # 添加图像token
    qs = f"{DEFAULT_IM_START_TOKEN}{DEFAULT_IMAGE_PATCH_TOKEN*256}{DEFAULT_IM_END_TOKEN}\n{qs}"
    
    # 构建对话prompt
    conv.append_message(conv.roles[0], qs)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()
    logger.debug(f"生成prompt: {prompt}")

    # 预处理图像
    image_tensor = global_model["processor"](image).unsqueeze(0).half().cuda()
    image_tensor_high = global_model["processor_high"](image).unsqueeze(0).half().cuda()

    # 生成输入
    inputs = tokenizer([prompt])
    input_ids = torch.as_tensor(inputs.input_ids).cuda()

    # 设置停止条件
    stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
    stopping_criteria = KeywordsStoppingCriteria([stop_str], tokenizer, input_ids)

    # 执行推理
    with torch.autocast("cuda", dtype=torch.bfloat16):
        output_ids = global_model["model"].generate(
            input_ids,
            images=[(image_tensor, image_tensor_high)],
            do_sample=False,
            num_beams=1,
            max_new_tokens=4096,
            stopping_criteria=[stopping_criteria]
        )

    # 解码输出
    outputs = tokenizer.decode(output_ids[0, input_ids.shape[1]:],skip_special_tokens=True).strip()
    if outputs.endswith(stop_str):
        outputs = outputs[:-len(stop_str)]
    
    return outputs.strip()

def process_rendering(outputs: str, render: bool) -> Optional[str]:
    """处理结果渲染"""
    if not render:
        return None

    try:
        if '**kern' in outputs:
            # 音乐符号渲染逻辑...
            return "./results/demo.html"
        elif '\\begin{tikzpicture}' in outputs:
            # 图表渲染逻辑...
            return "./results/demo.html"
    except Exception as e:
        logger.error(f"渲染失败: {str(e)}")
    
    return None

@app.post("/ocr", response_model=OCRResponse)
async def process_ocr(
    file: UploadFile = File(...),
):
    request_params: OCRRequest = OCRRequest()
    """OCR处理接口，带并发控制"""
    # 等待获取信号量，如果并发数已满则等待
    async with request_semaphore:
        logger.info(f"开始处理OCR请求 (当前并发数: {MAX_CONCURRENT_REQUESTS - request_semaphore._value}/{MAX_CONCURRENT_REQUESTS})")
        logger.info(f"请求参数 - 类型: {request_params.type}, 渲染: {request_params.render}")

        try:
            # 1. 处理输入图片
            image = await process_image_file(file)
            
            # 2. 执行模型推理
            outputs = await asyncio.to_thread(generate_output, image, request_params)
            
            # 3. 处理结果渲染
            html_path = process_rendering(outputs, request_params.render)

            return JSONResponse(content={
                    "code":200,
                    "data":{
                        "text": outputs,
                        "html_path": html_path
                    },
                    "msg": "success"
                }
            )

        except HTTPException:
            raise  # 直接抛出已有的HTTP异常
        except Exception as e:
            logger.error(f"处理失败: {str(e)}", exc_info=True)
            return JSONResponse(content={
                    "code": 500,
                    "msg": f"处理失败: {str(e)}",
                    "data": None
                }
            )
        finally:
            logger.info("请求处理完成，释放并发槽")

if __name__ == "__main__":
    # 全局变量
    model_path = OCR_MODEL_PATH
    server_port=OCR_SERVER_PORT
    server_host=OCR_SERVER_HOST
    
    # 从环境变量获取并发数设置，默认为4
    max_concurrent = int(os.getenv("MAX_CONCURRENT_REQUESTS", str(OCR_MAX_CONCURRENT_REQUESTS)))
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