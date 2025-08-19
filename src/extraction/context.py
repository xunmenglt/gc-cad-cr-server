import os
import re
from dataclasses import dataclass,field
from typing import List,Dict,Literal,Optional,Tuple

from enum import Enum

from vjmap.items import (
    QueryItem,
    EnvelopBounds
)


class ContextScope(Enum):
    TENDER = "tender" # 招标文件
    BUILDING_DESIGN = "building_design" # 建筑设计总说明
    BASEMENT = "basement" # 地下室
    DEFENSE = "defense" # 人防
    CCD = "ccd" # 计价文件

@dataclass
class BaseFileContext:
    file_path: str = field(metadata={"help": "文件路径"})
    text_content_list: List[str] = field(metadata={"help": "文本内容列表"})
    paragraphs:List[Dict[Literal["title","content"],str]]=field(default_factory=dict,metadata={"help":"段落内容"})
    # 额外字段
    file_name: str = field(init=False, metadata={"help": "文件名"})
    file_extension: str = field(init=False, metadata={"help": "文件后缀"})
    file_size:int=field(init=False,metadata={"help":"文件大小"})

    def __post_init__(self):
        """在实例化时自动解析文件名和后缀"""
        self.file_name = os.path.basename(self.file_path)  # 获取文件名（带后缀）
        self.file_extension = os.path.splitext(self.file_name)[1]  # 获取文件后缀（带点）
        self.file_size=os.path.getsize(self.file_path)

@dataclass
class FacadeContext:
    submap:Optional[EnvelopBounds]=field(default=None,metadata={"help":"子区域边界"})
    text_items:List[QueryItem]=field(default_factory=list,metadata={"help":"文本项列表"})
    candidate_lines:List[QueryItem]=field(default_factory=list,metadata={"help":"候选线条"})
    """
    Tuple[List[QueryItem],QueryItem]:([left_side,right_side,pole],height)
    """
    elevation:List[Tuple[List[QueryItem],QueryItem]]=field(default_factory=list,metadata={"help":"标高信息"})
    
    def __repr__(self):
        submap=self.submap
        elevation=self.elevation
        format_str=""
        if not submap:
            return "当前立面子图不存在"
        format_str+=f"子图坐标：{submap.to_str()}\n"
        format_str+=f"标高数据：\n"
        if not elevation:
            format_str+="\t当前子图没有标高数据\n"
        else:
            for idx,elevation_data in enumerate(elevation):
                left_side,right_side,pole=elevation_data[0]
                number_item=elevation_data[-1]
                format_str+="\t"+"-"*5+"\n"
                format_str+=f"\t- id:{idx}\n"
                format_str+=f"\t\t左侧斜边：{left_side.bounds.to_str()}\n"
                format_str+=f"\t\t右侧斜边：{right_side.bounds.to_str()}\n"
                format_str+=f"\t\t顶部标杆：{pole.bounds.to_str()}\n"
                format_str+=f"\t\t标高：{number_item.text}"
        return format_str

    def to_dict(self):
        data={}
        data["submap"]=self.submap.to_dict()
        data["text_items"]=[item.to_dict() for item in self.text_items]
        data["candidate_lines"]=[item.to_dict() for item in self.candidate_lines]
        data["elevation"]=[[[item.to_dict() for item in items],item.to_dict()]for items,item in self.elevation]
        
        return data
    
    @staticmethod
    def from_dict(data):
        context=FacadeContext()
        context.submap=EnvelopBounds().from_dict(data["submap"])
        context.text_items=[QueryItem().from_dict(item) for item in data["text_items"]]
        context.candidate_lines=[QueryItem().from_dict(item) for item in data["candidate_lines"]]
        context.elevation=[[[QueryItem().from_dict(item) for item in items],QueryItem().from_dict(item)]for items,item in data["elevation"]]
        return context
    
    # 根据正负零零点，获取与其旗杆平行的所有点，从小到大
    def get_group_by_zero_point(self) -> List[Tuple[List[Tuple[List[QueryItem],QueryItem]],List[float],List[float]]]:
        if not self.elevation:
            return []
        
        # 分组结果，即属于同一垂直平行方向上的所有点
        group_result:List[Tuple[List[Tuple[List[QueryItem],QueryItem]],List[float],List[float]]]=[]
        candidate_groups:List[List[Tuple[List[QueryItem],QueryItem]]]=[]
        
        all_in_data=set()
        
        for elevation_data in self.elevation:
            _,_,pole=elevation_data[0]
            if pole.bounds.to_str() not in all_in_data:
                all_in_data.add(pole.bounds.to_str())
            else:
                continue
            # 从现在开始，遍历所有点，如果与当前点垂直平行，则加入group
            group:List[Tuple[List[QueryItem],QueryItem]]=[]
            for item in self.elevation:
                _,_,after_pole=item[0]
                if after_pole.bounds.to_str() in all_in_data or after_pole.bounds.to_str()==pole.bounds.to_str():
                    continue
                else:
                    all_in_data.add(after_pole.bounds.to_str())
                    center_point=after_pole.bounds.center_point()
                    if center_point.x>=pole.bounds.minx and center_point.x<=pole.bounds.maxx:
                        group.append(item)
            candidate_groups.append(group)
        def parse_value(item:QueryItem)->float:
            value=item.text
            if value!=None and re.match(r"^[+-]?(?:%%[pP]\s*)?\d+(?:\.\d+)?$",value):
                try:
                    value=float(value.replace("%%p","").replace("%%P","").strip())
                    return value
                except:
                    return 0.0
            else:
                return 0.0
        for group in candidate_groups:
            if len(group)<2:
                continue
            # 对group进行排序，从大到小
            group.sort(key=lambda x:parse_value(x[-1]),reverse=True)
            values=[parse_value(item[-1]) for item in group]
            # 计算后一个值与前一个值的差值
            diffs=[round(values[i]-values[i+1],2) for i in range(len(values)-1)]
            group_result.append((group,values,diffs))
        return group_result
    
    
    

