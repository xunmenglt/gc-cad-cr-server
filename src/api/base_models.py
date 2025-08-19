from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BaseRequestModel(BaseModel):
    """
    基础请求参数模型
    """
    params: dict = Field(default_factory=dict, description="请求参数")
    data: dict = Field(default_factory=dict, description="data请求体")
    files: dict = Field(default_factory=dict, description="上传文件")

class BaseResponseModel(BaseModel):
    """
    基础响应模型
    """
    code: int = Field(200, description="API状态码")
    msg: str = Field("success", description="API状态信息")
    data: Any = Field(None, description="API数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
            }
        }
    
    @classmethod
    def from_api_response(cls, raw_json: Dict[str, Any]) -> "OCRResponseModel":
        code = raw_json.get("code", -1)
        msg = raw_json.get("msg", None)  # 有的接口可能没有 msg 字段
        data = raw_json.get("data", {})
        return cls(
            code=code,
            msg=msg,
            data=data
        )