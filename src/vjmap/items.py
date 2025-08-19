"""
相关实体类
"""
import math
from dataclasses import dataclass,field,asdict
from typing import Optional

from dataclasses import dataclass
from typing import Optional,List
import json


class GeoPoint:
    def __init__(self,x:float,y:float):
        self.x=x
        self.y=y

    def distance_to(self,point):
        distance = math.sqrt((self.x - point.x) ** 2 + (self.y - point.y) ** 2)
        return distance
    
    def to_dict(self):
        return {
            "x":self.x,
            "y":self.y
        }
    
    @staticmethod
    def from_dict(data):
        return GeoPoint(**data)
    
    def to_str(self):
        return str(self.x)+","+str(self.y)

@dataclass
class EnvelopBounds:
    minx:Optional[float]=None
    miny:Optional[float]=None
    maxx:Optional[float]=None
    maxy:Optional[float]=None
    
    def is_contains(self,bounds):
        if self.minx<bounds.minx and self.maxx>bounds.maxx and self.miny<bounds.miny and self.maxy>bounds.maxy:
            return True
        else:
            return False
    
    def center_point(self):
        center_x=(self.minx+self.maxx)/2
        center_y=(self.miny+self.maxy)/2
        return GeoPoint(center_x,center_y)
    
    def from_string(self,bounds_str:str):
        bounds=json.loads(bounds_str)
        self.minx=min(bounds[0],bounds[2])
        self.maxx=max(bounds[0],bounds[2])
        self.miny=min(bounds[1],bounds[3])
        self.maxy=max(bounds[1],bounds[3])
        return self
    
    def eq(self,bounds):
        if self.minx==bounds.minx and self.miny==bounds.miny and self.maxy==bounds.maxy and self.maxx==bounds.maxx:
            return True
        return False
        
    def scale(self,p:float=1.0):
        # 计算宽和高
        height=self.height()
        width=self.width()
        
        deta_height=height*(p-1)/2
        deta_width=width*(p-1)/2
        
        return EnvelopBounds(
            minx=self.minx-deta_width,
            miny=self.miny-deta_height,
            maxx=self.maxx+deta_width,
            maxy=self.maxy+deta_height
        )
    
    def height(self):
        return self.maxy-self.miny

    def width(self):
        return self.maxx-self.minx
    
    def to_str(self):
        return f"{self.minx},{self.miny},{self.maxx},{self.maxy}"
    
    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return EnvelopBounds(**data)
        
@dataclass
class QueryItem:
    alpha: Optional[int] = None
    bounds: Optional[str|EnvelopBounds] = None
    color: Optional[int] = None
    colorIndex: Optional[int] = None
    envelop: Optional[str] = None
    geojson: Optional[str] = None
    id: Optional[int] = None
    isEnvelop: Optional[bool] = None
    layerindex: Optional[int] = None
    length: Optional[float] = None
    lineWidth: Optional[int] = None
    linetype: Optional[str] = None
    linetypeScale: Optional[float] = None
    name: Optional[str] = None
    objectid: Optional[str] = None
    points: Optional[str|List[GeoPoint]] = None
    thickness: Optional[int] = None
    xdata: Optional[str] = None
    text: Optional[str] = None
    
    def to_dict(self):
        result = asdict(self)
        # 手动处理嵌套类型
        if isinstance(self.bounds, EnvelopBounds):
            result['bounds'] = self.bounds.to_dict()
        if isinstance(self.points, list) and all(isinstance(p, GeoPoint) for p in self.points):
            result['points'] = [p.to_dict() for p in self.points]
        return result
    
    @staticmethod
    def from_dict(data):
        # 还原 bounds
        bounds = data.get('bounds')
        if isinstance(bounds, dict):
            data['bounds'] = EnvelopBounds.from_dict(bounds)

        # 还原 points
        points = data.get('points')
        if isinstance(points, list) and all(isinstance(p, dict) for p in points):
            data['points'] = [GeoPoint.from_dict(p) for p in points]

        return QueryItem(**data)
    

@dataclass
class TableAttribute:
    cellEmptyRatio:int=-1
    tableCellMaxCount:int=-1
    tableTextCount:int=-1
    unLinkLineRatio:int=-1


@dataclass
class TableItem:
    attr:Optional[TableAttribute]=None
    colCount:int=0
    rowCount:int=0
    cols:List[str]=field(default_factory=list)
    rows:List[str]=field(default_factory=list)
    rect:Optional[EnvelopBounds]=None
    datas:List[List[str]]=field(default_factory=list)
