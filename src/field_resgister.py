from extraction.fields import (
    Field,
    BaseValueField,
    LiftValueField,
    AddressValueField,
    CityLevelField,
    BaseCategorizedField,
    DateToDateByDaysField,
    ConstructionPeriodField,
    EngineeringQualityExcellenceStandardsField,
    SingleAreaValueField,
    LandscapeAreaField,
    GreeningRateField,
    OrdinaryParkingSpaceField,
    BuildingAreaForBusinessModelField,
    NumberOfFloorsBusinessModelField,
    ServiceLifeBusinessModelField,
    EarthquakeLevelBusinessModelField,
    StructureTypeBusinessModelField,
    TotalBuildingAreaField,
    AboveGroundBuildingAreaField,
    UndergroundBuildingAreaField,
    BuildingFortificationIntensityBusinessModelField,
    ProjectNameField,
    ChargerNumberField,
    ParkingSpaceNumberField,
    LandAreaField,
    EarthquakeLevelField,
    HeightBusinessModelField,
    StandardHeightBusinessModelField,
    PlotRatioField,
    DegreeCountField,
    TotalHouseholdsField,
    BedCountField,
    RoomCountField,
    BuildingBaseAreaField,
    # 新增的专门字段子类
    GreeningAreaField,
    StartDateField,
    CompletionDateField,
    ConstructionUnitField,
    DesignUnitField,
    CivilDefenseBuildingAreaField,
    FoundationTypeField
)

from extraction.context import ContextScope
FIELDS_POOL=dict()

def regist_field(key_name,field:Field):
    if key_name in FIELDS_POOL:
        return False
    else:
        FIELDS_POOL[key_name]=field
    return True



###################### 通用基础字段 #######################
regist_field(
    "项目名称",
    ProjectNameField(
        name="项目名称",
        field_id="project_name",
        context_scope=[ContextScope.TENDER],
        alias=["标段名称","工程名称"],
        paragraph_keys=["投标须知前附表"],
        is_use_ie=False,
        is_general_candidates=True,
        default_value="暂无项目名称"
    )
)


regist_field(
    "建设性质",
    BaseCategorizedField(
        name="建设性质",
        field_id="construction_nature",
        context_scope=[ContextScope.TENDER],
        classifications=["新建","改建","扩建"],
        paragraph_keys=["工程概况"],
        is_general_candidates=True,
        default_value="新建"
    )
)

regist_field(
    "项目地点",
    AddressValueField(
        name="项目地点",
        field_id="project_location",
        context_scope=[ContextScope.TENDER],
        paragraph_keys=["投标须知前附表"],
        alias=["工程地点","联系地址","地址："],
        is_general_candidates=True,
        default_value="暂无项目地点"
    )
)


regist_field(
    "建设地点等级",
    CityLevelField(
        name="建设地点等级",
        field_id="construction_location_level",
        dependencies=["项目地点"],
        project_fields=FIELDS_POOL,
        default_value="未知"
    )
)


regist_field(
    "一级项目类别",
    BaseCategorizedField(
        name="一级项目类别",
        field_id="primary_project_category",
        context_scope=[ContextScope.TENDER],
        classifications=["居住建筑","学校","办公建筑","体育建筑","卫生建筑","文化建筑","商业建筑","旅馆酒店建筑","交通建筑","居民服务建筑","工业建筑","市政工程","轨道交通工程"],
        classification_suffix="建筑",
        paragraph_keys=["工程概况"],
        classification_map={
            "学校":"教育建筑"
        },
        is_general_candidates=True,
        default_value="未知"
    )
)

