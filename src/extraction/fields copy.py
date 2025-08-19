import re
import tqdm
from lxml import etree
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from abc import ABC, abstractmethod
from dataclasses import dataclass,field,asdict
from typing import List,Literal,Optional,Union,Dict,Tuple,Any
from extraction.context import ContextScope,ProjectContext,BaseFileContext,DwgFileContext,BusinessModelItem
from pipelines.ai_task_pipelines import (ExtractionCategorizedTaskPipeLine,
                                         ExtractionFieldValueTaskBaseLanguageModelPipeLine,
                                         AddressParsePipeLine,
                                         FloorAreaExtractionPipeLine,
                                         ServiceLifeExtractionPipeLine,
                                         StructureTypeExtractionPipeLine,
                                         EarthquakeLevelExtractionPipeLine,
                                         BuildingFortificationIntensityExtractionPipeLine,
                                         ChargerCountExtractionPipeLine,
                                         ParkingSpaceCountExtractionPipeLine,
                                         LandAreaFieldValueTaskLanguageModelPipeLine,
                                         HeightParsePipeLine,
                                         StandardHeightParsePipeLine)
from utils.address import parse_regions,get_level_by_city
from api.modules import api_caller
from api.modules.ocr import OCRResponseModel
from api.modules.ie import IEResponseModel
from pipelines.fileparse_pipelines import DwgTextParsePipeLine
from pipelines.cut_off_pipelines import DwgImageCatOffPipeLine
from splitter.cad_splitter import TitleBelowTableSplitter
from vjmap.items import (
    QueryItem
)
from utils.data import is_number
from utils.file import image_to_text


@dataclass
class ContentItem:
    content:str=field(default="")
    ie_info:Optional[Dict]=field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls,item):
        return cls(
            **item
        )
        

@dataclass
class OcrItem:
    image_path:str=field(default="")
    content:Optional[str]=field(default="")
    
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls,item):
        return cls(
            **item
        )



@dataclass
class ReferenceData:
    texts:List[ContentItem]=field(default_factory=list)
    ocrs:List[OcrItem]=field(default_factory=list)
    
    def to_dict(self):
        result = asdict(self)
        if isinstance(self.texts,list) and all(isinstance(t,ContentItem) for t in self.texts):
            result["texts"]=[t.to_dict() for t in self.texts]
        if isinstance(self.ocrs,list) and all(isinstance(o,OcrItem) for o in self.ocrs):
            result["ocrs"]=[o.to_dict() for o in self.ocrs]
        return result
    
    @classmethod
    def from_dict(cls,item):
        texts=item['texts']
        if isinstance(texts,list) and all(isinstance(t,dict) for t in texts):
            item["texts"]=[ContentItem.from_dict(t) for t in texts]
        ocrs=item['ocrs']
        if isinstance(ocrs,list) and all(isinstance(o,dict) for o in ocrs):
            item["ocrs"]=[OcrItem.from_dict(o) for o in texts]
        return cls(
            **item
        )

class Field(ABC):
    def __init__(self,
                 name:str,
                 alias:List[str]=[],
                 dependencies:List[str]=[],
                 default_value:Union[str,float,int,dict]=None,
                 context_scope:List[ContextScope]=[],
                 is_hidden:bool=False,
                 is_use_ocr:bool=False,
                 is_use_ie:bool=False,
                 field_id:str=None,
                 is_general=True):
        self.name=name # 字段名称
        self.alias=alias # 字段别名，可多个
        self.dependencies=dependencies # 字段依赖项
        self.default_value=default_value # 字段默认值
        self.context_scope=context_scope # 上下文范围
        self.is_hidden=is_hidden # 是否隐藏字段
        self.value=None # 存贮的值
        self.ref_data:ReferenceData=ReferenceData() # 参考数据
        self.is_use_ocr=is_use_ocr
        self.is_use_ie=is_use_ie
        self.is_general=is_general
        self.field_id=field_id
        
    
    @abstractmethod
    def _extract_field_value(self,context:ProjectContext):
        """根据上下文完成字段解析"""
        pass

    def extract_surrounding_text(self,text,key,pre_len=10,post_len=50)->List[str]:
        matches=re.finditer(re.escape(key), text)  # 查找所有匹配的 key
        results = [
            text[max(0, match.start() - pre_len): min(len(text), match.end() + post_len)]
            for match in matches
        ]
        return results
    
    
    def _post_process(self):
        return self.value
    
    def parse(self, context,**kwargs):
        if self.value:
            return self.value
        self.value=self._extract_field_value(context=context)
        self.value=self._post_process()
        
        if kwargs.get("pd"):
            kwargs["pd"].update(1)
            kwargs["pd"].desc=f"正在抽取【{self.name}】"
            
        if self.value:
            return self.value
        else:
            return self.default_value

    
    def ie_filter(self,contents: List[str]) -> Tuple[List, List]:
        if not self.is_use_ie:
            self.ref_data.texts = [
                ContentItem(content=content, ie_info=None)
                for content in contents
            ]
            return contents, []

        if not contents:
            return [], []

        filted_contents = []
        ie_results = []
        key=self.name
        def call_ie(content: str):
            res: IEResponseModel = api_caller.call(
                "ie",
                {
                    "text": content,
                    "entity_type": key,
                    "relation": ""
                }
            )
            return content, res

        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_content = {executor.submit(call_ie, content): content for content in contents}
            for future in tqdm.tqdm(as_completed(future_to_content), total=len(contents), desc=f"IE过滤中【{key}】"):
                content, res = future.result()
                if res.data and len(res.data) > 0:
                    data = res.data[0]
                    if data.target and data.target.strip():
                        filted_contents.append(content)
                        ie_results.append(data.to_dict())

        self.ref_data.texts = [
            ContentItem(content=content, ie_info=ie_info)
            for content, ie_info in zip(filted_contents, ie_results)
        ]

        print(f"IE模型过滤详情:{len(filted_contents)}/{len(contents)}")
        
        return filted_contents, ie_results
            
    
    def ocr_check(self,dwg_context:DwgFileContext,p_height=1.0,p_width=1.0,scale=1.02)->Tuple[List,List]:
        if not self.is_use_ocr:
            return [],[]
        keys=[self.name]+self.alias
        cutoff_tool=DwgImageCatOffPipeLine(dwg_context)
        cut_result=cutoff_tool.invoke(keys=keys,p_height=p_height,p_width=p_width,scale=scale)
        ocr_images=[]
        ocr_contents=[]
        count=0
        for key in cut_result:
            for image_path in tqdm.tqdm(cut_result[key],desc=f'当前OCR识别字段【{key}】'):
                count+=1
                content=image_to_text(image_path)
                if content:
                    ocr_images.append(image_path)
                    ocr_contents.append(content)
                # res:OCRResponseModel=api_caller.call("ocr",{"file_path":image_path})
                # if res.data and res.data.text:
                #     ocr_images.append(image_path)
                #     ocr_contents.append(res.data.text)
        self.ref_data.ocrs = [
            OcrItem(content=content, image_path=image_path)
            for content, image_path in zip(ocr_contents, ocr_images)
        ]
        print(f"OCR成功识别详情：{len(ocr_images)}/{count}")
        return ocr_images,ocr_contents
                
        
        
        
            
        
        




