import json
from typing import Dict, Any, Optional,List,Literal
from pydantic import BaseModel, Field
from api.base_models import BaseRequestModel, BaseResponseModel
from api.api_module import APIModule
import mimetypes

# 请求模型
class IERequestModel(BaseRequestModel):
    def __init__(self, text: str,entity_type:str,relation:str=None):
        """
        初始化请求模型
        :param text: 输入文本  
        :param entity_type: 实体类型
        :param relation: 关系
        """
        data={
            "text": text,
            "entity_type": entity_type,
            "relation": relation
        }
        super().__init__(data=data)

# 响应模型（根据你的服务实际结构来定）
"""
    "data": [
        {
            "id": "0849daf8-726a-4d1a-879e-ebcc328842cb",
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
"""
class IERestultItem(BaseModel):
    id: str = Field("", description="唯一标识符")
    instruction: str = Field("", description="指令")
    start: List[int] = Field([], description="开始位置")
    end: List[int] = Field([], description="结束位置")
    target: str = Field("", description="目标文本")
    
    def to_dict(self) -> dict:
        return self.model_dump()
    
class IEResponseModel(BaseResponseModel):
    data:List[IERestultItem] = Field([], description="识别结果")
    
    @classmethod
    def from_api_response(cls, raw_json: Dict[str, Any]) -> "IEResponseModel":
        code = raw_json.get("code", -1)
        msg = raw_json.get("msg", json.dumps(raw_json,ensure_ascii=False))
        data = raw_json.get("data", [])
        # 处理 data 字段为 OCRRestultItem 类型
        if isinstance(data, dict):
            data = [IERestultItem(**data)]
        elif isinstance(data, list):
            data = [IERestultItem(**item) for item in data]
        else:
            raise ValueError("Invalid data format")
        return cls(
            code=code,
            msg=msg,
            data=data
        )
    
# 注册 IE 模块
ie_module = APIModule(
    name="ie",
    method="POST",
    url="http://localhost:8999/ie",
    headers={"accept": "application/json","Content-Type": "application/json"},  # multipart/form-data 会自动设置
    request_model=IERequestModel,
    response_model=IEResponseModel
)
