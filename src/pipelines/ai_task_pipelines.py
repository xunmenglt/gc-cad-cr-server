import json
import hashlib
from abc import ABC, abstractmethod
from typing import Iterable,List,Dict,Literal,Tuple
from jinja2 import Template
from utils.openai import openai_chat_by_api,ChatCompletionMessageParam
from pipelines.base import PipeLine
from common.prompts import (field_requiring_classification_prompt_template,
                            field_directed_prompt_template,
                            address_search_template,
                            building_area_extraction_prompt,
                            structure_type_extraction_prompt,
                            service_life_extraction_prompt,
                            earthquake_level_extraction_prompt,
                            building_fortification_intensity_prompt,
                            charger_count_extraction_prompt,
                            parking_space_count_extraction_prompt,
                            land_area_prompt_template,
                            building_height_with_refcontent_prompt,
                            building_standard_height_with_refcontent_prompt)
from extraction.context import DwgFileContext,FacadeContext
from utils.file import image_chat
from vjmap.services import (
    MapPngByBoundsService,
    MapPngByBoundsParams
)
from typing import Any
from conf.config import CANDIDATES_GENERATION_MODEL_NAME


class BaseLanguageModelTaskPipeLine(PipeLine,ABC):
    def __init__(self,model_name="gpt-4o-mini"):
        self.model_name=model_name

    
    def single_complete(self,query,temperature=0.7,max_tokens=1024):
        ai_res=openai_chat_by_api(
            model_name=self.model_name,
            messages=[{
                    "role":"user",
                    "content":query
            }],
            inference_params={
                "temperature":temperature,
                "max_tokens":max_tokens
            }
        )
        return ai_res
    
    @abstractmethod
    def create_query(self):
        """构建query"""
        pass
    

class ExtractionCategorizedTaskPipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self, field_name:str,content:str,classifications:List[str],model_name="gpt-4o-mini"):
        super().__init__(model_name)
        self.field_name=field_name
        self.content=content
        self.classifications=classifications
    
    def create_query(self):
        template=Template(field_requiring_classification_prompt_template)
        query=template.render(
            {
                "content":self.content,
                "classifications":self.classifications,
                "field_name":self.field_name
            }
        )
        return query
    
    def invoke(self)->str:
        query=self.create_query()
        ai_res=self.single_complete(query=query)
        for classification in self.classifications:
            if classification in ai_res:
                return classification
        return None
    
class ExtractionFieldValueTaskBaseLanguageModelPipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self, field_name:str,content:str,alias:List[str]=[],model_name="gpt-4o-mini"):
        super().__init__(model_name)
        self.field_name=field_name
        self.content=content
        self.alias=alias
    
    def create_query(self):
        template=Template(field_directed_prompt_template)
        keys=[self.field_name]+self.alias
        content=self.content.replace("2\r\n","\r\n")
        query=template.render(
            {
                "content":content,
                "keys":keys
            }
        )
        return query
    
    def parse_ai_res_for_field_directed(self,ai_res:str):
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        data=json.loads(ai_res.strip())
        if data.get("extract_content"):
            return data["extract_content"]
        return None

    def invoke(self)->str:
        query=self.create_query()
        ai_res=self.single_complete(query=query)
        field_value=self.parse_ai_res_for_field_directed(ai_res=ai_res)
        return field_value
class LandAreaFieldValueTaskLanguageModelPipeLine(ExtractionFieldValueTaskBaseLanguageModelPipeLine):
    def create_query(self):
        template=Template(land_area_prompt_template)
        keys=[self.field_name]+self.alias
        content=self.content.replace("2\r\n","\r\n")
        query=template.render(
            {
                "content":content,
                "keys":keys
            }
        )
        return query
# 抽取充电桩数量
class ChargerCountExtractionPipeLine(ExtractionFieldValueTaskBaseLanguageModelPipeLine):
    def create_query(self):
        template=Template(charger_count_extraction_prompt)
        keys=[self.field_name]+self.alias
        content=self.content.replace("2\r\n","\r\n")
        query=template.render(
            {
                "content":content,
                "keys":keys
            }
        )
        return query

# 停车位数量
class ParkingSpaceCountExtractionPipeLine(ExtractionFieldValueTaskBaseLanguageModelPipeLine):
    def create_query(self):
        template=Template(parking_space_count_extraction_prompt)
        keys=[self.field_name]+self.alias
        content=self.content.replace("2\r\n","\r\n")
        query=template.render(
            {
                "content":content,
                "keys":keys
            }
        )
        return query

class AddressParsePipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self, address:str,model_name="gpt-4o-mini"):
        super().__init__(model_name)
        self.address=address
    
    def create_query(self):
        template=Template(address_search_template)
        query=template.render(
            {
                "address":self.address
            }
        )
        return query
    
    def parse_ai_res_for_field_directed(self,ai_res:str)->Tuple[str]:
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        ai_res=ai_res.replace("`","")
        ai_res=ai_res.replace("json","")
        data=json.loads(ai_res.strip())
        if data and len(data)>0:
            return (data["province"],data["city"],data["county"]) 
        return None

    def invoke(self)->str:
        query=self.create_query()
        ai_res=self.single_complete(query=query)
        values=self.parse_ai_res_for_field_directed(ai_res=ai_res)
        if values:
            values = "".join(values)
        return values
    
    
class FloorAreaExtractionPipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self, field_name:str,ref_contexts:List[str],model_name="gpt-4o-mini"):
        super().__init__(model_name)
        self.field_name=field_name
        self.ref_contexts=ref_contexts
    
    def create_query(self):
        template=Template(building_area_extraction_prompt)
        query=template.render(
            {
                "field_name":self.field_name,
                "ref_context":'\n'.join(self.ref_contexts)
            }
        )
        return query
    
    def parse_ai_res_for_field_directed(self,ai_res:str)->float:
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        ai_res=ai_res.replace("`","")
        ai_res=ai_res.replace("json","")
        if not ai_res:
            return 0.0
        
        try:
            data=json.loads(ai_res.strip())
        except json.JSONDecodeError:
            return 0.0
        
        if data and len(data)>0:
            return float(data["area"])
        return 0.0

    def invoke(self)->float:
        query=self.create_query()
        ai_res=self.single_complete(query=query)
        value=self.parse_ai_res_for_field_directed(ai_res=ai_res)
        value=round(value, 2)
        return value



class BaseGeneralBusinessExtractionPipeLine(BaseLanguageModelTaskPipeLine):
   
    def __init__(self, field_name:str,ref_contexts:List[str],model_name="gpt-4o-mini"):
        super().__init__(model_name)
        self.field_name=field_name
        self.ref_contexts=ref_contexts
    
    def _get_prompt(self):
        raise NotImplementedError("子类必须实现该方法")
    def _get_value_key(self):
        raise NotImplementedError("子类必须实现该方法")
    
    def create_query(self):
        template=Template(self._get_prompt())
        query=template.render(
            {
                "field_name":self.field_name,
                "ref_context":'\n'.join(self.ref_contexts)
            }
        )
        return query
    
    def parse_ai_res_for_field_directed(self,ai_res:str)->float:
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        ai_res=ai_res.replace("`","")
        ai_res=ai_res.replace("json","")
        data=json.loads(ai_res.strip())
        if data and len(data)>0:
            return data[self._get_value_key()]
        return None
    
    def invoke(self):
        query=self.create_query()
        try:
            ai_res=self.single_complete(query=query)
        except Exception as e:
            print(f"AI请求失败: {str(e)}")
            return None
        try:
            value=self.parse_ai_res_for_field_directed(ai_res=ai_res)
        except Exception as e:
            print(f"【{self.field_name}】模型解析异常")
            value="模型输出结果解析异常"
        return value
    
class StructureTypeExtractionPipeLine(BaseGeneralBusinessExtractionPipeLine):
    def __init__(self, alias:List[str],**kwargs):
        super().__init__(**kwargs)
        self.keys=[self.field_name]+alias
    def _get_prompt(self):
        return structure_type_extraction_prompt
    def create_query(self):
        template=Template(self._get_prompt())
        query=template.render(
            {
                "keys":self.keys,
                "ref_context":'\n'.join(self.ref_contexts)
            }
        )
        return query
    def _get_value_key(self):
        return "structure_type"

class ServiceLifeExtractionPipeLine(BaseGeneralBusinessExtractionPipeLine):
    def _get_prompt(self):
        return service_life_extraction_prompt
    
    def _get_value_key(self):
        return "service_life"
    
class EarthquakeLevelExtractionPipeLine(BaseGeneralBusinessExtractionPipeLine):
    def _get_prompt(self):
        return earthquake_level_extraction_prompt
    
    def _get_value_key(self):
        return "earthquake_level"

class BuildingFortificationIntensityExtractionPipeLine(BaseGeneralBusinessExtractionPipeLine):
    def _get_prompt(self):
        return building_fortification_intensity_prompt
    
    def _get_value_key(self):
        return "building_fortification_intensity"
    
