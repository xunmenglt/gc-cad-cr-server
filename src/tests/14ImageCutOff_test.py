import os
import sys

sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')

from pipelines.fileparse_pipelines import DwgTextParsePipeLine
from pipelines.cut_off_pipelines import DwgImageCatOffPipeLine
from api.modules import api_caller
file_path="/opt/data/private/liuteng/code/gc-cad-cr/data/input/合水口人才房学校/建筑设计总说明/建筑设计总说明_t3.dwg"

context=DwgTextParsePipeLine(
    file_path=file_path
).invoke()
cutoff_tool=DwgImageCatOffPipeLine(context)


keys=["容积率","绿化率"]

cut_result=cutoff_tool.invoke(keys,p_width=2)

for key in cut_result:
    print(f"当前识别字段【{key}】:")
    for idx,image_path in enumerate(cut_result[key]):
        res=api_caller.call("ocr",{"file_path":image_path})
        print(f"{idx+1}==>{res}")



