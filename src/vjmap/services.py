import os
import time
import uuid
import json

from api.client import APIClient
from vjmap.items import QueryItem

from vjmap.utils import (
    getAccessToken,
    getServiceUrl
)
from dataclasses import dataclass, field,asdict
from typing import List,Optional,Literal,Dict
from .items import (
    EnvelopBounds,
    TableItem,
    TableAttribute
)





class Service:
    def __init__(self):
        """
        初始化文件上传模块
        :param client: APIClient 实例
        """
        self.client=APIClient(getServiceUrl())

class UploadMAPService(Service):
    
    def upload_file(self, file_path)->dict:
        """
        上传文件接口
        :param file_path: 文件路径
        :return: 接口响应
        """
        endpoint = f"/map/uploads"  # 上传文件的接口地址
        files = {
            'fileToUpload': open(file_path, 'rb')
        }
        params={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="POST", endpoint=endpoint,params=params, files=files)
            return response
        finally:
            files['fileToUpload'].close()
    

@dataclass
class OpenMapRequestParams:
    version: str = ""  # 文件二进制内容
    layer: str = ""  # 样式
    geom: str = True  # 以几何渲染方式打开
    fileid: str = ""  # 文件唯一ID，地图ID第一次打开时需传递fileid
    imageLeft: str = ""  # 图像左上角坐标，第一次打开图像类型时有效
    imageTop: str = ""  # 图像左上角坐标，第一次打开图像类型时有效
    imageResolution: str = ""  # 图像分辨率，第一次打开图像类型时有效
    uploadname: str = ""  # 上传的文件名
    mapfrom: str = ""  # 地图来源参数数(协同图形有效)
    mapdependencies: str = ""  # 地图依赖项(协同图形有效)
    subfrom: str = ""  # 地图来源参数数字(子项的设置)(协同图形有效)
    subdependencies: str = ""  # 地图依赖项数字(子项的设置)(协同图形有效)
    stylename: str = ""  # 样式图层名称
    layeron: List[int] = field(default_factory=list)  # 要开的图层索引列表，格式如[0,1,3]
    layeroff: List[int] = field(default_factory=list)  # 要关的图层索引列表，格式如[2,4]
    clipbounds: str = ""  # 地图裁剪范围，范围如[x1,y1,x2,y2]
    bkcolor: str = 0  # 背景颜色
    lineweight: List[int] = field(default_factory=list)  # 线宽，格式如[1, 1, 1, 0]
    expression: str = ""  # 样式表达式
    secretKey: str = ""  # 如果第一次创建图时要对图加密可设置此key
    accessKey: str = ""  # 如果设置了密码带访问key
    
    def __post_init__(self):
        # 需要校验的字段列表
        required_fields = ["fileid", "uploadname"]
        # 遍历字段列表，逐一校验是否为空
        for field_name in required_fields:
            value = getattr(self, field_name)  # 动态获取字段值
            if not value:  # 判断值是否为 None 或空字符串
                raise ValueError(f"{field_name} 是必需的，不能为空或 None")
            
    def to_dict(self):
        return asdict(self)



class OpenmapService(Service):
    def aopenmap(self,mapid:str,params:OpenMapRequestParams)->dict:
        """
        异步打开地图接口
        :param mapid: 地图id
        :return: 接口响应
        """
        if not mapid:
            raise ValueError("mapid is empty")
        endpoint = f"/map/openmap/{mapid}" 
        params=params.to_dict()
        headers={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="GET", endpoint=endpoint,headers=headers,params=params)
            return response
        finally:
            pass
    def open_map(self,mapid:str,params:OpenMapRequestParams)->dict:
        """
        打开地图接口
        :param mapid: 地图id
        :param params: 打开地图参数
        :return: 接口响应
        """
        while True:
            open_res=self.aopenmap(mapid=mapid,params=params)
            open_status=open_res.get('status',None)
            if open_status=='error':
                print(open_res)
            elif open_status!='finish':
                print(f"当前地图【{mapid}】打开状态为【{open_status}】，等待2秒后重试")
                time.sleep(2)
                continue
            else:
                break
        return open_res
    def openmap(self,mapid:str,params:OpenMapRequestParams)->dict:
        """
        打开地图接口
        :param mapid: 地图id
        :param params: 打开地图参数
        :return: 接口响应
        """
        while True:
            open_res=self.aopenmap(mapid=mapid,params=params)
            open_status=open_res.get('status',None)
            if open_status=='error':
                print(open_res)
            elif open_status!='finish':
                print(f"当前地图【{mapid}】打开状态为【{open_status}】，等待2秒后重试")
                time.sleep(2)
                continue
            else:
                break
        return open_res