"""
class BaseLanguageModelTaskPipeLine(PipeLine,ABC):
    def __init__(self,model_name="gpt-4o-mini"):
        self.model_name=model_name

    
    def single_complete(self,query,temperature=0.7,max_tokens=1024):
        ai_res=openai_chat_by_api(
            model_name=self.model_name,
            messages=[{
                    "role":"user",
                    "content":query
            }],
            inference_params={
                "temperature":temperature,
                "max_tokens":max_tokens
            }
        )
        return ai_res
    
    @abstractmethod
    def create_query(self):
        pass
"""

class HeightParsePipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self, file_context:DwgFileContext,facade_context:FacadeContext,building_model_name:str,**kwargs):
        super().__init__(**kwargs)
        self.file_context=file_context
        self.facade_context=facade_context
        self.building_model_name=building_model_name
        
    def _get_value_key(self):
        return "building_height"
    
    def create_image(self):
        mapPngByBoundsService=MapPngByBoundsService(self.file_context.mapid)
        url=mapPngByBoundsService.map_to_img_url(params=MapPngByBoundsParams(
            width=4096,
            bbox=self.facade_context.submap.to_str()
        ))
        image_name=f"{self.file_context.mapid}_{hashlib.md5(self.facade_context.submap.to_str().encode()).hexdigest()}.png"
        end_save_dir=f"data/images/{self.file_context.mapid}"
        image_path=mapPngByBoundsService.url_to_img(img_url=url,image_name=image_name,save_dir=end_save_dir)
        return image_path
    
    def create_query(self):
        template=Template(building_height_with_refcontent_prompt)
        query=template.render(
            {
                "building_model_name":self.building_model_name,
                "content":repr(self.facade_context)
            }
        )
        return query
    
    def parse_ai_res_for_field_directed(self,ai_res:str)->float:
        ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
        ai_res=ai_res.replace("`","")
        ai_res=ai_res.replace("json","")
        data=json.loads(ai_res.strip())
        if data and len(data)>0:
            return data.get(self._get_value_key(),-1)
        return None
    
    
    def invoke(self):
        image=self.create_image()
        query=self.create_query()
        ai_res=image_chat(image,query)
        res=self.parse_ai_res_for_field_directed(ai_res)
        try:
            value = float(res)
        except Exception as e:
            value = -1
        return value
    
class StandardHeightParsePipeLine(HeightParsePipeLine):
    def _get_value_key(self):
        return "floor_height"

    def create_query(self):
        template=Template(building_standard_height_with_refcontent_prompt)
        query=template.render(
            {
                "building_model_name":self.building_model_name,
                "content":repr(self.facade_context)
            }
        )
        return query
    
# ======================= 下面是候选答案生成 =======================
class CandidatesGenerationPipeLine(BaseLanguageModelTaskPipeLine):
    def __init__(self,
                 model_name=CANDIDATES_GENERATION_MODEL_NAME,
                 temperature=0.7,
                 max_tokens=4096,
                 prompt:str="",
                 prompt_params:Dict[str,Any]={},
                 **kwargs):
        super().__init__(**kwargs)
        self.model_name=model_name
        self.prompt=prompt
        self.prompt_params=prompt_params
        self.temperature=temperature
        self.max_tokens=max_tokens
    
    def single_complete(self,query,temperature=0.7,max_tokens=4096):
        ai_res=openai_chat_by_api(
            model_name=self.model_name,
            messages=[{
                    "role":"user",
                    "content":query
            }],
            inference_params={
                "temperature":temperature,
                "max_tokens":max_tokens
            }
        )
        return ai_res
    
    def create_query(self):
        template=Template(self.prompt)
        query=template.render(
            self.prompt_params
        )
        return query
    
    def parse_ai_res(self,ai_res:str)->List[str]:
        try:
            ai_res=ai_res.split("<output>")[-1].split("</output>")[0]
            ai_res=ai_res.replace("`","")
            ai_res=ai_res.replace("json","")
            data=json.loads(ai_res.strip())
            if data and len(data)>0 and "candidates" in data:
                return data["candidates"]
        except json.JSONDecodeError:
            return []
    
    def invoke(self):
        query=self.create_query()
        ai_res=self.single_complete(query=query,temperature=self.temperature,max_tokens=self.max_tokens)
        candidates=self.parse_ai_res(ai_res=ai_res)
        return candidates