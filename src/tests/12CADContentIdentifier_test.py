import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')

from extraction.identifier import CADContentIdentifier
from extraction.fields import (
    Field,
    BaseValueField,
    AddressValueField,
    CityLevelField,
    BaseCategorizedField,
    DateToDateByDaysField,
    EngineeringQualityExcellenceStandardsField,
    SingleAreaValueField,
    LandscapeAreaField,
    GreeningRateField,
    OrdinaryParkingSpaceField
)
from extraction.context import ContextScope
from conf.config import DATA_TMP_DIR
FIELDS_POOL=dict()

def regist_field(key_name,field:Field):
    if key_name in FIELDS_POOL:
        return False
    else:
        FIELDS_POOL[key_name]=field
    return True


regist_field(
    "项目名称",
    BaseValueField(
        name="项目名称",
        context_scope=[ContextScope.TENDER],
        alias=["标段名称","工程名称"]
    )
)

regist_field(
    "项目地点",
    AddressValueField(
        name="项目地点",
        context_scope=[ContextScope.TENDER],
        alias=["工程地点","联系地址"]
    )
)

regist_field(
    "建设地点等级",
    CityLevelField(
        name="建设地点等级",
        dependencies=["项目地点"],
        project_fields=FIELDS_POOL
    )
)

regist_field(
    "建设性质",
    BaseCategorizedField(
        name="建设性质",
        context_scope=[ContextScope.TENDER],
        classifications=["新建","改建","扩建"],
    )
)

regist_field(
    "一级项目类别",
    BaseCategorizedField(
        name="一级项目类别",
        context_scope=[ContextScope.TENDER],
        classifications=["居住建筑","学校","办公建筑","体育建筑","卫生建筑","文化建筑","商业建筑","旅馆酒店建筑","交通建筑","居民服务建筑","工业建筑","市政工程","轨道交通工程"],
        classification_suffix="建筑",
        classification_map={
            "学校":"教育建筑"
        }
    )
)

regist_field(
    "投资类型",
    BaseCategorizedField(
        name="投资类型",
        context_scope=[ContextScope.TENDER],
        classifications=["政府投资","企业投资","个人投资"],
        alias=["资金来源"]
    )
)

regist_field(
    "造价阶段",
    BaseCategorizedField(
        name="造价阶段",
        context_scope=[ContextScope.TENDER],
        classifications=["估算","概算","招标","预算","结算","决算"],
        classification_suffix="阶段"
    )
)

regist_field(
    "执行清单",
    BaseCategorizedField(
        name="执行清单",
        context_scope=[ContextScope.TENDER],
        classifications=["GB50500-2008《建设工程工程量清单计价规范》","GB50500-2013《建设工程工程量清单计价规范》","GB/T50854-2024《房屋建筑与装饰工程工程量计算标准》"],
        alias=["工程量的确定方法"],
        default_value="GB50500-2008《建设工程工程量清单计价规范》"
    )
)


regist_field(
    "基础类型",
    BaseCategorizedField(
        name="基础类型",
        context_scope=[ContextScope.TENDER],
        classifications=["条形基础","独立基础","满堂基础","桩基础","桩基工程","桩基"],
        classification_map={
            "桩基工程":"桩基础",
            "桩基":"桩基础"
        }
    )
)

regist_field(
    "基础类型",
    BaseCategorizedField(
        name="基础类型",
        context_scope=[ContextScope.TENDER],
        classifications=["条形基础","独立基础","满堂基础","桩基础","桩基工程"],
        classification_map={
            "桩基工程":"桩基础"
        }
    )
)


regist_field(
    "学位数",
    BaseValueField(
        name="学位数",
        context_scope=[ContextScope.TENDER],
        alias=["学位个数","学位"]
    )
)

regist_field(
    "学位数",
    BaseValueField(
        name="学位数",
        context_scope=[ContextScope.TENDER],
        alias=["学位个数","学位"]
    )
)


regist_field(
    "信息价取定时间",
    BaseValueField(
        name="信息价取定时间",
        context_scope=[ContextScope.TENDER],
        alias=["信息价","日    期"]
    )
)

