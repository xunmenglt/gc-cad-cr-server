import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
from vjmap.services import UploadMAPService,QueryFeaturesService,QueryFeaturesParams,MapPngByBoundsService,MapPngByBoundsParams
from parser.text_parser import MapTextParser
from splitter.cad_splitter import TitleBelowTableSplitter
from vjmap.items import EnvelopBounds
from vjmap.utils import caculate_envelop_bounds
from utils.openai import openai_chat_by_api,InferenceParams
from conf.config import VL_MODEL_NAME
from utils.file import image_to_base64


# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/input/h002万科浪骑游艇会酒店/建筑设计总说明/T-SW-0001~0003 结构设计总说明.dwg")
print(res)
# res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/test/01、02 结构设计总说明.dwg")

mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]


map_text_parser=MapTextParser(mapid=mapid,geom=True)

text_list_query_items=map_text_parser.parse_all_text_from_map()

target_text="结构设计等级"


title_splitter=TitleBelowTableSplitter(
    title=target_text,
    text_list=text_list_query_items,
    mapid=mapid
)

path=title_splitter.save_to_image()
print("文件路径：{}".format(path))
from utils.openai import openai_chat_by_api,InferenceParams
base64_image=image_to_base64(path)
res=openai_chat_by_api(
    model_name=VL_MODEL_NAME,
    messages=[
        {
            "role":"system",
            "content":[{"type":"text","text": "你是表格识别助手"}],
        },
        {
            "role":"user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}, 
                },
                {"type": "text", "text": "请完整识别并输出图片中的表格内容，将其转换成markdown格式。"},
            ],
        }
    ],
    inference_params=InferenceParams(
        temperature=0,
        max_tokens=4096
    )
)
print(res)





