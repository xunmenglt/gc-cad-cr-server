import time
import sys
import os
import uuid
sys.path.append(os.getcwd())
from vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapPngByBoundsService,MapPngByBoundsParams
from parser.text_parser import MapTextParser
from vjmap.items import EnvelopBounds
from vjmap.utils import caculate_envelop_bounds
from vjmap.services import UploadMAPService,OpenMapRequestParams,OpenmapService,ExportLayoutParams,ExportLayoutIndex,ExportLayoutService


def get_children_layout(parent_mapid:str,fileid:str,uploadname:str,layoutIndex:int):
    """
    根据父mapid、fileid、uploadname、layoutIndex获取子mapid
    """
    openmapService=OpenmapService()
    open_res=openmapService.open_map(mapid=parent_mapid,params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname))
    layouts=open_res.get("layouts",None)    
    if not layouts:
        layouts=[]
    else:
        layouts=layouts.split(",")
    if layoutIndex>len(layouts):
        raise ValueError(f"布局索引超出范围: {layoutIndex}")
    
    exportLayoutIndex=ExportLayoutIndex(layoutIndex=idx+1)
    exportLayoutParams=ExportLayoutParams(mapid=mapid,layoutIndex=exportLayoutIndex)
    res=exportLayoutService.export(params=exportLayoutParams)
    status=res.get("status",False)
    if not status:
        raise RuntimeError(f"导出布局失败:{layout}")
    file_id=res.get("fileid",None)
    if not file_id:
        raise ValueError(f"导出布局失败:{layoutIndex}")
    children_map_id=uuid.uuid4().hex
    return {
        "mapid":children_map_id,
        "fileid":file_id
    }


openmapService=OpenmapService()

# 1. 打开图纸
## 1.1 上传本地文件到系统
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/dev/gc-cad-cr-server/src/data/file_system/test/A-2-102.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]
params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)

## 1.2 判断当前图纸是否被打开
open_res=openmapService.open_map(mapid=mapid,params=params)
# 2. 判断当前图纸中有多少个
## 2.1 获取布局
layouts=open_res.get("layouts",None)
if not layouts:
    layouts=[]
else:
    layouts=layouts.split(",")
# 3. 分别导出图纸
exportLayoutService=ExportLayoutService()
for idx,layout in enumerate(layouts):
    children_layout=get_children_layout(parent_mapid=mapid,fileid=fileid,uploadname=uploadname,layoutIndex=idx+1)
    children_map_id=children_layout["mapid"]
    file_id=children_layout["fileid"]
    open_res=openmapService.open_map(mapid=children_map_id,params=OpenMapRequestParams(fileid=file_id,uploadname=uploadname))       
    exportLayoutService=ExportLayoutService()
    res=exportLayoutService.get_children_layout(parent_mapid=mapid,fileid=fileid,uploadname=uploadname,layoutIndex=idx+1)
    print(res)
    
    