class BaseCategorizedField(Field):
    """基础的具有类别的字段"""
    def __init__(self, name, alias = [], dependencies = [], paragraph_keys=[],default_value = None, context_scope = [],
                 classifications:List[str]=[],
                 classification_map:Dict={},
                 classification_prefix:str="",
                 classification_suffix:str="",
                 agent_model_name="gpt-4o-mini",
                 is_use_ocr:bool=False,
                 is_use_ie:bool=False
                ):        
        super().__init__(name, alias, dependencies, default_value, context_scope,is_use_ie=is_use_ie,is_use_ocr=is_use_ocr)
        self.classifications=classifications # 类别限定列表
        self.classification_map=classification_map # 类别名称映射
        self.classification_prefix=classification_prefix # 类别前缀
        self.classification_suffix=classification_suffix # 类别后缀
        self.agent_model_name=agent_model_name
        self.paragraph_keys=paragraph_keys
        
    
    def most_common_element(self,lst):
        count = Counter(lst)
        most_common = count.most_common(1)  # 获取出现最多的元素
        return most_common[0] if most_common else None
    
    def _extract_field_value(self,context:ProjectContext):
        """
        抽取需要被分类的字段
        """
        value=None
        field_name=self.name
        classifications=self.classifications
        context_scope=self.context_scope
        alias=self.alias
        
        matched_paragraphs=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph['title']:
                                matched_paragraphs.append(paragraph['content'])
                                break
        # 首先直接根据分类列表在原文本中进行匹配
        if matched_paragraphs and len(matched_paragraphs)>0:
            content='\n'.join(matched_paragraphs)[:4096]
            pipeline=ExtractionCategorizedTaskPipeLine(
                field_name=field_name,
                content=content,
                classifications=classifications,
                model_name=self.agent_model_name
            )
            value=pipeline.invoke()
        else:
            matched_classifications=[]
            for scope in context_scope:
                # TODO 需要优化，目前只获取上下文中的文件内容列表，如果是dwg为表格的内容没有获取
                contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
                contents=[]
                for file_context in contexts:
                    text_content_list=file_context.text_content_list
                    table_content_list=[]
                    if isinstance(file_context,DwgFileContext):
                        table_content_list=file_context.table_content_list
                    contents.extend(table_content_list)
                    contents.extend(text_content_list)
                for classification in classifications:
                    for content in contents:
                        count=content.count(classification)
                        for _ in range(count):
                            matched_classifications.append(classification)
            if matched_classifications and len(matched_classifications)>0:
                value,count=self.most_common_element(matched_classifications)
            else:
                # 根据key_name和alias获取文本相关片段，让大模型进行判断
                matched_str_list=[]
                for scope in context_scope:
                    # TODO 需要优化，目前只获取上下文中的文件内容列表，如果是dwg为表格的内容没有获取
                    contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
                    contents=[]
                    for file_context in contexts:
                        text_content_list=file_context.text_content_list
                        table_content_list=[]
                        if isinstance(file_context,DwgFileContext):
                            table_content_list=file_context.table_content_list
                        contents.extend(table_content_list)
                        contents.extend(text_content_list)
                    for content in contents:
                        matched_str_list=self.extract_surrounding_text(content,field_name)
                    if not matched_str_list or len(matched_str_list)<=0:
                        for content in contents:
                            for alia in alias:
                                str_list=self.extract_surrounding_text(content,alia)
                                matched_str_list.extend(str_list)
                content='\n'.join(matched_str_list)[:512]
                pipeline=ExtractionCategorizedTaskPipeLine(
                    field_name=field_name,
                    content=content,
                    classifications=classifications,
                    model_name=self.agent_model_name
                )
                value=pipeline.invoke()
        if not value:
            return self.default_value
        value=self.classification_map.get(value,value)
        value=value.strip(self.classification_prefix)
        value=value.strip(self.classification_suffix)
        return self.classification_prefix+value+self.classification_suffix
    


