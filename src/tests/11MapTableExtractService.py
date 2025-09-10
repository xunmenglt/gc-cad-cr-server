import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr')
from src.vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapTableExtractParams,MapTableExtractService,MapPngByBoundsService,MapPngByBoundsParams
from src.splitter.cad_splitter import CADSubMapSplitter

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/N1教学楼建筑_t3.dwg")
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

splitter=CADSubMapSplitter(mapid=mapid,level=1)
res=splitter.split()
res.sort(key=lambda x:x['bounds'].minx)
for item in res:
    print(f"{item['bounds'].minx},{item['bounds'].miny},{item['bounds'].maxx},{item['bounds'].maxy}")
    
    
    params = MapTableExtractParams(
        bounds=item["bounds"].to_str(),
        mapid=mapid
    )
    
    service =  MapTableExtractService(mapid=mapid)
    
    tables=service.extract(params=params)
    print(tables)
    print("========================")
    
    svc=MapPngByBoundsService(mapid=mapid)

    # 注意：这里的bbox代表minx,miny,maxx,maxy
    bounds=item["bounds"]
    params=MapPngByBoundsParams(
        bbox=bounds.to_str(),
        width=4096
    )
    url=svc.map_to_img_url(params=params)
    print(url)
    print(f"表格数量：{len(tables)}")
    print("========================")
    print("========================")
    
    import pdb;pdb.set_trace()


