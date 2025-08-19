import os
import json
import tqdm

from splitter.base import Splitter
from typing import List
from vjmap.items import (
    QueryItem,
    GeoPoint,
    EnvelopBounds
)
from vjmap.services import (
    MapConstDataService,
    QueryFeaturesParams,
    QueryFeaturesService,
    MapPngByBoundsParams,
    MapPngByBoundsService
)

from vjmap.utils import(
    geoPointFromString
)

from typing import Dict,List


class CADSubMapSplitter(Splitter):
    def __init__(self,mapid:str,version:str="v1",geom:bool=True,level=0,**kwargs):
        super(Splitter).__init__(**kwargs)
        self.mapid=mapid
        self.version=version
        self.geom=geom
        self.level=level
        self.ent_type_id_map={}
        self.map_rects=[]
        self.all_rects=[]
        self.query_ent_types=['AcDbLine', 'AcDbPolyline', 'AcDb2dPolyline', 'AcDb3dPolyline']
        self.query_ent_type_map_items:Dict[str,List[QueryItem]]={}
        # self.query_ent_types=['AcDbPolyline']
        
    
    
    def get_type_name_by_id(self,name):
        for id in self.ent_type_id_map:
            if self.ent_type_id_map[id]==name:
                return id
        return None
    
    def getmap_lines(self)->List:
        svc=MapConstDataService()
        self.ent_type_id_map=svc.getConstData(mapid=self.mapid,version=self.version)
        condition=""
        for type_name in self.query_ent_types:
            typeId=self.get_type_name_by_id(type_name)
            if typeId:
                condition=condition + f"name='{typeId}'" +" or "
                
        condition=condition.strip(" or ")
        # 有可能记录数会很多，这里用分页查询
        limit=50000
        beginpos=0
        query_params=QueryFeaturesParams(
            querytype="condition",
            condition=condition,
            fields="objectid,points,envelop,bounds,name", # 只要id,坐标
            limit=limit,
            maxReturnCount=limit,
            beginpos=beginpos
        )
        query_service=QueryFeaturesService()
        result:List[QueryItem]=[]
        pbar:tqdm.tqdm=None
        while True:
            query_params.beginpos=beginpos
            query=query_service.query(self.mapid,params=query_params,version=self.version)
            if not query.get("result") or len(query["result"])==0:
                break
            beginpos += limit
            result.extend(query["result"])
            if not pbar:
                pbar=tqdm.tqdm(total=query["recordCount"],desc="CAD图纸线条读取")
            pbar.update(len(query["result"]))
            pbar.refresh()
            if len(result) >= query["recordCount"]:
                break;

        if pbar:
            pbar.close()
        for item in result:
            bounds=json.loads(item.bounds)
            item.bounds=EnvelopBounds(minx=bounds[0],miny=bounds[1],maxx=bounds[2],maxy=bounds[3])
            if item.points:
                item.points=geoPointFromString(item.points)

        # 记录一下所有线条类型的映射关系
        for item in result:
            if item.name in self.query_ent_type_map_items:
                self.query_ent_type_map_items[item.name].append(item)
            else:
                self.query_ent_type_map_items[item.name]=[item]
        return result

    
    def find_all_rect_in_map(self,lines:List[QueryItem]=[]):
        if self.all_rects and len(self.all_rects)!=0:
            return self.all_rects
        all_rects = []
        # 矩形（有可能是四条直线或者 一条多段线4个点（闭合），5个点(闭合）所组成
        # 先查找一条多段线4个点（闭合），5个点(闭合）所组成的矩形
        for e in tqdm.tqdm(lines,desc="寻找单线段组成的矩形"):
            if not e.points:
                continue
            points=e.points
            if points[0] == points[-1]:
                points = points[:-1]
            if len(points) != 4:
                continue
            cx = sum(point.x for point in points) / 4.0
            cy = sum(point.y for point in points) / 4.0
            center=GeoPoint(x=cx,y=cy)
            dist = center.distance_to(points[0])
            if all(abs(center.distance_to(p) - dist) < 1e-6 for p in points):
                rect_obj = {
                    'bounds': e.bounds,
                    'ents': [e.objectid]
                }
                all_rects.append(rect_obj)
        # 再查询由四条直线所组成的矩形
        # 首先找到所有符合的线，条件为：坐标两个点，横线或竖线
        filtered_lines=[]
        for ln in lines:
            points=ln.points
            if len(points) != 2:
                continue
            geo_start:GeoPoint = points[0]
            geo_end:GeoPoint = points[1]
            
            if(abs(geo_start.x-geo_end.x)<=1e-8 and abs(geo_start.y-geo_end.y)<=1e-8):
                continue

            isVLine=abs(geo_start.x-geo_end.x)<=1e-8
            isHLine=abs(geo_start.y-geo_end.y)<=1e-8
            if not (isHLine or isVLine):
                continue
            filtered_lines.append({
                "line":ln,
                "is_horz_line":isHLine,
                "find_flag":False,
                'objectid': ln.objectid,
                "start_point":geo_start.to_str(),
                "end_point":geo_end.to_str(),
            })
        # 构建坐标点字典和实体字典
        coord_point_map = {}
        ent_map = {}
        for ln in filtered_lines:
            ent_map[ln['objectid']] = ln

            for point in [ln['start_point'], ln['end_point']]:
                if point not in coord_point_map:
                    coord_point_map[point] = set()
                coord_point_map[point].add(ln['objectid'])

        # 一个点可能属于多个实体中，coord_point_map用于存储点与实体id的映射
        coord_point_map = {k: list(v) for k, v in coord_point_map.items()}
        
        # 查找下一个线段
        def find_next_line(ln, is_start_point, next_is_hort_line):
            pt = ln['start_point'] if is_start_point else ln['end_point']
            find_lines = coord_point_map.get(pt)
            if not find_lines:
                return None

            idx = next((i for i, e in enumerate(find_lines) if e != ln['objectid'] and e[:3] == ln['objectid'][:3]), -1)

            if idx < 0:
                idx = next((i for i, e in enumerate(find_lines) if e != ln['objectid']), -1)
                if idx < 0:
                    return None

            find_ln = ent_map[find_lines[idx]]

            if find_ln['is_horz_line'] != next_is_hort_line:
                return None

            is_ln_start_point = find_ln['start_point'] != pt
            return {
                'find_line': find_ln,
                'is_start_point': is_ln_start_point
            }
        # 查找矩形
        for ln in tqdm.tqdm(filtered_lines,desc="寻找多线段组成的矩形"):
            if ln['is_horz_line']:
                continue

            if ln['find_flag']:
                continue

            next_line1 = find_next_line(ln, True, True)
            if not next_line1:
                continue

            next_line2 = find_next_line(next_line1['find_line'], next_line1['is_start_point'], False)
            if not next_line2:
                continue

            next_line3 = find_next_line(next_line2['find_line'], next_line2['is_start_point'], True)
            if not next_line3:
                continue

            next_line4 = find_next_line(next_line3['find_line'], next_line3['is_start_point'], False)
            if not next_line4:
                continue

            if next_line4['find_line']['objectid'] == ln['objectid'] and next_line4['is_start_point']:
                ln['find_flag'] = True
                next_line1['find_line']['find_flag'] = True
                next_line2['find_line']['find_flag'] = True
                next_line3['find_line']['find_flag'] = True

                rect_bounds = f"[{ln['start_point']},{next_line2['find_line']['start_point'] if next_line2['is_start_point'] else next_line2['find_line']['end_point']}]"
                bounds=EnvelopBounds()
                bounds.from_string(rect_bounds)
                rect_obj = {
                    'bounds': bounds,
                    'ents': [ln['objectid'], next_line1['find_line']['objectid'], next_line2['find_line']['objectid'], next_line3['find_line']['objectid']]
                }
                all_rects.append(rect_obj)
        self.all_rects = all_rects
        return all_rects
    
    def split(self)->List:
        """
        子图拆分
        """
        level=self.level
        map_rects=[]
        if len(self.map_rects)>0:
            return self.map_rects
        lines = self.getmap_lines()
        all_rects = self.find_all_rect_in_map(lines)
        # 在所有矩形中，只有没有被其他矩形所包含的，才认为是一个新的图的图框
        for i in tqdm.tqdm(range(len(all_rects)),desc="子图查询中"):
            current_level=0
            for j in range(len(all_rects)):
                if i == j:
                    continue  # 如果是自己

                # 判断矩形是否包含
                if all_rects[j]['bounds'].is_contains(all_rects[i]['bounds']):
                    current_level+=1
                    if(current_level>level):
                        break

            if current_level==level:
                map_rects.append(all_rects[i])  # 只被level个矩形包含的，才认为是一个新的图的图框

        self.map_rects = map_rects
        return self.map_rects
        
    def save_sub_maps_to_images(self,width:int=1024,height:int=None,bg:str="rgb(0,0,0)",save_dir="data/images"):
        map_rects=self.split()
        # 对子图进行排序
        map_rects=sorted(map_rects,key=lambda rect:(rect["bounds"].miny,rect["bounds"].minx))
        mapPngByBoundsService=MapPngByBoundsService(self.mapid,self.version,self.geom)
        idx=1
        for rect in tqdm.tqdm(map_rects,desc=f"子图转图片中【{save_dir}】"):
            url=mapPngByBoundsService.map_to_img_url(params=MapPngByBoundsParams(
                width=width,
                height=height,
                bbox=rect['bounds'].to_str()
            ))
            image_name=f"{self.mapid}_{idx:03d}.png"
            end_save_dir=f"{save_dir}/{self.mapid}"
            mapPngByBoundsService.url_to_img(img_url=url,image_name=image_name,save_dir=end_save_dir)
            idx+=1
        return True
    