regist_field(
    "工程质量创优标准",
    EngineeringQualityExcellenceStandardsField(
        name="工程质量创优标准",
        context_scope=[ContextScope.TENDER],
        alias=["工程质量标准","工程质量"],
    )
)

regist_field(
    "开工日期",
    BaseValueField(
        name="开工日期",
        context_scope=[ContextScope.TENDER],
        alias=["计划开工日期","计划开工时间"]
    )
)

regist_field(
    "工期",
    BaseValueField(
        name="工期",
        context_scope=[ContextScope.TENDER],
        alias=["计划施工总工期"],
        return_type="number"
    )
)


regist_field(
    "竣工日期",
    DateToDateByDaysField(
        name="竣工日期",
        dependencies=["开工日期","工期"],
        alias=["计划施工总工期"],
        project_fields=FIELDS_POOL
    )
)


regist_field(
    "建设单位",
    BaseValueField(
        name="建设单位",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN]
    )
)

regist_field(
    "设计单位",
    BaseValueField(
        name="设计单位",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["设计有限公司","科技发展有限公司"]
    )
)

regist_field(
    "地下建筑面积",
    SingleAreaValueField(
        name="地下建筑面积",
        context_scope=[ContextScope.BASEMENT],
        alias=["建筑面积"]
    )
)



regist_field(
    "容积率",
    SingleAreaValueField(
        name="容积率",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["规定容积率"]
    )
)

regist_field(
    "占地面积",
    SingleAreaValueField(
        name="占地面积",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        alias=["工程建设用地面积","总用地面积","建设用地面积"]
    )
)

regist_field(
    "建筑物基底",
    SingleAreaValueField(
        name="建筑物基底",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["建筑基底面积"]
    )
)


regist_field(
    "景观面积",
    LandscapeAreaField(
        name="景观面积",
        dependencies=["占地面积","建筑物基底"],
        project_fields=FIELDS_POOL
    )
)

regist_field(
    "绿化面积",
    SingleAreaValueField(
        name="绿化面积",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["绿地面积"]
    )
)

regist_field(
    "绿化率",
    GreeningRateField(
        name="绿化率",
        dependencies=["绿化面积","占地面积"],
        project_fields=FIELDS_POOL
    )
)

regist_field(
    "停车位",
    SingleAreaValueField(
        name="停车位",
        context_scope=[ContextScope.BASEMENT,ContextScope.BUILDING_DESIGN],
        alias=["机动车停车位"],
        is_hidden=True
    )
)

regist_field(
    "充电桩停车位",
    SingleAreaValueField(
        name="充电桩停车位",
        context_scope=[ContextScope.BUILDING_DESIGN,ContextScope.BASEMENT],
        alias=["充电桩车位","充电车位"],
        return_type="number",
        default_value=0
    )
)

regist_field(
    "普通停车位",
    OrdinaryParkingSpaceField(
        name="普通停车位",
        dependencies=["停车位","充电桩停车位"],
        project_fields=FIELDS_POOL
    )
)

if __name__=="__main__":
    project_dir="/opt/data/private/liuteng/code/gc-cad-cr/data/input/罗湖外国语学校"
    identifier=CADContentIdentifier(
        project_dir=project_dir,
        agent_model_name="qwen2.5-7b-instruct"
    )
    import pdb;pdb.set_trace()
    print("开始抽取字段...")
    result=identifier.extract_filds(FIELDS_POOL)
    base_info=result["general"]
    for idx,item in enumerate(base_info.items()):
        key,value=item
        print(f"{idx+1:02d}.【{key}】==>【{value}】")
    import os
    import json
    tmp_dir=os.path.join(DATA_TMP_DIR,'general_data')
    os.makedirs(tmp_dir,exist_ok=True)
    with open(os.path.join(tmp_dir,f"{result['project_name']}.json"),'w',encoding="utf-8") as fp:
        fp.write(json.dumps(result,ensure_ascii=False,indent=4))