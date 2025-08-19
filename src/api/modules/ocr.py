import json
from typing import Dict, Any, Optional,List
from pydantic import BaseModel, Field
from api.base_models import BaseRequestModel, BaseResponseModel
from api.api_module import APIModule
import mimetypes
from conf.config import OCR_MODEL_PATH

# 请求模型
class OCRRequestModel(BaseRequestModel):
    def __init__(self, file_path: str):
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"
        files = {
            "file": (file_path, open(file_path, "rb"), mime_type)
        }
        super().__init__(files=files)

# 响应模型（根据你的服务实际结构来定）
class OCRRestultItem(BaseModel):
    text: str = Field("", description="识别的文本内容")
    html_path: Optional[str] = Field("", description="识别的置信度")
    
class OCRResponseModel(BaseResponseModel):
    data:OCRRestultItem = Field(None, description="识别结果")
    
    @classmethod
    def from_api_response(cls, raw_json: Dict[str, Any]={},**kwargs) -> "OCRResponseModel":
        code = raw_json.get("code", 500)
        msg = raw_json.get("msg") or json.dumps(raw_json, ensure_ascii=False)
        data = raw_json.get("data", {})
        # 处理 data 字段为 OCRRestultItem 类型
        if isinstance(data, dict):
            data = OCRRestultItem(**data)
        elif isinstance(data, list):
            data = [OCRRestultItem(**item) for item in data]
        else:
            raise ValueError("Invalid data format")
        return cls(
            code=code,
            msg=msg,
            data=data
        )

# 注册 OCR 模块
ocr_module = APIModule(
    name="ocr",
    method="POST",
    url=OCR_MODEL_PATH,
    headers={"accept": "application/json"},  # multipart/form-data 会自动设置
    request_model=OCRRequestModel,
    response_model=OCRResponseModel
)
