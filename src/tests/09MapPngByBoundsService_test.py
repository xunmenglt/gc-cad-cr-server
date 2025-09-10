import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr')
from src.vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapPngByBoundsService,MapPngByBoundsParams
from src.splitter.cad_splitter import CADSubMapSplitter
from src.vjmap.items import EnvelopBounds

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/人防设计说明--测试字段：人防面积.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

svc=MapPngByBoundsService(mapid=mapid)


# 注意：这里的bbox代表minx,miny,maxx,maxy
bounds=EnvelopBounds(minx=317475.68096970,miny=26710.62197135,maxx=337390.99795709,maxy=27419.65809307)
params=MapPngByBoundsParams(
    bbox=bounds.scale(1.02).to_str(),
    width=1024
)
url=svc.map_to_img_url(params=params)
print(url)




