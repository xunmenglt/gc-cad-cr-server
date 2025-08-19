from typing import Dict, Callable, Optional, Type
from api.api_module import APIModule

class APICaller:
    def __init__(self):
        self.registry:Dict[str, APIModule] = {}
        
    def register_module(self, module: APIModule):
        """
        注册 API 模块
        :param module: APIModule 实例
        """
        if module.name in self.registry:
            raise ValueError(f"Module {module.name} is already registered.")
        self.registry[module.name] = module

    def call(self, module_name: str, params: dict):
        """
        调用注册的 API 模块
        :param module_name: 模块名称
        :param params: 接口参数
        :return: 接口响应
        """
        if module_name not in self.registry:
            raise ValueError(f"Module {module_name} is not registered.")
        
        module = self.registry[module_name]
        return module.call(params)