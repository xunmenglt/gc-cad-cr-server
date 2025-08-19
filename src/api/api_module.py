from typing import Type,Callable,Optional,Dict
from pydantic import BaseModel
import requests
from api.base_models import BaseRequestModel, BaseResponseModel


# 定义接口调用函数签名
class APIModule:
    def __init__(
        self,
        name:str,
        method: str,
        url: str,
        request_model: Type[BaseRequestModel],
        response_model: Type[BaseResponseModel],
        headers: Optional[Dict[str, str]] = None,
        call_fun:Callable=None
    ):
        self.name=name
        self.method=method
        self.url=url
        self.request_model=request_model
        self.response_model=response_model
        self.call_fun=call_fun or self._default_call_fun
        self.headers = headers or {}
    
    def call(self, params: dict):
        """
        调用接口
        :param params: 接口参数
        :return: 接口响应
        """
        return self.call_fun(self, params)
    def send_request(self, method, url, headers=None, params=None, data=None, files=None):
        """
        通用请求方法
        :param method: HTTP 方法 (GET, POST, PUT, DELETE)
        :param url: API 接口地址
        :param headers: 请求头
        :param params: 查询参数
        :param data: 请求体
        :param files: 上传文件
        :return: 响应数据
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                files=files
            )
            response.encoding="utf-8"
            response.raise_for_status()
            return response.json()  # 返回 JSON 格式响应
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    def _default_call_fun(self,module:"APIModule", params: Dict) -> BaseResponseModel:
        validated_params = module.request_model(**params)
        response = self.send_request(
            method=module.method,
            url=module.url,
            headers=module.headers,
            params=validated_params.params,
            data=validated_params.data,
            files=validated_params.files
        )
        return module.response_model.from_api_response(response)
    
        

