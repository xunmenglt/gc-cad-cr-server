import sys
sys.path.insert(0,'/opt/data/private/liuteng/code/gc-cad-cr/src')
from vjmap.services import (
    UploadMAPService,
    QueryFeaturesService,
    QueryFeaturesParams,
    OpenmapService,
    OpenMapRequestParams,
    MapPngByBoundsService,
    MapPngByBoundsParams
)
import tqdm
from vjmap.items import (
    QueryItem,
    EnvelopBounds
)
from parser.text_parser import MapTextParser
from splitter.cad_splitter import CADSubMapSplitter
from typing import List,Dict,Literal,Union,Tuple
import re

# 上传文件
uploadService=UploadMAPService()
res=uploadService.upload_file("/opt/data/private/liuteng/code/gc-cad-cr/data/input/b001中心区N1区学校/业态/宿舍楼/立面/N1宿舍楼建筑_t3.dwg")
print(res)
mapid=res["mapid"]
fileid=res["fileid"]
uploadname=res["uploadname"]

# 打开地图
openmapService=OpenmapService()
params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
res=openmapService.openmap(mapid=mapid,params=params)
print(res)

# 分割子图
splitter=CADSubMapSplitter(mapid=mapid,level=4)
res=splitter.split()

all_rects=splitter.all_rects
all_rects=[rect["bounds"] for rect in all_rects]

# 获取图纸中的文字
map_text_parser=MapTextParser(mapid=mapid,geom=True)

text_list_query_items=map_text_parser.parse_all_text_from_map()

keys=["立面","剖面"]


# 获取所有包含关键字的text_item
def get_key_text_items(keys:List[str],text_list_query_items:List[QueryItem]):
    text_items:List[QueryItem]=[]
    for text_item in text_list_query_items:
        if text_item.text:
            if any([key in text_item.text for key in keys]):
                text_items.append(text_item)
    return text_items


def verify_item_is_right(text_item:QueryItem,proportion_items:QueryItem)->bool:
    # 构建一个矩形范围，是text_item宽的3倍，高是text_item高上下的2倍
    text_item_height=text_item.bounds.height()
    text_item_width=text_item.bounds.width()
    minx=text_item.bounds.minx
    miny=text_item.bounds.miny-text_item_height*2
    maxx=text_item.bounds.maxx+text_item_width*3
    maxy=text_item.bounds.maxy+text_item_height*2
    rect=EnvelopBounds(minx,miny,maxx,maxy)
    # 判断proportion_items是否在rect范围内
    return rect.is_contains(proportion_items.bounds)
    


# 过滤非必要的关键词数据
def filter_key_text_items(text_items:List[QueryItem],text_list_query_items:List[QueryItem]):
    # 先找到 ‘1:’ 开头的数据    
    proportion_items=[]
    pattern = r"^1:[0-9]{2,4}$"
    for item in text_list_query_items:
        if item.text and re.fullmatch(pattern, item.text):
            proportion_items.append(item)
    # 候选数据
    candidate_items=[]
    for text_item in text_items:
        for proportion_item in proportion_items:
            if verify_item_is_right(text_item,proportion_item):
                candidate_items.append((text_item,proportion_item))
                proportion_items.remove(proportion_item)
                break
    return candidate_items


def get_key_text_items_with_filter(keys:List[str],text_list_query_items:List[QueryItem]):
    text_items=get_key_text_items(keys,text_list_query_items)
    candidate_items=filter_key_text_items(text_items,text_list_query_items)
    return [text_item for text_item,_ in candidate_items]


text_items=get_key_text_items_with_filter(keys,text_list_query_items)
            
print(f"当前数据有{len(text_items)}条")
print(text_items)