#########
regist_field(
    "总建筑面积",
    TotalBuildingAreaField(
        name="总建筑面积",
        field_id="total_building_area",
        dependencies=["地上建筑面积","地下建筑面积"],
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        paragraph_keys=["工程概况","技术经济指标"],
        project_fields=FIELDS_POOL,
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "地上建筑面积",
    AboveGroundBuildingAreaField(
        name="地上建筑面积",
        field_id="above_ground_building_area",
        dependencies=["建筑面积"],
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        paragraph_keys=["工程概况","技术经济指标"],
        alias=["地上总建筑面积"],
        project_fields=FIELDS_POOL,
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "地下建筑面积",
    UndergroundBuildingAreaField(
        name="地下建筑面积",
        field_id="underground_building_area",
        dependencies=["建筑面积"],
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        paragraph_keys=["工程概况","技术经济指标"],
        alias=["地下总建筑面积","地下室总面积"],
        project_fields=FIELDS_POOL,
        is_general_candidates=True,
        default_value=0
    )
)


regist_field(
    "占地面积",
    LandAreaField(
        name="占地面积",
        field_id="land_area",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        alias=["工程建设用地面积","总用地面积","建设用地面积","用地面积"],
        paragraph_keys=["工程概况"],
        is_general_candidates=True,
        default_value=0
    )
)




regist_field(
    "容积率",
    PlotRatioField(
        name="容积率",
        field_id="plot_ratio",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["规定容积率"],
        paragraph_keys=["技术经济指标"],
        is_use_ocr=False,
        is_general_candidates=True,
        default_value=0
    )
)


#########
regist_field(
    "学位数",
    DegreeCountField(
        name="学位数",
        field_id="degree_count",
        context_scope=[ContextScope.TENDER],
        alias=["学位个数","学位"],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "住宅总户数",
    TotalHouseholdsField(
        name="住宅总户数",
        field_id="total_households",
        context_scope=[ContextScope.TENDER],
        alias=["户数"],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "床位数",
    BedCountField(
        name="床位数",
        field_id="bed_count",
        context_scope=[ContextScope.TENDER],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "客房数",
    RoomCountField(
        name="客房数",
        field_id="room_count",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["总客房数"],
        paragraph_keys=["技术经济指标"],
        is_general_candidates=True,
        default_value=0
    )
)


regist_field(
    "投资类型",
    BaseCategorizedField(
        name="投资类型",
        field_id="investment_type",
        context_scope=[ContextScope.TENDER],
        classifications=["政府投资","企业投资","个人投资"],
        alias=["资金来源"],
        paragraph_keys=["投标须知前附表","工程概况"],
        is_general_candidates=True,
        default_value="政府投资"
    )
)


regist_field(
    "造价阶段",
    BaseCategorizedField(
        name="造价阶段",
        field_id="cost_stage",
        context_scope=[ContextScope.TENDER],
        classifications=["估算","概算","招标","预算","结算","决算"],
        classification_suffix="阶段",
        is_general_candidates=True,
        default_value="招标"
    )
)

regist_field(
    "执行清单",
    BaseCategorizedField(
        name="执行清单",
        field_id="execution_list",
        context_scope=[ContextScope.TENDER],
        classifications=["GB50500-2008《建设工程工程量清单计价规范》","GB50500-2013《建设工程工程量清单计价规范》","GB/T50854-2024《房屋建筑与装饰工程工程量计算标准》"],
        alias=["工程量的确定方法"],
        default_value="GB50500-2008《建设工程工程量清单计价规范》",
        is_general_candidates=True
    )
)

regist_field(
    "建筑物基底面积",
    BuildingBaseAreaField(
        name="建筑物基底面积",
        field_id="building_base_area",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["建筑物基地","建筑基底面积"],
        paragraph_keys=["技术经济指标"],
        is_use_ocr=True,
        p_width=6,
        is_general_candidates=True,
        default_value=0
    )
)

#########
regist_field(
    "景观面积",
    LandscapeAreaField(
        name="景观面积",
        field_id="landscape_area",
        dependencies=["占地面积","建筑物基底面积"],
        project_fields=FIELDS_POOL,
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "绿化面积",
    GreeningAreaField(
        name="绿化面积",
        field_id="greening_area",
        context_scope=[ContextScope.BUILDING_DESIGN],
        paragraph_keys=["技术经济指标"],
        alias=["绿地面积"],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "绿化率",
    GreeningRateField(
        name="绿化率",
        field_id="greening_rate",
        dependencies=["绿化面积","占地面积"],
        context_scope=[ContextScope.BUILDING_DESIGN],
        project_fields=FIELDS_POOL,
        is_use_ocr=True,
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "电梯",
    LiftValueField(
        name="电梯",
        field_id="elevator",
        context_scope=[ContextScope.CCD],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "充电桩停车位",
    ChargerNumberField(
        name="充电桩停车位",
        field_id="charger_parking_spaces",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN,ContextScope.BASEMENT],
        alias=["充电桩车位","充电车位","充电桩"],
        return_type="number",
        paragraph_keys=["工程概况","技术经济指标"],
        default_value=0,
        is_general_candidates=True
    )
)

#########

regist_field(
    "总停车位",
    ParkingSpaceNumberField(
        name="总停车位",
        field_id="total_parking_spaces",
        context_scope=[ContextScope.TENDER,ContextScope.BASEMENT,ContextScope.BUILDING_DESIGN],
        alias=["停车位","机动车停车位","停车数量"],
        paragraph_keys=["工程概况","技术经济指标"],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "开工日期",
    StartDateField(
        name="开工日期",
        field_id="start_date",
        context_scope=[ContextScope.TENDER],
        alias=["计划开工日期","计划开工时间"],
        is_general_candidates=True,
        default_value="暂无开工日期"
    )
)

regist_field(
    "竣工日期",
    CompletionDateField(
        name="竣工日期",
        field_id="completion_date",
        context_scope=[ContextScope.TENDER],
        alias=["计划竣工日期","计划竣工时间","计划完工日期"],
        is_general_candidates=True,
        default_value="暂无竣工日期"
    )
)



regist_field(
    "工期",
    ConstructionPeriodField(
        name="工期",
        field_id="construction_period",
        dependencies=["开工日期","竣工日期"],
        project_fields=FIELDS_POOL,
        default_value=0
    )
)

regist_field(
    "基础类型",
    FoundationTypeField(
        name="基础类型",
        field_id="foundation_type",
        context_scope=[ContextScope.TENDER],
        classifications=["条形基础","独立基础","满堂基础","桩基础","桩基工程","桩基"],
        classification_map={
            "桩基工程":"桩基础",
            "桩基":"桩基础"
        },
        is_general_candidates=True,
        default_value="暂无基础类型"
    )
)

#########

regist_field(
    "建设单位",
    ConstructionUnitField(
        name="建设单位",
        field_id="construction_unit",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        alias=["招 标 人"],
        is_general_candidates=True,
        default_value="暂无建设单位"
    )
)

regist_field(
    "设计单位",
    DesignUnitField(
        name="设计单位",
        field_id="design_unit",
        context_scope=[ContextScope.BUILDING_DESIGN],
        alias=["设计有限公司","设计股份有限公司","科技发展有限公司","设计研究总院","设计研究院"],
        is_general_candidates=True,
        default_value="暂无设计单位"
    )
)

regist_field(
    "人防建筑面积",
    CivilDefenseBuildingAreaField(
        name="人防建筑面积",
        field_id="civil_defense_building_area",
        context_scope=[ContextScope.DEFENSE,ContextScope.BUILDING_DESIGN],
        alias=["人防总建筑面积"],
        is_general_candidates=True,
        default_value=0
    )
)

regist_field(
    "抗震等级",
    EarthquakeLevelField(
        name="抗震等级",
        field_id="earthquake_level",
        dependencies=["业态抗震等级"],
        project_fields=FIELDS_POOL,
        default_value="一级"
    )
)

# # # TODO 装配率









# ####################### 业态字段 #######################
regist_field(
    "建筑面积",
    BuildingAreaForBusinessModelField(
        name="建筑面积",
        field_id="building_area",
        is_general_candidates=True,
        default_value=-1
    )
)

regist_field(
    "建筑高度",
    HeightBusinessModelField(
        name="建筑高度",
        field_id="building_height"
    )
)

regist_field(
    "标准层高",
    StandardHeightBusinessModelField(
        name="标准层高",
        field_id="standard_floor_height"
    )
)


regist_field(
    "楼层数",
    NumberOfFloorsBusinessModelField(
        name="楼层数",
        field_id="number_of_floors",
        project_fields=FIELDS_POOL,
        dependencies=["建筑面积"],
        alias=["建筑层数"],
        default_value=-1
    )
)





regist_field(
    "结构类型",
    StructureTypeBusinessModelField(
        name="结构类型",
        field_id="structure_type",
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        is_use_ocr=False,
        alias=["主要结构形式"],
        paragraph_keys=["结构设计等级","结构类型、设计分类等级"],
        default_value="框架剪力墙结构"
    )
)

regist_field(
    "使用年限",
    ServiceLifeBusinessModelField(
        name="使用年限",
        field_id="service_life",
        alias=["设计使用年限"],
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        paragraph_keys=["工程概况","技术经济指标"],
        default_value=50
    )
)

regist_field(
    "业态抗震等级",
    EarthquakeLevelBusinessModelField(
        name="业态抗震等级",
        field_id="business_earthquake_level",
        is_use_ocr=False,
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        alias=["抗震等级","结构安全等级","结构的安全等级","安全等级划分"],
        paragraph_keys=["工程概况","结构设计等级","建筑分类等级","结构类型、设计分类等级"],
        default_value="一级"
    )
)

regist_field(
    "建筑设防烈度",
    BuildingFortificationIntensityBusinessModelField(
        name="建筑设防烈度",
        field_id="building_fortification_intensity",
        is_use_ocr=True,
        context_scope=[ContextScope.TENDER,ContextScope.BUILDING_DESIGN],
        alias=["抗震设防烈度"],
        paragraph_keys=["工程概况"],
        default_value=7
    )
)

