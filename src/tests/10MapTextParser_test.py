import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr')
from src.vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapPngByBoundsService,MapPngByBoundsParams
from src.parser.text_parser import MapTextParser
from src.vjmap.items import EnvelopBounds
from src.vjmap.utils import caculate_envelop_bounds

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/人防设计说明--测试字段：人防面积.dwg")
# res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/01、02 结构设计总说明.dwg")

mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]


map_text_parser=MapTextParser(mapid=mapid,geom=True)

text_clusters=map_text_parser.semantic_localization_from_text_clusters(key="总用地面积")
# text_clusters=map_text_parser.semantic_localization_from_text_clusters(key="使用年限")



svc=MapPngByBoundsService(mapid=mapid)

for idx in range(len(text_clusters)):
    cluster=text_clusters[idx]

    content=map_text_parser.text_cluster_to_content(cluster=cluster)
    print(f"簇{idx+1}:{content}")
    bounds=caculate_envelop_bounds([p.bounds for p in cluster])
    # 注意：这里的bbox代表minx,miny,maxx,maxy
    params=MapPngByBoundsParams(
        bbox=bounds.scale(1).to_str(),
        width=1024
    )
    url=svc.map_to_img_url(params=params)
    print(url)
    print("---------------------------")
    