# 获取包含关键字的子图
def get_submaps_by_text_items(text_items:List[QueryItem],all_rects:List[EnvelopBounds])->List[EnvelopBounds]:
    submaps:List[EnvelopBounds]=[]
    for text_item in text_items:
        for rect in all_rects:
            if rect.is_contains(text_item.bounds):
                submaps.append(rect)
    # 判断当前子图是否被包含在其他子图中
    delete_indices=[]
    for i, submap in enumerate(submaps):
        for j, other_submap in enumerate(submaps):
            if i != j and submap.is_contains(other_submap):  # 改了这里
                delete_indices.append(i)  # 删除的是当前“父图”
                break
    
    # 保留不是父图的
    result = [s for idx, s in enumerate(submaps) if idx not in delete_indices]
    
    # 去重
    result = list({tuple(r.to_dict().values()) : r for r in result}.values())
    
    return result

submaps=get_submaps_by_text_items(text_items,all_rects)
submaps=submaps[:1]
print(f"当前数据有{len(submaps)}条")
print(submaps)


# 所有子图中的文字和线条
elevation_line_type="AcDbLine"
elevation_lines=splitter.query_ent_type_map_items[elevation_line_type]


def get_elevation_data(text_items:List[QueryItem],lines:List[QueryItem])->List[Tuple[List[QueryItem],QueryItem]]:
    """
    获取标高数据
    """
    # 先找小旗子
    pole_flags:List[Tuple[QueryItem,Tuple[QueryItem]]]=[] # 用于保存旗杆
    should_skip_items=set()
    # 左侧边\
    left_sides:List[QueryItem]=[]
    # 右侧边/
    right_sides:List[QueryItem]=[]
    other_items:List[QueryItem]=[]
    tol=1e-4
    
    for side in tqdm.tqdm(lines,desc="finding side..."):
        if len(side.points)!=2:
            continue
        if (
            abs(side.bounds.minx-side.bounds.maxx)<=tol or
            abs(side.bounds.miny-side.bounds.maxy)<=tol
        ):
            other_items.append(side)
            continue
        delta_x=side.points[0].x-side.points[1].x
        delta_y=side.points[0].y-side.points[1].y
        if delta_x<0:
            delta_x=-1
        elif delta_x>0:
            delta_x=1
        else:
            continue
        if delta_y<0:
            delta_y=-1
        elif delta_y>0:
            delta_y=1
        else:
            continue
        if delta_x*delta_y<0:
            left_sides.append(side)
        else:
            right_sides.append(side)
            
    for left_side in tqdm.tqdm(left_sides,desc="finding flags..."):
        for right_side in right_sides:
            if(
                abs(left_side.bounds.miny-right_side.bounds.miny)>=tol or
                abs(left_side.bounds.maxy-right_side.bounds.maxy)>=tol or
                abs(left_side.bounds.maxx-right_side.bounds.minx)>=tol
            ):
                continue
            for pole in other_items:
                if (pole.bounds.to_str() in should_skip_items) or pole==left_side or pole==right_side or len(pole.points)!=2 or abs(pole.bounds.height())>=tol or abs(pole.bounds.width())<tol:
                        continue
                if (
                        (
                            abs(pole.bounds.minx-left_side.bounds.minx)<tol and \
                            abs(pole.bounds.maxy-left_side.bounds.maxy)<tol and \
                            abs(pole.bounds.maxx-right_side.bounds.maxx)>=tol
                        ) or \
                        (
                            abs(pole.bounds.maxx-right_side.bounds.maxx)<tol and \
                            abs(pole.bounds.maxy-right_side.bounds.maxy)<tol and \
                            abs(pole.bounds.minx-left_side.bounds.minx)>tol
                        ) or \
                        (
                            abs(pole.bounds.minx-left_side.bounds.minx)>=tol and 
                            abs(pole.bounds.maxy-left_side.bounds.maxy)<tol and 
                            pole.bounds.minx>left_side.bounds.minx and 
                            pole.bounds.minx<right_side.bounds.maxx and
                            pole.bounds.maxx>right_side.bounds.maxx
                        ) or \
                        (
                            abs(pole.bounds.maxx-right_side.bounds.maxx)>=tol and 
                            abs(pole.bounds.maxy-left_side.bounds.maxy)<tol and 
                            pole.bounds.maxx>left_side.bounds.minx and 
                            pole.bounds.maxx<right_side.bounds.maxx and
                            pole.bounds.minx<left_side.bounds.minx
                        )
                ):
                    pole_flags.append((pole,(left_side,right_side,pole)))
                    should_skip_items.update([left_side.bounds.to_str(),right_side.bounds.to_str(),pole.bounds.to_str()])
                    break
    # 找上方的数字信息
    pattern=re.compile(r"^(?:%%P)?-?\d+(?:\.\d+)$")
    
    # 先找到符合正则要求的text_item
    number_text_items:List[QueryItem]=[]
    for text_item in text_items:
        if re.match(pattern,text_item.text):
            number_text_items.append(text_item)
    result=[]
    # 再找出符合要求的text_item
    for pole_flag,triate in pole_flags:
        pole_flag_width=pole_flag.bounds.width()
        minx=pole_flag.bounds.minx-pole_flag_width*0.25
        maxx=pole_flag.bounds.maxx+pole_flag_width*0.25
        candidate_text_items=[]
        
        for number_item in number_text_items:
            if (
                number_item.bounds.miny>pole_flag.bounds.maxy and \
                number_item.bounds.minx>minx and \
                number_item.bounds.maxx<maxx
            ):
                candidate_text_items.append(number_item)
        # 排序
        if len(candidate_text_items)>0:
            candidate_text_items.sort(key=lambda x:x.bounds.miny)
            candidate_text_item=candidate_text_items[0]
            result.append((triate,candidate_text_item))
    return result

