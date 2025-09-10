import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
from api.modules import api_caller

print("开始测试")
res=api_caller.call("ocr",{"file_path":"/opt/data/private/liuteng/code/gc-cad-cr/data/images/a.png"})
print(res)
res=api_caller.call("ie",
    {
        "text": "金融资产管理公司违反金融法律、行政法规的,由中国人民银行依照有关法律和《金融违法行为处罚办法》给予处罚;",
        "entity_type": "公司",
        "relation": "违法法规"
    }
)
print(res)
print("测试结束")