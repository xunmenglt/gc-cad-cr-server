
import addressparser


PROVINCE_LEVEL_MAPPING = {
    "一线城市": ["北京市", "上海市", "广州市", "深圳市"],
    "二线城市": [
        "成都市", "重庆市", "杭州市", "武汉市", "苏州市", "西安市", "南京市", "长沙市", "天津市", "郑州市", 
        "东莞市", "无锡市", "宁波市", "青岛市", "合肥市", "佛山市", "大连市", "福州市", "厦门市", "哈尔滨市", 
        "济南市", "温州市", "南宁市", "长春市", "泉州市", "石家庄市", "贵阳市", "南昌市", "金华市", "常州市", 
        "南通市", "嘉兴市", "太原市", "徐州市", "惠州市", "珠海市", "中山市", "台州市", "烟台市", "兰州市", 
        "绍兴市", "海口市", "扬州市"
    ],
    "三四线城市": "除一二线的其他城市"
}

def parse_regions(address:str):
    if not address:
        return ("","","","")
    res=addressparser.transform([address])
    if len(res)<=0:
        return ("","","","")
    # 解析省份信息
    row=res.iloc[0]
    province=row[0]
    city=row[1]
    county=row[2]
    town=row[3]
    return (province,city,county,town)

def get_level_by_city(city_name:str):
    if not city_name:
        return "城市不存在"
    for key,values in PROVINCE_LEVEL_MAPPING.items():
        if city_name in values:
            return key
    return "城市不存在"

region=parse_regions("松岗街道位于中国的广东省深圳市宝安区。松明大道、沙江路与宝安大道的交汇处也位于宝安区。如果您需要更详细的信息，可以告诉我具体的需求。")
address="".join(region)
level=get_level_by_city(region[1])
print(f"{level}:{address}")