class TitleBelowTableSplitter(CADSubMapSplitter):
    def __init__(self,title:str,text_list:List[QueryItem],**kwargs):
        self.title=title
        self.text_list=text_list
        self.table:EnvelopBounds=None
        super().__init__(**kwargs)
        self.query_ent_types=['AcDbLine',"AcDbPolyline"]
        self.title_query_item=None
        for query_item in text_list:
            if query_item.text and title in query_item.text:
                self.title_query_item=query_item
                break
        

    def _fileter_lines(self,lines:List[QueryItem]=[]):
        """
        过滤掉非标题下方的线条
        """
        if not self.title_query_item:
            return lines
        title_bounds=self.title_query_item.bounds
        if isinstance(title_bounds, str):
            title_bounds=EnvelopBounds().from_string(title_bounds)
        filtered_lines=[]
        for line in lines:
            if isinstance(line.bounds, str):
                line.bounds=EnvelopBounds().from_string(line.bounds)
            if title_bounds.miny>line.bounds.maxy:
                filtered_lines.append(line)
        return filtered_lines

    def split(self)->EnvelopBounds:
        """
        子图拆分
        """
        level=self.level
        if self.table:
            return self.table
        lines = self.getmap_lines();
        # 过滤掉非标题下方的线条
        lines=self._fileter_lines(lines)
        all_rects = self.find_all_rect_in_map(lines)
        # 在标题下方第一个矩形中，就是我们需要查找的内容
        temporary_selected_rects=[]
        for rect in all_rects:
            bounds=rect['bounds']
            if isinstance(bounds, str):
                bounds=EnvelopBounds().from_string(bounds)
            if (bounds.minx >= self.title_query_item.bounds.minx or abs(bounds.minx-self.title_query_item.bounds.minx)<=10000) and \
                bounds.minx<=self.title_query_item.bounds.maxx and bounds.maxy<=self.title_query_item.bounds.miny:
                temporary_selected_rects.append(rect)
        
        if len(temporary_selected_rects)==0:
            return None
        # 根据坐标maxy坐标进行降序排序
        self.temporary_selected_rects=sorted(temporary_selected_rects,key=lambda rect:rect['bounds'].maxy)
        self.table=self.temporary_selected_rects[-1]['bounds']
        return self.table
        
    def save_to_image(self,width:int=1024,height:int=None,bg:str="rgb(0,0,0)",image_name=None,save_dir="data/images"):
        if not self.title_query_item:
            return None
        bounds=self.split()
        if not bounds:
            return None
        # 对子图进行排序
        mapPngByBoundsService=MapPngByBoundsService(self.mapid,self.version,self.geom)
        url=mapPngByBoundsService.map_to_img_url(params=MapPngByBoundsParams(
                width=width,
                bbox=bounds.scale(1.02).to_str(),
        ))
        image_path=mapPngByBoundsService.url_to_img(img_url=url,image_name=image_name,save_dir=save_dir)
        return image_path