@dataclass
class DwgFileContext(BaseFileContext):
    table_content_list:List[str]=field(default_factory=list,metadata={"help":"表格内容列表"})
    text_list:List[QueryItem]=field(default_factory=list,metadata={"help":"文本列表"})
    facade_content_list:List[FacadeContext]=field(default_factory=list,metadata={"help":"立面内容列表"})
    mapid:Optional[str]=field(default=None,metadata={"help":"地图ID"})
    fileid:Optional[str]=field(default=None,metadata={"help":"文件ID"})
    uploadname:Optional[str]=field(default=None,metadata={"help":"上传名称"})


@dataclass
class BusinessModelItem:
    building_model_name:str=field(default="",metadata={"help":"业态名称"})
    building:List[BaseFileContext]=field(default_factory=list,metadata={"help":"建筑"})
    structure:List[BaseFileContext]=field(default_factory=list,metadata={"help":"结构"})
    facade:List[BaseFileContext]=field(default_factory=list,metadata={"help":"立面"})
    
@dataclass
class BusinessModel:
    model_names:List[str]=field(default_factory=list,metadata={"help":"业态名称列表"})
    models:Dict[str,BusinessModelItem]=field(default_factory=dict,metadata={"help":"业态信息"})

@dataclass
class ProjectContext:
    root_dir:str=field(metadata={"help":"CAD项目根目录"})
    tender_document_context:List[BaseFileContext]=field(default_factory=list,metadata={"help":"招标相关上下文"})
    building_design_document_context:List[BaseFileContext]=field(default_factory=list,metadata={"help":"建筑设计说明相关上下文"})
    basement_document_context:List[BaseFileContext]=field(default_factory=list,metadata={"help":"地下室相关上下文"})
    defense_document_context:List[BaseFileContext]=field(default_factory=list,metadata={"help":"人防相关上下文"})
    construction_cost_document_context:List[BaseFileContext]=field(default_factory=list,metadata={"help":"计价文件上下文"})
    
    business_model:Optional[BusinessModel]=field(default=None,metadata={"help":"业态信息"})
    
    project_name:str=field(init=False,metadata={"help":"项目名称"})
    
    
    
    def get_contents_by_scope(self,scope:ContextScope)->List[BaseFileContext]:
        if scope==ContextScope.TENDER: # 获取招标上下文
            return self.tender_document_context
        elif scope==ContextScope.BUILDING_DESIGN: # 获取建筑总设计说明上下文
            return self.building_design_document_context
        elif scope==ContextScope.BASEMENT: # 获取地下室相关说明上下午
            return self.basement_document_context
        elif scope==ContextScope.DEFENSE: # 获取人防相关说明上下文
            return self.defense_document_context
        elif scope==ContextScope.CCD: # 获取计价文件上下文
            return self.construction_cost_document_context
        else:
            raise ValueError(f"不存在上下文【{scope.value()}】类型")
    
    def __post_init__(self):
        self.project_name = os.path.basename(self.root_dir)  # 获取文件名（带后缀）