import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
from vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapPngByBoundsService,MapPngByBoundsParams
from parser.text_parser import MapTextParser
from splitter.cad_splitter import TitleBelowTableSplitter
from vjmap.items import EnvelopBounds
from vjmap.utils import caculate_envelop_bounds

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/input/e001北京大学深圳医院深汕医院项目/建筑设计总说明/深汕人民医院建筑设计总说明.dwg")
print(res)
# res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/01、02 结构设计总说明.dwg")

mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]


map_text_parser=MapTextParser(mapid=mapid,geom=True)

text_list_query_items=map_text_parser.parse_all_text_from_map()

target_text="技术经济指标"


title_splitter=TitleBelowTableSplitter(
    title=target_text,
    text_list=text_list_query_items,
    mapid=mapid
)

path=title_splitter.save_to_image()