@dataclass
class ExportLayoutIndex:
    isExportLayout: bool = True
    layoutIndex: int = 1
    
    def to_dict(self):
        return asdict(self)

    

@dataclass
class ExportLayoutParams:
    mapid: str = ""
    version: str = "v1"
    layoutIndex: ExportLayoutIndex = field(default_factory=ExportLayoutIndex)
    geom: bool = False
    
    def __post_init__(self):
        # 需要校验的字段列表
        required_fields = ["mapid","layoutIndex"]
        # 遍历字段列表，逐一校验是否为空
        for field_name in required_fields:
            value = getattr(self, field_name)  # 动态获取字段值
            if not value:  # 判断值是否为 None 或空字符串
                raise ValueError(f"{field_name} 是必需的，不能为空或 None")
    
    def to_dict(self):
        json_data = asdict(self)
        return json_data
        

class ExportLayoutService(Service):
    def export(self,params:ExportLayoutParams)->dict:
        """
        导出布局接口
        :param mapid: 地图id
        :return: 接口响应
        """
        endpoint = f"/map/cmd/exportLayout/_null/v1" 
        params=params.to_dict()
        headers={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="POST", endpoint=endpoint,headers=headers,data=params)
            return response
        finally:
            pass
    def get_current_map_layout_number(self,mapid:str,fileid:str,uploadname:str):
        """
        根据mapid、fileid、uploadname获取当前地图的布局数量
        """
        openmapService=OpenmapService()
        open_res=openmapService.open_map(mapid=mapid,params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname))
        layouts=open_res.get("layouts",None)    
        if not layouts:
            layouts=[]
        else:
            layouts=layouts.split(",")
        return len(layouts)
    
    def get_children_layout(self,parent_mapid:str,fileid:str,uploadname:str,layoutIndex:int)->Dict[Literal["mapid","fileid"],str]:
        """
        根据父mapid、fileid、uploadname、layoutIndex获取子mapid
        """
        layout_number=self.get_current_map_layout_number(mapid=parent_mapid,fileid=fileid,uploadname=uploadname)
        if layoutIndex>layout_number:
            raise ValueError(f"布局索引超出范围: {layoutIndex}")
        exportLayoutIndex=ExportLayoutIndex(layoutIndex=layoutIndex)
        exportLayoutParams=ExportLayoutParams(mapid=parent_mapid,layoutIndex=exportLayoutIndex)
        print("布局解析参数:")
        print(json.dumps(exportLayoutParams.to_dict(),indent=4))
        res=self.export(params=exportLayoutParams)
        status=res.get("status",False)
        if not status:
            return {
                "mapid":None,
                "fileid":None
            }
        file_id=res.get("fileid",None)
        if not file_id:
            return {
                "mapid":None,
                "fileid":None
            }
        children_map_id=uuid.uuid4().hex
        res={
            "mapid":children_map_id,
            "fileid":file_id
        }
        print(f"布局解析结果：")
        print(json.dumps(res,indent=4))
        return res
        
        
        
class MapMetadataService(Service):
    def getMetaData(self,mapid:str,version:str="v1"):
        """
        获取地图元数据
        :param mapid: 地图id
        :param version: 版本号
        :return: 接口响应
        """
        if not mapid:
            raise ValueError("mapid is empty")
        endpoint = f"/map/cmd/metadata/{mapid}/{version}" 
        headers={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="GET", endpoint=endpoint,headers=headers)
            return response
        finally:
            pass
        
class MapConstDataService(Service):
    def getConstData(self,mapid:str,version:str="v1"):
        """
        获取地图常量数据
        :param mapid: 地图id
        :param version: 版本号
        :return: 接口响应
        """
        if not mapid:
            raise ValueError("mapid is empty")
        endpoint = f"/map/cmd/constData/{mapid}/{version}" 
        headers={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="GET", endpoint=endpoint,headers=headers)
            if response and response.get("entTypeIdMap"):
                return response["entTypeIdMap"]
            return {}
        finally:
            pass
        
class CloseMapService(Service):
    def close(self,mapid:str,version:str="v1"):
        """
        主动关闭打开的地图
        :param mapid: 地图id
        :param version: 版本号
        :return: 接口响应
        """
        if not mapid:
            raise ValueError("mapid is empty")
        endpoint = f"/map/cmd/closemap/{mapid}/{version}" 
        headers={
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="GET", endpoint=endpoint,headers=headers)
            if response and response.get("status"):
                return True
            return False
        finally:
            pass
        