# def get_elevation_data(text_items:List[QueryItem],lines:List[QueryItem])->List[Tuple[List[QueryItem],QueryItem]]:
#     # 先找小旗子
#     pole_flags:List[Tuple[QueryItem,Tuple[QueryItem]]]=[] # 用于保存旗杆
#     should_skip_items=set()
#     for left_side in tqdm.tqdm(lines):
#         if left_side.bounds.to_str() in should_skip_items:
#             continue
#         for right_side in lines:
#             if right_side==left_side or right_side.bounds.to_str() in should_skip_items:
#                 continue
#             if (
#                 len(left_side.points)==2 and 
#                 len(right_side.points)==2 and 
#                 abs(left_side.bounds.minx-left_side.bounds.maxx)>1e-6 and
#                 abs(left_side.bounds.miny-left_side.bounds.maxy)>1e-6 and 
#                 abs(right_side.bounds.minx-right_side.bounds.maxx)>1e-6 and 
#                 abs(right_side.bounds.miny-right_side.bounds.maxy)>1e-6 and 
#                 abs(left_side.bounds.miny-right_side.bounds.miny)<1e-6 and
#                 abs(left_side.bounds.maxy-right_side.bounds.maxy)<1e-6 and 
#                 abs(left_side.bounds.maxx-right_side.bounds.minx)<1e-6
#             ):
#                 for pole in lines:
#                     if (pole.bounds.to_str() in should_skip_items) or pole==left_side or pole==right_side or len(pole.points)!=2 or abs(pole.bounds.height())>1e-6 or abs(pole.bounds.width())<1e-6:
#                         continue
#                     if (
#                             (
#                                 abs(pole.bounds.minx-left_side.bounds.minx)<1e-6 and \
#                                 abs(pole.bounds.maxy-left_side.bounds.maxy)<1e-6 and \
#                                 abs(pole.bounds.maxx-right_side.bounds.maxx)>1e-6
#                             ) or \
#                             (
#                                 abs(pole.bounds.maxx-right_side.bounds.maxx)<1e-6 and \
#                                 abs(pole.bounds.maxy-right_side.bounds.maxy)<1e-6 and \
#                                 abs(pole.bounds.minx-left_side.bounds.minx)>1e-6
#                             )
#                         ):
#                         pole_flags.append((pole,(left_side,right_side,pole)))
#                         should_skip_items.update([left_side.bounds.to_str(),right_side.bounds.to_str(),pole.bounds.to_str()])
#                         break
#     # 找上方的数字信息
#     pattern=re.compile(r"^(?:%%P)?-?\d+(?:\.\d+)$")
    
