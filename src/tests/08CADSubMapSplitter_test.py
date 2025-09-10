import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
from vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,OpenmapService,OpenMapRequestParams
from splitter.cad_splitter import CADSubMapSplitter

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/input/a001深圳国际会展中心/业态/幼儿园/建筑/幼儿园_t3_t3.dwg")
print(res)
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

openmapService=OpenmapService()
params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
res=openmapService.openmap(mapid=mapid,params=params)
print(res)

splitter=CADSubMapSplitter(mapid=mapid,level=4)
res=splitter.split()
res.sort(key=lambda x:x['bounds'].minx)
for item in res:
    print(f"{item['bounds'].minx},{item['bounds'].miny},{item['bounds'].maxx},{item['bounds'].maxy}")
print(len(res))

# 子图转图片
splitter.save_sub_maps_to_images(width=2048,save_dir="../data/images")