@dataclass
class QueryFeaturesParams:
    querytype: Literal["condition", "rect", "point", "expression"] = "condition"  # 查询类型，如condition, rect, point, expression
    beginpos: int = 0  # 记录开始位置
    bounds: str = ""  # 范围
    condition: str = ""  # 查询条件
    fields: str = ""  # 返回字段列表，以逗号分隔，如"name,objectid"
    geom: bool = True  # 是否为几何图形查询
    includegeom: bool = True  # 是否返回几何图形数据
    isContains: bool = False  # 是否包含关系
    layername: str = ""  # 样式名称
    maxReturnCount: Optional[int|str] = ""  # 返回最多的记录条数
    realgeom: bool = True  # 是否返回真实实体几何
    expr: str = ""  # 表达式
    x: Optional[float] = None  # 点查询x坐标
    y: Optional[float] = None  # 点查询y坐标
    pixelsize: int = 1  # 查询影像像素大小
    zoom: int = 1  # 当前缩放级别
    toMapCoordinate: bool = False  # 是否返回CAD地图坐标,
    limit:int=1000 # 查询限制返回记录数

    def __post_init__(self):
        # 必要字段校验
        required_fields = ["querytype", "condition"]
        for field_name in required_fields:
            value = getattr(self, field_name)
            if not value:
                raise ValueError(f"{field_name} 是必需的，不能为空或 None")

    def to_dict(self):
        return asdict(self)
    

class CreateMapStyleService(Service):
    def __init__(self,**kwargs):
        self.layername=""
        super().__init__(**kwargs)
    
    def get_layername(self,mapid:str,version:str="v1",geom:bool=True) -> str:
        """
        :param mapid: 地图ID
        :param version: 接口版本号
        :geom params: 是否几何渲染
        :return: 接口响应结果
        获取样式名称
        """
        if not mapid:
            raise ValueError("mapid is empty")
        if not version:
            raise ValueError("version is empty")
        if self.layername:
            return self.layername
        endpoint = f"/map/cmd/createMapStyle/{mapid}/{version}"
        params = {
            "geom":geom,
            "token":getAccessToken()
        }
        try:
            response = self.client.send_request(method="GET", endpoint=endpoint,params=params)
            if response and response.get("stylename"):
                self.layername=response["stylename"]
                return response["stylename"]
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to query features: {e}")
        
        

class QueryFeaturesService(CreateMapStyleService):

    def query(self, mapid: str, params: QueryFeaturesParams,version: str="v1") -> dict:
        """
        查询实体接口
        :param mapid: 地图ID
        :param version: 接口版本号
        :param params: 查询参数
        :return: 接口响应结果
        """
        if not mapid:
            raise ValueError("mapid is empty")
        if not version:
            raise ValueError("version is empty")

        # 初始化layername
        if not params.layername:
            layername=self.get_layername(mapid=mapid,version=version,geom=params.geom)
            if not layername:
                raise ValueError("layername is not exist")
            params.layername=layername
        
        endpoint = f"/map/cmd/queryFeatures/{mapid}/{version}"
        headers = {
            "token": getAccessToken()
        }
        data = params.to_dict()
        print(f"querytype【{params.querytype}】===> {params.condition}")
        try:
            response = self.client.send_request(method="POST", endpoint=endpoint, headers=headers, data=data)
            if not response:
                return {
                    "recordCount":-1,
                    "result":[]
                }
            recordCount=response["recordCount"]
            if not response.get("result"):
                result=[]
            else:
                result=response["result"]
            query_items=[]
            for item in result:
                query_item=QueryItem()
                for key,value in item.items():
                    if hasattr(query_item,key):
                        setattr(query_item,key,value)
                query_items.append(query_item)
            return {
                "recordCount":recordCount,
                "result":query_items
            }
        except Exception as e:
            raise RuntimeError(f"Failed to query features: {e}")
        
@dataclass
class MapPngByBoundsParams:
    width: Optional[float|int|str]=None
    height:Optional[float|int|str]=None
    srs:str=""
    bbox: str=""
    mapbounds:str=""
    transparent:Optional[bool|str]=False
    backgroundColor:str='rgb(0,0,0)'
    format:str="image/png"
    service:str="WMS"
    request:str="GetMap"
    layers:str=""
    crs:str=""
    fourParameter:str=""
    token:str=""
    
    
    def to_dict(self):
        if not self.height:
            bounds=EnvelopBounds()
            bounds.from_string(f"[{self.bbox}]")
            self.height=round(
                self.width*bounds.height()/bounds.width()
            )
            bounds=bounds.scale(1.0)
            self.bbox=bounds.to_str()
        params = asdict(self)
        # 将布尔值转换为 "true" 或 "false"
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
        return params