class BaseValueField(Field):
    def __init__(self, name, alias = [], dependencies = [], default_value = None, context_scope = [],return_type="str",agent_model_name:str="gpt-4o-mini",is_hidden:bool=False,is_use_ocr=False,is_use_ie=False,p_height=1.0,p_width=2.0):
        super().__init__(name=name, alias=alias, dependencies=dependencies, default_value=default_value, context_scope=context_scope,is_hidden=is_hidden,is_use_ocr=is_use_ocr,is_use_ie=is_use_ie)
        self.agent_model_name=agent_model_name
        self.return_type=return_type
        self.p_width=p_width
        self.p_height=p_height
    """基础的 字段-值"""
    def _extract_field_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        matched_str_list=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            if contexts is None or len(contexts)<=0:
                continue
            contents=[]
            for file_context in contexts:
                text_content_list=file_context.text_content_list
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                contents.extend(table_content_list)
                contents.extend(text_content_list)
                if isinstance(file_context,DwgFileContext):
                    if file_context.text_list:
                        ocr_images,ocr_contents=self.ocr_check(file_context,p_width=self.p_width,p_height=self.p_height)
                        contents.extend(ocr_contents)
            for content in contents:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    matched_str_list.extend(str_list)
        matched_str_list,ie_results=self.ie_filter(matched_str_list)
        content="\n".join(matched_str_list)
        if not content.strip():
            value="数据中无该字段对应值"
        else:
            pipline=ExtractionFieldValueTaskBaseLanguageModelPipeLine(
                field_name=field_name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()
        return value
    
    def _post_process(self):
        if not self.value:
            return None
        if self.return_type=="number":
            self.value=''.join(re.findall(r'\d+', self.value))
        elif self.return_type=="str" and isinstance(self.value,str):
            self.value=self.value.split("，")[0]
            self.value=self.value.split(",")[0]
            self.value=self.value.split(";")[0]
            self.value=self.value.split("；")[0]
            self.value=self.value.replace(" ","")
            self.value=self.value.split("\n")[0]
            self.value=self.value.split(":")[-1]
            self.value=self.value.split("：")[-1]
            self.value=self.value.split("至")[-1]
        return super()._post_process()
    

class ParagraphMatchField(BaseValueField):
    def __init__(self, paragraph_keys:List[str]=[],**kwargs):
        self.paragraph_keys=paragraph_keys
        super().__init__(**kwargs)
    def keys_in_content(self,content:str,keys:List[str]):
        """
        检查keys是否在content中
        """
        for key in keys:
            if key in content:
                return True
        return False
    def _extract_field_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        # 先走段落匹配
        matched_paragraphs=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph['title']:
                                matched_paragraphs.append(paragraph['content'])
                                break
        matched_str_list=matched_paragraphs
        matched_str_list=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            if contexts is None or len(contexts)<=0:
                continue
            contents=[]
            for file_context in contexts:
                text_content_list=file_context.text_content_list
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                contents.extend(table_content_list)
                contents.extend(text_content_list)
                if isinstance(file_context,DwgFileContext):
                    if file_context.text_list:
                        ocr_images,ocr_contents=self.ocr_check(file_context,p_width=self.p_width,p_height=self.p_height)
                        contents.extend(ocr_contents)
            for content in contents:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    matched_str_list.extend(str_list)
        matched_str_list,ie_results=self.ie_filter(matched_str_list)
        content="\n".join(matched_str_list)
        if not content.strip():
            value="数据中无该字段对应值"
        else:
            pipline=ExtractionFieldValueTaskBaseLanguageModelPipeLine(
                field_name=field_name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()     
        return value
    
class BaseDependentsField(ParagraphMatchField):
    def __init__(self, project_fields:Dict[str,Field]={},**kwargs):
        super().__init__(**kwargs)
        self.project_fields=project_fields
        self.ref_value=None
    def caculate_addition(self,n1,n2):
        value=-1
        try:
            if n1 and n2:
                value = float(n1)+float(n2)
        finally:
            return round(value,2)
    
    def caculate_subtraction(self,n1,n2):
        value=-1
        try:
            value = float(n1)-float(n2)
        finally:
            return value
    def caculate_division(self,greening_area,floor_area):
        value=-1
        try:
            if greening_area and floor_area:
                value = float(greening_area)/float(floor_area)
        finally:
            return value
    
    def parse_value_by_dependencies_values(self,dependencies_values:Dict):
        """根据依赖项的结果计算当前字段的结果"""
        pass
    def create_default_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        # 先走段落匹配
        matched_paragraphs=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph['title']:
                                matched_paragraphs.append(paragraph['content'])
                                break
        matched_str_list=matched_paragraphs
        content="\n".join(matched_str_list)
        if not content.strip():
            value="数据中无该字段对应值"
        else:
            pipline=ExtractionFieldValueTaskBaseLanguageModelPipeLine(
                field_name=field_name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()   
        self.ref_value=value   
        return value
    def _extract_field_value(self, context):
        if not self.dependencies:
            return super()._extract_field_value(context)
        if not self.ref_value:
            self.create_default_value(context=context)
        if self.is_use_ocr or self.is_use_ie:
            self.value=super()._extract_field_value(context)
        dependencies_values={}
        for dependencie in self.dependencies:
            if dependencie in self.project_fields:
                dependencies_values[dependencie]=self.project_fields[dependencie].parse(context=context)
            else:
                raise ValueError(f"当前项目不存在依赖字段【{dependencie}】")
        value=self.parse_value_by_dependencies_values(dependencies_values=dependencies_values)
        if isinstance(value,str) and  "-" not in value:
            self.value=value
        return self.value

################### 自定义字段 ###################


# 项目名称 
class ProjectNameField(ParagraphMatchField):
    pass

# 项目地址

# 总建筑面积
class TotalBuildingAreaField(BaseDependentsField):
    def parse_value_by_dependencies_values(self, dependencies_values):
        if len(dependencies_values) ==2:
            area1=dependencies_values[self.dependencies[0]]
            area2=dependencies_values[self.dependencies[1]]
            value=self.caculate_addition(area1,area2)
            self.value=value
            return value
        else:
            return None
    def _post_process(self):
        if self.ref_value and isinstance(self.ref_value,str):
            match = re.search(r'-?\d+\.?\d*', self.ref_value)
            if match:
                self.ref_value=match.group()
            else:
                self.ref_value=None
        if isinstance(self.value,str):
            match = re.search(r'-?\d+\.?\d*', self.value)
            if match:
                self.value=match.group()
            else:
                self.value=None
        if self.value is None and self.ref_value is None:
            self.value=-1
        elif self.value is None:
            self.value=self.ref_value
        elif self.ref_value is not None and self.ref_value is not None:
            if abs(float(self.value)-float(self.ref_value))/float(self.ref_value)>=0.2:
                self.value=self.ref_value
        self.value=str(self.value)
        return super()._post_process()

# 地上建筑面积
class AboveGroundBuildingAreaField(BaseDependentsField):
    def parse_value_by_dependencies_values(self, dependencies_values):
        if len(dependencies_values) ==1:
            buildings_areas:Dict[str,Dict[str,Any]]=dependencies_values[self.dependencies[0]]
            total_value=0
            for key in buildings_areas:
                if "地下" not in key:
                    total_value+=buildings_areas[key]['value']['total']
            self.value=total_value
            return total_value
        else:
            return None

    def _post_process(self):
        if self.ref_value and isinstance(self.ref_value,str):
            match = re.search(r'-?\d+\.?\d*', self.ref_value)
            if match:
                self.ref_value=match.group()
            else:
                self.ref_value=None
        if isinstance(self.value,str):
            match = re.search(r'-?\d+\.?\d*', self.value)
            if match:
                self.value=match.group()
            else:
                self.value=None
        if self.value is None and self.ref_value is None:
            self.value=-1
        elif self.value is None:
            self.value=self.ref_value
        elif self.ref_value is not None and self.ref_value is not None:
            if abs(float(self.value)-float(self.ref_value))/float(self.ref_value)>=0.2:
                self.value=self.ref_value
        self.value=str(self.value)
        return super()._post_process()
# 地下建筑面积
class UndergroundBuildingAreaField(BaseDependentsField):
    def parse_value_by_dependencies_values(self, dependencies_values):
        self.has_underground=False
        if len(dependencies_values) ==1:
            buildings_areas:Dict[str,Dict[str,Any]]=dependencies_values[self.dependencies[0]]
            total_value=0
            for key in buildings_areas:
                if "地下" in key:
                    self.has_underground=True
                    total_value+=buildings_areas[key]['value']['total']
            self.value=total_value
            return total_value
        else:
            return None
    def _post_process(self):
        if self.ref_value and isinstance(self.ref_value,str):
            match = re.search(r'-?\d+\.?\d*', self.ref_value)
            if match:
                self.ref_value=match.group()
            else:
                self.ref_value=None
        if isinstance(self.value,str):
            match = re.search(r'-?\d+\.?\d*', self.value)
            if match:
                self.value=match.group()
            else:
                self.value=None
        if not self.has_underground:
            self.value=0
        elif self.value is None and self.ref_value is None:
            self.value=-1
        elif self.value is None:
            self.value=self.ref_value
        elif self.ref_value is not None and self.ref_value is not None:
            if abs(float(self.value)-float(self.ref_value))/float(self.ref_value)>=0.2:
                self.value=self.ref_value
        self.value=str(self.value)
        return super()._post_process()

class CityLevelField(BaseDependentsField):
    """城市等级字段"""
    def parse_value_by_dependencies_values(self, dependencies_values):
        if self.dependencies[0] in dependencies_values:
            project_address=dependencies_values[self.dependencies[0]]
            regions=parse_regions(project_address)
            value=get_level_by_city(regions[1])
            return value
        return None

class LandscapeAreaField(BaseDependentsField):
     """景观面积=占地面积-基底面积"""
     def parse_value_by_dependencies_values(self, dependencies_values):
        total_area=dependencies_values[self.dependencies[0]]
        building_floor_area=dependencies_values[self.dependencies[1]]
        if not building_floor_area:
            building_floor_area=0
        value=self.caculate_subtraction(total_area,building_floor_area)
        self.value=value
        return value
    
class GreeningRateField(BaseDependentsField):
    """绿化率=(绿化面积/占地面积)"""
    def parse_value_by_dependencies_values(self, dependencies_values):
        greening_area=dependencies_values[self.dependencies[0]]
        floor_area=dependencies_values[self.dependencies[1]]
        value=self.caculate_division(greening_area,floor_area)*100
        return f"{value:.2f}%"
class OrdinaryParkingSpaceField(BaseDependentsField):
    """普通停车位=(停车位-充电桩位)"""
    def parse_value_by_dependencies_values(self, dependencies_values):
        parking_space=dependencies_values[self.dependencies[0]]
        charging_pile_position=dependencies_values[self.dependencies[1]]
        value=self.caculate_subtraction(parking_space,charging_pile_position)
        return int(value)

class ConstructionPeriodField(BaseDependentsField):
    """工期计算，两日期相减"""
    
    def _format_date(self,date_str):
        if "-" in date_str:
            format="%Y-%m-%d"
        elif "/" in date_str:
            format="%Y/%m/%d"
        elif "年" in date_str:
            format="%Y年%m月%d日"
        else:
            raise ValueError(f"日期异常，无法解析：{date_str}")
        return format
    def caculate_subtraction(self,startTime,endTime):
        try:
            from datetime import datetime
            # 原始日期
            start_time_format=self._format_date(startTime)
            end_time_format=self._format_date(endTime)
            startTime = datetime.strptime(startTime, start_time_format)
            endTime = datetime.strptime(endTime, end_time_format)
            # 计算差值
            delta = startTime-endTime 
            return delta.days+1
        except:
            return None
    
    def parse_value_by_dependencies_values(self, dependencies_values):
        if len(dependencies_values) ==2:
            startTime=dependencies_values[self.dependencies[0]]
            endTime=dependencies_values[self.dependencies[1]]
            value=self.caculate_subtraction(endTime,startTime)
            self.value=value
            return value
        else:
            return None
    

class DateToDateByDaysField(BaseDependentsField):
    """日期加天数得到日期字段"""
    
    def caculate_completion_date(self,startTime,total_days):
        try:
            from datetime import datetime,timedelta
            # 原始日期
            if "-" in startTime:
                format="%Y-%m-%d"
            elif "/" in startTime:
                format="%Y/%m/%d"
            elif "年" in startTime:
                format="%Y年%m月%d日"
            else:
                raise ValueError(f"日期异常，无法解析：{startTime}")
            date_obj = datetime.strptime(startTime,format)
            # 加30天
            new_date = date_obj + timedelta(days=int(total_days))
            return new_date.strftime(format)
        except:
            return None
    
    def parse_value_by_dependencies_values(self, dependencies_values):
        startTime=dependencies_values[self.dependencies[0]]
        total_days=dependencies_values[self.dependencies[1]]
        value=self.caculate_completion_date(startTime,total_days)
        return value
    
    def _post_process(self):
        if self.value:
            self.value=self.value.replace(" ","")
        return super()._post_process()
    

class AddressValueField(ParagraphMatchField):
    """地址字段"""
    
    def _post_process(self):
        from utils.address import parse_regions
        address=self.value
        self.value="".join(parse_regions(self.value)[:3])
        new_address=AddressParsePipeLine(
                address=address,
                model_name=self.agent_model_name
        ).invoke()
        new_address="".join(parse_regions(new_address)[:3])
        self.value=new_address
        return super()._post_process()



class EngineeringQualityExcellenceStandardsField(BaseValueField):
    def _post_process(self):
        self.value=next((clazz for clazz in ["合格", "不合格"] if clazz in self.value), self.value)
        return super()._post_process()


class SingleAreaValueField(ParagraphMatchField):
    def _post_process(self):
        match = re.search(r'-?\d+\.?\d*', self.value)
        if match:
            self.value=match.group()
        else:
            return 0
        return super()._post_process()

# 占地面积
class LandAreaField(SingleAreaValueField):
    def _get_pipeline(self):
        return LandAreaFieldValueTaskLanguageModelPipeLine

    def _extract_field_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        # 先走段落匹配
        matched_paragraphs=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph['title']:
                                matched_paragraphs.append(paragraph['content'])
                                break
        
        matched_str_list=[]+matched_paragraphs
        
        # 从业态中获取相关内容
        if context.business_model is not None:
            for model in context.business_model.models.values():
                building_contexts=model.building
                for building_context in building_contexts:
                    table_content_list=building_context.table_content_list
                    for table_content in table_content_list:
                        if self.keys_in_content(table_content,keys):
                            for key in keys:
                                str_list=self.extract_surrounding_text(table_content,key,50,50)
                                matched_str_list.extend(str_list)
                                if str_list and len(str_list)>0:
                                    break
                            
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            if contexts is None or len(contexts)<=0:
                continue
            contents=[]
            for file_context in contexts:
                text_content_list=file_context.text_content_list
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                contents.extend(table_content_list)
                contents.extend(text_content_list)
                if isinstance(file_context,DwgFileContext):
                    if file_context.text_list:
                        ocr_images,ocr_contents=self.ocr_check(file_context,p_width=self.p_width,p_height=self.p_height)
                        contents.extend(ocr_contents)
            for content in contents:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    matched_str_list.extend(str_list)
        matched_str_list,ie_results=self.ie_filter(matched_str_list)
        content="\n".join(matched_str_list)
        if not content.strip():
            value="数据中无该字段对应值"
        else:
            pipline=self._get_pipeline()(
                field_name=field_name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()     
            if len(value)>10:
                pipline=self._get_pipeline()(
                    field_name=field_name,
                    content=value,
                    alias=self.alias,
                    model_name=self.agent_model_name
                )
                value=pipline.invoke() 
        return value
    
# 充电桩数量
class ChargerNumberField(SingleAreaValueField):
    def _get_pipeline(self):
        return ChargerCountExtractionPipeLine
    
    def find_car_ref_contents(self,text_list:List[QueryItem],keys)->List[str]:
        # 候选item列表
        candidate_items:List[QueryItem]=[]
        for item in text_list:
            if any([key in item.text for key in keys]):
                candidate_items.append(item)
        # 获取与candid一行的item
        rows=[]
        for cadidate_item in candidate_items:
            row=[]
            for item in text_list:
                p=item.bounds.center_point()
                if p.y<=cadidate_item.bounds.maxy and p.y>=cadidate_item.bounds.miny:
                    row.append(item)
            rows.append(row)
        contents=[]
        for row in rows:
            row.sort(key=lambda x:x.bounds.minx)
            content="".join([item.text for item in row])
            contents.append(content)
        return contents
    def _extract_field_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        # 先走段落匹配
        matched_paragraphs=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph['title']:
                                matched_paragraphs.append(paragraph['content'])
                                break
        matched_str_list=[]+matched_paragraphs
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            if contexts is None or len(contexts)<=0:
                continue
            contents=[]
            for file_context in contexts:
                text_content_list=file_context.text_content_list
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                contents.extend(table_content_list)
                contents.extend(text_content_list)
                if isinstance(file_context,DwgFileContext):
                    if file_context.text_list:
                        ocr_images,ocr_contents=self.ocr_check(file_context,p_width=self.p_width,p_height=self.p_height)
                        contents.extend(ocr_contents)
                        # TODO 停车数专有
                        car_ref_contents=self.find_car_ref_contents(file_context.text_list,keys)
                        contents.extend(car_ref_contents)
            for content in contents:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    matched_str_list.extend(str_list)
        matched_str_list,ie_results=self.ie_filter(matched_str_list)
        content="\n".join(matched_str_list)
        if not content.strip():
            value="数据中无该字段对应值"
        else:
            pipline=self._get_pipeline()(
                field_name=field_name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()     
            if len(value)>10:
                pipline=self._get_pipeline()(
                    field_name=field_name,
                    content=value,
                    alias=self.alias,
                    model_name=self.agent_model_name
                )
                value=pipline.invoke() 
        return value
# 停车位数量
class ParkingSpaceNumberField(ChargerNumberField):
    def _get_pipeline(self):
        return ParkingSpaceCountExtractionPipeLine

class BaseBusinessModelField(Field):
    def __init__(self, name, alias = [], dependencies = [], project_fields:Dict[str,Field]={},default_value = None, context_scope = [], is_hidden = False, is_use_ocr = False, is_use_ie = False,agent_model_name="gpt-4o-mini"):
        is_general=False
        self.agent_model_name=agent_model_name
        self.project_fields=project_fields
        super().__init__(name, alias, dependencies, default_value, context_scope, is_hidden, is_use_ocr, is_use_ie, is_general)
    
    def _extract_field_business_model(self,context:ProjectContext,business_model_item:BusinessModelItem)->Tuple[Any,ReferenceData]:
        raise NotImplementedError("请实现`_extract_field_business_model`方法")
    
    def _extract_field_value(self, context:ProjectContext)->Dict[str,Any]:
        # 获取当前字段对应的业态信息
        if not context.business_model:
            return None
        business_model=context.business_model
        
        if not business_model.model_names:
            return None
        
        value:Dict[str,Dict[str,Any]]={}
        
        for business_model_name in business_model.model_names:
            business_model_item=business_model.models[business_model_name]
            item_value,ref_data=self._extract_field_business_model(context,business_model_item)
            value[business_model_name] = {
                "value":item_value,
                "ref_data":ref_data
            }
        return value
        
 

# 建筑面积
class BuildingAreaForBusinessModelField(BaseBusinessModelField):
    
    pattern = r'''
    (.*?)                          # 任意前缀内容（非贪婪），可忽略
    [\s　]*                        # 可选空格或全角空格

    # =================== 楼层信息匹配 ===================
    (?P<level>
        (
            [+-]?\d+                          # 阿拉伯数字形式（如 +3, -2, 10）
            |
            (负|地下)?                        # 中文楼层前缀（负、地下）
            [首零一二三四五六七八九十]+        # 中文数字（首层、一、二、三……）
            (层)?                             # 可选的“层”字
        )
        (
            (、|~|至)                          # 连接符，如 “、” 或 “至” 表示并列或范围
            ((负|地下)?[零一二三四五六七八九十]+)  # 第二部分中文楼层
            (层)?                             # 第二部分可选“层”字
        )*
    )
    (组合)?
    ((夹|奇数|偶数)层)?              # 可选后缀说明：夹层、奇数层、偶数层

    (地下室平时|平时平面图|地下室|平面图)  # 图纸类别：平面图、地下室平时等

    # =================== 屋面类平面图匹配 ===================
    |
    (?P<roof>
        (屋顶|构架|屋面|天面)(层)?平面图  # 屋面类关键词
    )
    '''
    
    def _extract_field_business_model(self,context:ProjectContext,business_model_item:BusinessModelItem)->Tuple[Any,ReferenceData]:
        ref_data=None
        if business_model_item.structure:
            area=self.extract_area_from_building_contexts(business_model_item.structure)
        elif business_model_item.building:
            area=self.extract_area_from_building_contexts(business_model_item.building)
        else:
            area=0
        return area,ref_data
    
    
    def extract_area_from_building_contexts(self,building_contexts:List[BaseFileContext]):
        keys=[self.name]
        matched_str_list=[]
        if building_contexts is None or len(building_contexts)<=0:
            return 0
        contents=[]
        for file_context in building_contexts:
            table_content_list=[]
            if isinstance(file_context,DwgFileContext):
                table_content_list=file_context.table_content_list
            for content in table_content_list:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    if str_list and len(str_list)>0:
                        matched_str_list.extend(str_list)
                        break
        content="\n".join(matched_str_list)
        if not content.strip():
            value=0
        else:
            pipline=ExtractionFieldValueTaskBaseLanguageModelPipeLine(
                field_name=self.name,
                content=content,
                alias=self.alias,
                model_name=self.agent_model_name
            )
            value=pipline.invoke()
        return value
    
    def _pre_process_text_list(self,text_list:List[QueryItem])->List[QueryItem]:
        # 寻找 "~" 的对象
        candidate_items:List[QueryItem]=[]
        delete_items=[]
        for item in text_list:
            if "~"==item.text:
                candidate_items.append(item)
                delete_items.append(item)

        rows=[]
        for cadidate_item in candidate_items:
            row=[]
            for item in text_list:
                p=cadidate_item.bounds.center_point()
                if p.y<=item.bounds.maxy and p.y>=item.bounds.miny:
                    row.append(item)
            rows.append(row)
        for row in rows:
            row.sort(key=lambda x:x.bounds.minx)
            for idx,item in enumerate(row):
                if item.text == "~":
                    if idx!=0 and idx<len(row)-1:
                        row[idx-1].text=row[idx-1].text+"~"+row[idx+1].text
                        delete_items.append(row[idx+1])
                        break;
                    
        for item in delete_items:
            try:
                text_list.remove(item)
            except:
                pass
        return text_list
    
    def chinese_to_int(self,cn: str) -> int:
        cn_num = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            "首":1
        }
        cn_unit = {'十': 10, '百': 100, '千': 1000, '万': 10000}

        if not cn:
            return 0

        negative = False
        if cn.startswith("负"):
            cn=cn[1:]
            negative = True
        if cn.startswith("地下"):
            cn = cn[2:]
            negative = True

        total = 0
        unit = 1
        num = 0
        i = len(cn) - 1
        while i >= 0:
            ch = cn[i]
            if ch in cn_unit:
                unit = cn_unit[ch]
                if i == 0:  # 例："十二" → 10 + 2
                    total += unit
            elif ch in cn_num:
                num = cn_num[ch]
                total += num * unit
                unit = 1
            i -= 1

        return -total if negative else total

    def caculate_total_value(self,building_model_name:str,value:Dict):
        total_value=0.0
        
        if "地下" in building_model_name:
            for key,v in value.items():
                if "负" in key or "-" in key or "地下" in key:
                    total_value+=v
        else:
            for key,v in value.items():
                if "负" not in key:
                    total_value+=v
        # 保留两位小数
        total_value=round(total_value,2)
        return total_value

    def _pattern_filter(self,text)->List[Tuple]:
        if not text:
            return None
        text=text.replace(" ", "")
        text=text.split("-")[-1]
        result=[]
        pattern = re.compile(self.pattern, re.VERBOSE)
        for m in re.finditer(pattern, text):
            raw_level=m.group('level')
            roof_name=m.group('roof')
            levels=[]
            if raw_level is not None:
                raw_level=raw_level.replace("层","")
            if raw_level is None:
                levels.append(roof_name)
            elif "至" in raw_level:
                ls=raw_level.split("至")
                start_level=self.chinese_to_int(ls[0])
                end_level=self.chinese_to_int(ls[1])
                if "奇数" in text:
                    for i in range(start_level,end_level+1):
                        if i%2!=0:
                            levels.append(i)
                elif "偶数" in text:
                    for i in range(start_level,end_level+1):
                        if i%2==0:
                            levels.append(i)
                else:
                    for i in range(start_level,end_level+1):
                        levels.append(i)
                levels=[f"{level}层平面图" for level in levels]
            else:
                split_levels=raw_level.split("、")
                for l in split_levels:
                    if "~" in l:
                        ls=l.split("~")
                        if len(ls)==2:
                            start_level=self.chinese_to_int(ls[0])
                            end_level=self.chinese_to_int(ls[1])
                        else:
                            start_level=end_level=self.chinese_to_int(ls[-1])
                        for i in range(start_level,end_level+1):
                            levels.append(i)
                    else:
                        l=self.chinese_to_int(l)
                        if "夹层" in text:
                            l=str(l)+"层夹"
                        levels.append(l)
                levels=[f"{level}层平面图" for level in levels]
            
            for level in levels:
                item=(
                    level,
                    text
                )
                result.append(item)
        return result   
    
    def is_area_text(self,text:str)->bool:
        if not text:
            return False
        if "本层建筑面积" in text or \
            "本层总建筑面积" in text or \
            "计容面积" in text or \
            "总建筑面积:" in text or \
            "层建筑面积" in text or \
            "本层面积" in text:
            return True
        return False
        
    def _area_filter(self,text_list:List[QueryItem],context)->List[str]:
        underground_pattern = r"地.*?[:：]\s*([0-9]+(?:\.[0-9]+)?)\s*平方米"
        # 先查找符合过滤条件的文本
        in_condition_text_list:List[QueryItem]=[]
        for text_item in text_list:  
            if text_item.text:
                filter_result=self._pattern_filter(text_item.text)
                if filter_result and len(filter_result)>0:
                    in_condition_text_list.append(text_item)                            
        is_special_underground=False
        if not in_condition_text_list or len(in_condition_text_list)<=0:
            for text_item in text_list:    
                if text_item.text:
                    if re.search(underground_pattern,text_item.text):
                        is_special_underground=True
                        in_condition_text_list.append(text_item)       
        if is_special_underground:
            return [text_item.text for text_item in in_condition_text_list],is_special_underground
        # 查找其下方的建筑面积
        area_text_list:List[Tuple[QueryItem,QueryItem,QueryItem]]=[]
        for condition_text in in_condition_text_list:
            font_height=abs(condition_text.bounds.maxy-condition_text.bounds.miny)
            font_width=abs(condition_text.bounds.maxx-condition_text.bounds.minx)
            condition_bounds=condition_text.bounds
            # 查找符合条件的文本
            candidate_text_list=[]
            for text_item in text_list:
                if not text_item.text:
                    continue
                if self.is_area_text(text_item.text) or ("地" in condition_text.text and re.search(underground_pattern,text_item.text)):
                    text_center_point=text_item.bounds.center_point()
                    # 单位归一化，以字高为y的单位长度，以condition_text宽为x的单位长度
                    if (abs(text_center_point.y-condition_bounds.miny)/font_height<=20):
                        if abs(text_center_point.x-condition_bounds.minx)/font_width>5:
                            continue
                        candidate_text_list.append(text_item)
            candidate_text_list.sort(key=lambda p: p.bounds.miny,reverse=True)
            candidate_text=candidate_text_list[0] if candidate_text_list else None
            if candidate_text:
                # 获取面积
                values:List[QueryItem]=[]
                for text_item in text_list:
                    text_center_point=text_item.bounds.center_point()
                    if (text_center_point.y>candidate_text.bounds.miny
                        and text_center_point.y<candidate_text.bounds.maxy
                        and text_center_point.x > candidate_text.bounds.maxx):
                        if text_item.text==":":
                            continue
                        values.append(text_item)
                if values and len(values)>0:
                    values.sort(key=lambda p: p.bounds.minx)
                    value=values[0]
                    area_text_list.append((condition_text,candidate_text,value))
                else:
                    area_text_list.append((condition_text,candidate_text,None))
                if re.search(underground_pattern,candidate_text.text):
                    area_text_list.append((condition_text,candidate_text,None))
            else: # TODO 针对c002项目进行设计
                ## 寻找‘建筑面积’字样
                floor_area_item=None
                for item in text_list:
                    if (
                            "建筑面积" in item.text and \
                            "本层建筑面积" not in item.text and \
                            abs(item.bounds.maxy-condition_text.bounds.miny)/font_height<20
                        ):
                        floor_area_item=item
                        break
                if floor_area_item: # 找下方的面积字段
                    for area_text in text_list:
                        area_text_center_point=area_text.bounds.center_point()
                        if (
                            abs(area_text.bounds.maxy-floor_area_item.bounds.miny)<5000 and
                            area_text.bounds.maxy<floor_area_item.bounds.miny and
                            area_text_center_point.x>=floor_area_item.bounds.minx and 
                            area_text_center_point.x<=floor_area_item.bounds.maxx and
                            len(area_text.text)>2 and
                            is_number(area_text.text.strip())
                        ):
                            area_text_list.append((condition_text,floor_area_item,area_text))
                            break
        result:List[str]=[]
        for condition_text,candidate_text,value in area_text_list:
            result.append(
                f"{condition_text.text}\n{candidate_text.text}:{value.text if value else ''}"
            )
        return result,is_special_underground
                    
                    
                    
                    
    def _extract_field_business_model(self, project_context, business_model_item:BusinessModelItem):
        building_contexts=business_model_item.building
        if not building_contexts:
            return None,None
        # 从building中抽取建筑面积信息
        area_content_map={}
        for context in building_contexts:
            if not isinstance(context,DwgFileContext):
                continue
            # text_content=context.text_content_list
            # 预处理text_content.text_list
            pre_processed_text_list=self._pre_process_text_list(context.text_list)
            text_contents,is_special_underground=self._area_filter(pre_processed_text_list,context=context)
            for content in text_contents:
                if is_special_underground:
                    pattern = r"地(上|下)([一二三四五六七八九十]+)层.*?[:：].*?平方米"
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        position = match.group(1)  # "上" 或 "下"
                        floor = match.group(2)     # 中文数字（如 "三"、"二"）
                        level=f"{'-'if position=='下' else '' }{self.chinese_to_int(floor)}层平面图"
                        area_content_map[level]=area_content_map.get(level,[])
                        area_content_map[level].append(content)
                else:  
                    restult=self._pattern_filter(content)
                    for item in restult:
                        level,_=item
                        if level is not None:
                            area_content=area_content_map.get(level,[])
                            area_content.append(content)
                            area_content_map[level]=area_content
        value={}
        ref_contexts=[]
        for field_name in area_content_map:
            ref_contexts=area_content_map.get(field_name,[])
            if ref_contexts and len(ref_contexts)>0:
                value[field_name]=FloorAreaExtractionPipeLine(
                    field_name=field_name,
                    ref_contexts=ref_contexts,
                    model_name=self.agent_model_name
                ).invoke()
        total_value=self.caculate_total_value(business_model_item.building_model_name,value)
        if value is None or len(value)<=0:
            # 直接在图纸中查找
            total_value=self.extract_area_from_building_contexts(business_model_item.building)
            try:
                total_value=self._str_to_number(total_value)
            except:
                import pdb;pdb.set_trace()
        
        value["total"]=total_value
        ref_data=ReferenceData()
        if ref_contexts and len(ref_contexts)>0:
            ref_data.texts=[ContentItem(content=content)for content in ref_contexts]
        return value,ref_data
                
    def _str_to_number(self,value):
        match = re.search(r'-?\d+\.?\d*', value)
        if match:
            return float(match.group())
        else:
            return 0
        

class NumberOfFloorsBusinessModelField(BaseBusinessModelField):

    def _calculate_number_of_floors(
        self, business_model_item: BusinessModelItem, floors_info: Optional[Dict[str, Union[str, int]]] = None
    ) -> int:
        """
        计算楼层数
        """
        if not floors_info:
            return 0

        total_floors = 0
        is_underground = "地下" in business_model_item.building_model_name
        chinese_digits = {"一", "二", "三", "四", "五", "六", "七", "八", "九", "首"}

        for key, value in floors_info.items():
            if value is None or value <= 0:
                continue

            if is_underground:
                if "负" in key or "-" in key or "地下" in key:
                    total_floors += 1
            else:
                first_char = key[0]
                if (first_char in chinese_digits or first_char.isdigit()) and "夹层" not in key:
                    total_floors += 1

        return total_floors

    def _extract_field_business_model(self, project_context, business_model_item: BusinessModelItem):

        if not self.dependencies:
            return None,None

        dependent_field_name = self.dependencies[0]
        dependent_field = self.project_fields.get(dependent_field_name)
        dependent_value = dependent_field.value if dependent_field else None
        if (
            not dependent_value
            or business_model_item.building_model_name not in dependent_value
            or not isinstance(dependent_value[business_model_item.building_model_name], dict)
        ):
            return None,None
        if len(dependent_value.get(business_model_item.building_model_name,{}).get('value',{}))<=1:
            # 从建筑图纸中提取楼层数
            keys=[self.name]+self.alias
            building_contexts=business_model_item.building
            matched_str_list=[]
            if building_contexts is None or len(building_contexts)<=0:
                return 0
            for file_context in building_contexts:
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                for content in table_content_list:
                    for key in keys:
                        str_list=self.extract_surrounding_text(content,key,50,50)
                        if str_list and len(str_list)>0:
                            matched_str_list.extend(str_list)
                            break
            content="\n".join(matched_str_list)
            if not content.strip():
                value=0
            else:
                pipline=ExtractionFieldValueTaskBaseLanguageModelPipeLine(
                    field_name=self.name,
                    content=content,
                    alias=self.alias,
                    model_name=self.agent_model_name
                )
                value=pipline.invoke()
                try:
                    value=int(value)
                except:
                    value=0
            return value,ReferenceData()
        floors_info = dependent_value[business_model_item.building_model_name].get('value',{})
        floor_count = self._calculate_number_of_floors(business_model_item, floors_info)
        ref_data=ReferenceData()
        return floor_count,ref_data
                
                

class BaseStructureExtractBusinessModelField(BaseBusinessModelField):

    def _pattern_filter(self,text:str):
        raise NotImplementedError("请实现`_pattern_filter`方法")
        

    def _extract_value(self,business_model_item:BusinessModelItem,relevant_text_list:List[str]):
        raise NotImplementedError("请实现`_extract_value`方法")
    
    
    
    def _get_ocr_ref_data(self, project_context, business_model_item: BusinessModelItem)->ReferenceData:
        target_text="建筑分类等级"
        structure_context_list=business_model_item.structure
        ref_data=ReferenceData()
        for structure_context in structure_context_list:
            if isinstance(structure_context,DwgFileContext):
                text_list_query_items=structure_context.text_list        
                target_query_item=None
                for query_item in text_list_query_items:
                    if query_item.text and target_text in query_item.text:
                        target_query_item=query_item
                        break
                if not target_query_item:
                    break
                title_splitter=TitleBelowTableSplitter(
                    title=target_query_item.text,
                    text_list=text_list_query_items,
                    mapid=structure_context.mapid
                )
                image_path=title_splitter.save_to_image()
                ref_data.ocrs.append(
                    OcrItem(
                        image_path=image_path
                    )
                )
        return ref_data
        
    
    def _extract_field_business_model(self, project_context:ProjectContext, business_model_item: BusinessModelItem):
        building_contexts=business_model_item.structure
        if not building_contexts:
            # return None,None
            building_contexts=project_context.building_design_document_context
        # 从building中抽取建筑面积信息
        relevant_text_list=[]
        for context in building_contexts:
            if not isinstance(context,DwgFileContext):
                continue
            content_list=[]
            text_content=context.text_content_list
            if text_content:
                content_list.extend(text_content)
            table_content_list=context.table_content_list
            if table_content_list:
                content_list.extend(table_content_list)
            for content in content_list:
                restult=self._pattern_filter(content)
                if restult:
                    relevant_text_list.append(restult)
        value=self._extract_value(business_model_item,relevant_text_list)
        ref_data=ReferenceData()
        if self.is_use_ocr:
            ref_data=self._get_ocr_ref_data(project_context, business_model_item)
        return value,ref_data
                               
                               

    
    
# 业态中的使用年限字段
class ServiceLifeBusinessModelField(BaseStructureExtractBusinessModelField):
    def __init__(self, paragraph_keys:List[str]=[],**kwargs):
        self.paragraph_keys=paragraph_keys
        super().__init__(**kwargs)
    
    def keys_in_content(self,content:str,keys:List[str]):
        """
        检查keys是否在content中
        """
        for key in keys:
            if key in content:
                return True
        return False
    def _extract_field_business_model(self, project_context:ProjectContext, business_model_item: BusinessModelItem):

        # 先走段落匹配:招标文件
        match_paragraph=[]
        for scope in self.context_scope:
            contexts=project_context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph["title"]:
                                match_paragraph.append(paragraph["content"])
                                break
        building_contexts=business_model_item.structure
        if not building_contexts:
            # return None,None
            building_contexts=project_context.get_contents_by_scope(ContextScope.BUILDING_DESIGN)+business_model_item.building
        relevant_text_list=[]+match_paragraph
        for context in building_contexts:
            if not isinstance(context,DwgFileContext):
                continue
            content_list=[]
            text_content=context.text_content_list
            if text_content:
                content_list.extend(text_content)
            table_content_list=context.table_content_list
            if table_content_list:
                content_list.extend(table_content_list)
            for content in content_list:
                restult=self._pattern_filter(content)
                if restult:
                    relevant_text_list.append(restult)
        value=self._extract_value(business_model_item,relevant_text_list)
        ref_data=ReferenceData()
        if self.is_use_ocr:
            ref_data=self._get_ocr_ref_data(project_context, business_model_item)
        return value,ref_data
    def _pattern_filter(self, text):
        if not text:
            return None
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        values=[]
        for key in keys:
            if key in text:
                value=self.extract_surrounding_text(text,key,30,30)
                values.extend(value)
                break
        if values:
            res= "\n".join(values)    
            if res: # 防止换行符太多。
                if (res.count('\n')/len(res))>=0.4:
                    return res.replace('\n','')
                else:
                    return res
        return None

    def _extract_value(self, business_model_item: BusinessModelItem, relevant_text_list: List[str]):
        if not relevant_text_list:
            return None
        relevant_text=relevant_text_list
        pipeline=ServiceLifeExtractionPipeLine(
            field_name=self.name,
            ref_contexts=relevant_text,
            model_name=self.agent_model_name
        )
        value=pipeline.invoke()
        return value

# 业态中的结构类型字段
class StructureTypeBusinessModelField(ServiceLifeBusinessModelField):
    def _pattern_filter(self, text):
        if not text:
            return None
        structure_types={
            "框架结构","剪力墙结构","框架剪力墙结构","钢结构","筒体结构","混合结构"
        }
        result=[]
        for structure_type in structure_types:
            if structure_type in text:
                values=self.extract_surrounding_text(text,structure_type,30,30)
                result.extend(values)
        if result:
            return "\n".join(result)
        return None
    def _extract_value(self, business_model_item: BusinessModelItem, relevant_text_list: List[str]):
        if not relevant_text_list:
            return None
        pipeline=StructureTypeExtractionPipeLine(
            field_name=self.name,
            alias=self.alias,
            ref_contexts=relevant_text_list,
            model_name=self.agent_model_name
        )
        value=pipeline.invoke()
        return value
    def _extract_field_business_model(self, project_context:ProjectContext, business_model_item: BusinessModelItem):
        # 先走段落匹配:招标文件
        match_paragraph=[]
        for scope in self.context_scope:
            contexts=project_context.get_contents_by_scope(scope)
            for file_context in contexts:
                if file_context.paragraphs and len(file_context.paragraphs)>0:
                    for paragraph in file_context.paragraphs:
                        for paragraph_key in self.paragraph_keys:
                            if paragraph_key in paragraph["title"]:
                                match_paragraph.append(paragraph["content"])
                                break
        building_contexts=business_model_item.structure
        if not building_contexts:
            # return None,None
            building_contexts=project_context.get_contents_by_scope(ContextScope.BUILDING_DESIGN)+business_model_item.building
        relevant_text_list=[]
        for context in building_contexts:
            if len(match_paragraph)>0:
                relevant_text_list=match_paragraph
                break
            if not isinstance(context,DwgFileContext):
                continue
            content_list=[]
            text_content=context.text_content_list
            if text_content:
                content_list.extend(text_content)
            table_content_list=context.table_content_list
            if table_content_list:
                content_list.extend(table_content_list)
            for content in content_list:
                restult=self._pattern_filter(content)
                if restult:
                    relevant_text_list.append(restult)
        value=self._extract_value(business_model_item,relevant_text_list)
        ref_data=ReferenceData()
        if self.is_use_ocr:
            ref_data=self._get_ocr_ref_data(project_context, business_model_item)
        return value,ref_data

# 抗震设防烈度字段（和抗震等级一样）
class BuildingFortificationIntensityBusinessModelField(ServiceLifeBusinessModelField):
    def _extract_value(self, business_model_item: BusinessModelItem, relevant_text_list: List[str]):
        if not relevant_text_list:
            return None
        relevant_text="\n".join(relevant_text_list)
        pipeline=BuildingFortificationIntensityExtractionPipeLine(
            field_name=self.name,
            ref_contexts=relevant_text,
            model_name=self.agent_model_name
        )
        value=pipeline.invoke()
        return value
    
# 业态中的抗震等级字段
class EarthquakeLevelBusinessModelField(ServiceLifeBusinessModelField):
    def _extract_value(self, business_model_item: BusinessModelItem, relevant_text_list: List[str]):
        if not relevant_text_list:
            return None
        relevant_text=relevant_text_list
        pipeline=EarthquakeLevelExtractionPipeLine(
            field_name=self.name,
            ref_contexts=relevant_text,
            model_name=self.agent_model_name
        )
        value=pipeline.invoke()
        return value
    
# 电梯字段
class LiftValueField(BaseValueField):
    """基础的 字段-值"""
    def _extract_field_value(self,context:ProjectContext):
        value=None
        field_name=self.name
        keys=[field_name]+self.alias
        matched_str_list=[]
        for scope in self.context_scope:
            contexts:List[BaseFileContext]=context.get_contents_by_scope(scope)
            contents=[]
            for file_context in contexts:
                text_content_list=file_context.text_content_list
                table_content_list=[]
                if isinstance(file_context,DwgFileContext):
                    table_content_list=file_context.table_content_list
                contents.extend(table_content_list)
                contents.extend(text_content_list)
                if isinstance(file_context,DwgFileContext):
                    if file_context.text_list:
                        ocr_images,ocr_contents=self.ocr_check(file_context,p_width=self.p_width,p_height=self.p_height)
                        contents.extend(ocr_contents)
            for content in contents:
                for key in keys:
                    str_list=self.extract_surrounding_text(content,key,50,50)
                    matched_str_list.extend(str_list)
        matched_str_list,ie_results=self.ie_filter(matched_str_list)
        content="\n".join(matched_str_list)
        pattern='电梯DT(\d+)'
        matches = re.findall(pattern, content)
        value=len(set(matches))
        return value
    
    def _post_process(self):
        if not self.value:
            return None
        if self.return_type=="number":
            self.value=''.join(re.findall(r'\d+', self.value))
        elif self.return_type=="str" and isinstance(self.value,str):
            self.value=self.value.split("，")[0]
            self.value=self.value.split(",")[0]
            self.value=self.value.split(";")[0]
            self.value=self.value.split("；")[0]
            self.value=self.value.replace(" ","")
            self.value=self.value.split("\n")[0]
            self.value=self.value.split(":")[-1]
            self.value=self.value.split("：")[-1]
        return super()._post_process()
    
    
# 抗震等级字段
class EarthquakeLevelField(BaseDependentsField):
    def parse_value_by_dependencies_values(self, dependencies_values):
        current_level="一级"
        if len(dependencies_values) ==1:
            buildings_earthquake_levels:Dict[str,Dict[str,Any]]=dependencies_values[self.dependencies[0]]
            """
            buildings_earthquake_levels的形状如下：
            {
                "地下室": {
                    "value": "三级"
                },
                "A05": {
                    "value": "三级"
                }
            }
            """
            earthquake_levels_mapping={}
            for key in buildings_earthquake_levels:
                level = buildings_earthquake_levels[key]['value']
                earthquake_levels_mapping[level]=earthquake_levels_mapping.get(level,0)+1
                if earthquake_levels_mapping.get(current_level,0)<earthquake_levels_mapping.get(level,0):
                    current_level=level
            self.value=current_level
        return current_level
    

# 建筑高度
class HeightBusinessModelField(BaseBusinessModelField):       
    """
    建筑高度字段，一般取决于建筑物和结构的总高度
    """      
    def _extract_field_business_model(self, project_context, business_model_item:BusinessModelItem):
        if not business_model_item.facade:
            return -1,self.ref_data
        facade_context_list=business_model_item.facade
        candidation_facade:List[float]=[]
        for file_context in facade_context_list:
            if isinstance(file_context,DwgFileContext):
                facade_context_list=file_context.facade_content_list
                for facade_context in tqdm.tqdm(facade_context_list,desc='建筑高度计算中...'):
                    if len(facade_context.elevation)>0:
                        # pipe=HeightParsePipeLine(file_context,facade_context,business_model_item.building_model_name)
                        # value=pipe.invoke()
                        # candidation_facade.append(value)
                        for _,pole_values,_ in facade_context.get_group_by_zero_point():
                            candidation_facade.extend(pole_values)
        if candidation_facade:
            if "地下室" in business_model_item.building_model_name:
                height=abs(min(candidation_facade))
            else:
                height=max(candidation_facade)
            self.value=height
            return height,self.ref_data
        else:
            return -1,self.ref_data
        
                

# 标准层高
class StandardHeightBusinessModelField(BaseBusinessModelField):
    
    def most_common_element(self,lst):
        if not lst:
            return None
        return Counter(lst).most_common(1)[0][0]
    
    """
    标准层高字段，一般取决于一层楼的高度
    """      
    def _extract_field_business_model(self, project_context, business_model_item:BusinessModelItem):
        if not business_model_item.facade:
            return -1,self.ref_data
        facade_context_list=business_model_item.facade
        candidation_facade:List[float]=[]
        for file_context in facade_context_list:
            if isinstance(file_context,DwgFileContext):
                facade_context_list=file_context.facade_content_list
                for facade_context in tqdm.tqdm(facade_context_list,desc='标准层高计算中...'):
                    if len(facade_context.elevation)>0:
                        # pipe=StandardHeightParsePipeLine(file_context,facade_context,business_model_item.building_model_name)
                        # value=pipe.invoke()
                        # candidation_facade.append(value)
                        for _,_,diffs in facade_context.get_group_by_zero_point():
                            candidation_facade.extend(diffs)
        
        if candidation_facade:
            # 移除为0的值
            candidation_facade=[value for value in candidation_facade if value!=0]
            if "地下室" in business_model_item.building_model_name:
                height=min(candidation_facade)
            else:
                # 寻找最多的重数
                height=self.most_common_element(candidation_facade)
            self.value=height
            return height,self.ref_data
        else:
            return -1,self.ref_data