#     # 先找到符合正则要求的text_item
#     number_text_items:List[QueryItem]=[]
#     for text_item in text_items:
#         if re.match(pattern,text_item.text):
#             number_text_items.append(text_item)
#     result=[]
#     # 再找出符合要求的text_item
#     for pole_flag,triate in pole_flags:
#         pole_flag_width=pole_flag.bounds.width()
#         minx=pole_flag.bounds.minx-pole_flag_width*0.25
#         maxx=pole_flag.bounds.maxx+pole_flag_width*0.25
#         candidate_text_items=[]
        
#         for number_item in number_text_items:
#             if (
#                 number_item.bounds.miny>pole_flag.bounds.maxy and \
#                 number_item.bounds.minx>minx and \
#                 number_item.bounds.maxx<maxx
#             ):
#                 candidate_text_items.append(number_item)
#         # 排序
#         if len(candidate_text_items)>0:
#             candidate_text_items.sort(key=lambda x:x.bounds.miny)
#             candidate_text_item=candidate_text_items[0]
#             result.append((triate,candidate_text_item))
#     return result
            
    
                    


def organize_submap_data(text_list_query_items:List[QueryItem],submaps:List[EnvelopBounds],elevation_lines:List[QueryItem])->List[Dict[Literal["submap","text_items","candidate_lines","elevation"],Union[List[QueryItem],EnvelopBounds,List[Tuple[List[QueryItem],QueryItem]]]]]:
    result:List[Dict[
                        Literal["submap","text_items","candidate_lines","elevation"],
                        Union[
                            List[QueryItem],
                            EnvelopBounds,
                            List[Tuple[List[QueryItem],QueryItem]]
                        ]
                    ]
                ]=[]
    for submap in submaps:
        text_items=[]
        candidate_lines=[]
        for text_item in text_list_query_items:
            if submap.is_contains(text_item.bounds):
                text_items.append(text_item)
        for line in elevation_lines:
            if submap.is_contains(line.bounds) and len(line.points)==2:
                candidate_lines.append(line)
        
        # 获取标高数据
        elevation=get_elevation_data(text_items,candidate_lines)
        
        result.append({
            "submap":submap,
            "text_items":text_items,
            "candidate_lines":candidate_lines,
            "elevation":elevation
        })
    return result

# 截图
# 对子图进行排序                
save_dir="data/images"
mapPngByBoundsService=MapPngByBoundsService(mapid)
idx=1
for rect in tqdm.tqdm(submaps,desc=f"子图转图片中【{save_dir}】"):
    url=mapPngByBoundsService.map_to_img_url(params=MapPngByBoundsParams(
        width=2048,
        bbox=rect.to_str()
    ))
    image_name=f"{mapid}_{idx:03d}.png"
    end_save_dir=f"{save_dir}/{mapid}"
    mapPngByBoundsService.url_to_img(img_url=url,image_name=image_name,save_dir=end_save_dir)
    idx+=1

submap_datas=organize_submap_data(text_list_query_items,submaps,elevation_lines)

print(f"子图数量：{len(submaps)}")






for submap_data in submap_datas:
    print("-"*10)
    
    submap=submap_data["submap"]
    text_items=submap_data["text_items"]
    candidate_lines=submap_data["candidate_lines"]
    elevation=submap_data["elevation"]
    print(f"子图坐标：{submap.to_str()}")
    print(f"标高数据：")
    for idx,elevation_data in enumerate(elevation):
        left_side,right_side,pole=elevation_data[0]
        number_item=elevation_data[-1]
        print("\t"+"-"*5)
        print("\t"+f"id:{idx}")
        print(f"\t左侧斜边：{left_side.bounds.to_str()}")
        print(f"\t右侧斜边：{right_side.bounds.to_str()}")
        print(f"\t顶部标杆：{pole.bounds.to_str()}")
        print(f"\t标高：{number_item.text}")
    print("-"*10)