class MapPngByBoundsService(CreateMapStyleService):
    def __init__(self,mapid:str,version:str="v1",geom:bool=True,**kwargs):
        super().__init__(**kwargs)  # 正确调用父类的初始化函数
        self.mapid=mapid
        self.version=version
        self.geom=geom
        self.img_urls=[] # 存放图片地址
    
    
    def map_to_img_url(self,params:MapPngByBoundsParams):
        endpoint = f"/map/cmd/wms/{self.mapid}/{self.version}"
        if not params:
            raise ValueError("params is empty")
        if not params.token:
            params.token=getAccessToken()
        # 初始化layername
        if not params.layers:
            layername=self.get_layername(mapid=self.mapid,version=self.version,geom=self.geom)
            if not layername:
                raise ValueError("layername is not exist")
            params.layers=layername
        params=params.to_dict()
        img_url=self.client.create_request_url(endpoint=endpoint,query_params=params)
        return img_url
    
    
    def url_to_img(self,img_url:str=None,image_name:str="",save_dir:str="data/images"):
        if not img_url:
            return False
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        if not image_name:
            image_name=f"{str(time.time()).replace('.','')}.png"
        save_path=os.path.join(save_dir,image_name)
        self.client.download_image(url=img_url,save_path=save_path)
        print(f"download image success,save path is {save_path}")
        return save_path
        
        
@dataclass
class MapTableExtractParams:
    bounds: str = ""
    cellEmptyRatio: int = 90 # 空值所占最大比例
    cellMaxArea: int = 90 # 单元格最大面积比
    condition: str = "" # 查询条件
    debug: bool = False # debug
    debugInfo: List[str] = None  # 默认初始化为 None，稍后赋值为空列表
    digit: int = 4 # 小数点计算精度
    findChildMapRects: bool = False
    geom: bool = True # 是否图形渲染
    layer: str = ""
    mapid: str = ""
    noHvLineSegCount: int = 0 # 线段中允许折线段数
    searchTableMost: bool = False # 表格数据允许重复
    tableEdgeMinPoint: int = 12 # 表格边框最少点
    tableMaxCellCount: int = 100000 # 单元格最大个数
    tableTextMinCount: int = 4 # 表格文本最少数
    tol: int = 0 # 误差值
    unLinkLineRatio: int = 20 # 未关联线所占最大比例
    version: str = "v1" # 版本号

    def __post_init__(self):
        if self.debugInfo is None:
            self.debugInfo = []
            
    def to_dict(self):
        params = asdict(self)
        # 将布尔值转换为 "true" 或 "false"
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
        return params
            
class MapTableExtractService(CreateMapStyleService):
    def __init__(self,mapid:str,version:str="v1",geom:bool=True,**kwargs):
        super().__init__(**kwargs)  # 正确调用父类的初始化函数
        self.mapid=mapid
        self.version=version
        self.geom=geom
        self.tables=[] # 存放表格数据
    
    
    def extract(self,params:MapTableExtractParams)->List[TableItem]:
        endpoint = f"/map/cmd/extractTable/_null/{self.version}"
        if not params:
            raise ValueError("params is empty")
        
        headers={
            "token":getAccessToken()
        }
        
        params.mapid=self.mapid
        params.geom=self.geom
        params.version=self.version
        
        # 初始化layername
        if not params.layer:
            layername=self.get_layername(mapid=self.mapid,version=self.version,geom=self.geom)
            if not layername:
                raise ValueError("layername is not exist")
            params.layer=layername
        data=params.to_dict()
        try:
            response = self.client.send_request(method="POST", endpoint=endpoint, headers=headers, data=data)
            if not response:
                return []
            tables=response["tables"]
            if not tables:
                tables=[]
            reslut=[]
            for item in tables:
                table_item = TableItem()
                for key,value in item.items():
                    if hasattr(table_item,key):
                        if key=="attr":
                            value=TableAttribute()
                            for attr_key,attr_value in item["attr"].items():
                                if hasattr(value,attr_key):
                                    setattr(value,attr_key,attr_value)
                        elif key=="rect":
                            value=EnvelopBounds().from_string(f"[{value}]")
                        setattr(table_item,key,value)
                reslut.append(table_item)
            return reslut
        except Exception as e:
            raise RuntimeError(f"Failed to query features: {e}")
        