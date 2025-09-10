import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr')
from vjmap.services import UploadMAPService,CreateMapStyleService

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/01、02 结构设计总说明.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

# # 打开地图
# openmapService=OpenmapService()
# params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
# res=openmapService.openmap(mapid=mapid,params=params)


# 获取地图原数据
createMapStyleService=CreateMapStyleService()
res=createMapStyleService.get_layername(mapid=mapid,version="v1",geom=True)
print(res)
