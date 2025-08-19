"""
文本解析器
"""
import tqdm
import json
import re
from scipy.spatial import KDTree
import numpy as np
from .base import Parser
from vjmap.services import (
    QueryFeaturesParams,
    QueryFeaturesService,
    MapConstDataService
)
from vjmap.items import (
    QueryItem,
    EnvelopBounds
)
from vjmap.utils import (
    geoPointFromString,
    get_min_distance,
    layout_coordinate_points,
    caculate_envelop_bounds,
    fill_in_the_blanks,
    has_fill_marker
)
from typing import List





class MapTextParser(Parser):
    def __init__(self,mapid:str,version:str="v1",geom:bool=True,**kwargs):
        super(Parser).__init__(**kwargs)
        self.mapid=mapid
        self.version=version
        self.geom=geom
        self.text_list=[]
        self.text_cluster_list=[]
        self.query_ent_types=["AcDbText","AcDbMText","AcDbAttributeDefinition","AcDbAttribute"]
        
    def get_type_name_by_id(self,name):
        for id in self.ent_type_id_map:
            if self.ent_type_id_map[id]==name:
                return id
        return None
    
    def parse_all_text_from_map(self)->List[QueryItem]:
        svc=MapConstDataService()
        self.ent_type_id_map=svc.getConstData(mapid=self.mapid,version=self.version)
        condition=""
        for type_name in self.query_ent_types:
            typeId=self.get_type_name_by_id(type_name)
            if typeId:
                condition=condition + f"name='{typeId}'" +" or "
        condition=condition.strip(" or ")
        
        # 有可能记录数会很多，这里用分页查询
        limit=10000
        beginpos=0
        query_params=QueryFeaturesParams(
            querytype="condition",
            condition=condition,
            fields="objectid,points,envelop,bounds,text", # 只要id,坐标
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
                pbar=tqdm.tqdm(total=query["recordCount"],desc="CAD图纸文本内容解析")
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
        layout_coordinate_points(result)
        self.text_list=result
        return result
    
    
    def is_in_cluster(self,cluster, point, min_distance=1000):
        # min_distance为维杰地图上的矢量距离
        minv=float("inf")
        if not point:
            return False
        for _p in cluster:
            md=get_min_distance(_p, point)
            if minv>md:
                minv=md
            if md <= min_distance:
                return True
        return False
    
    # def text_clusters(self,min_distence=2000):
    #     """
    #     获取文本簇列表
    #     """
    #     if self.text_cluster_list and len(self.text_cluster_list)>0:
    #         return self.text_cluster_list
    #     # 获取所有的文本信息
    #     all_text_list=self.parse_all_text_from_map()
    #     text_cluster_list:List[List[QueryItem]]=[]
    #     for point in tqdm.tqdm(all_text_list,desc="文本聚类中"):
    #         if not point.text or len(point.text)<=2:
    #             continue
    #         if not text_cluster_list or len(text_cluster_list)<=0:
    #             text_cluster_list.append([point])
    #             continue
    #         flag = False
    #         for cluster in text_cluster_list:
    #             flag = self.is_in_cluster(cluster, point, min_distance=min_distence)
    #             if flag:
    #                 cluster.append(point)
    #                 break
    #         if not flag:
    #             text_cluster_list.append([point])
    #     self.text_cluster_list=text_cluster_list
    #     print(f"共有文本簇：{len(text_cluster_list)}")
    #     return self.text_cluster_list
    
    def text_clusters(self, min_distence=2000):
        """
        使用中心点 + KDTree + 自定义bounding box距离判断
        """
        if self.text_cluster_list:
            return self.text_cluster_list

        all_text_list = self.parse_all_text_from_map()
        centers = []
        index_to_item = []

        for item in all_text_list:
            if not item.text or len(item.text) <= 2 or not item.bounds:
                continue
            cx = (item.bounds.minx + item.bounds.maxx) / 2
            cy = (item.bounds.miny + item.bounds.maxy) / 2
            centers.append([cx, cy])
            index_to_item.append(item)

        centers = np.array(centers)
        tree = KDTree(centers)
        visited = set()
        clusters = []

        for i in range(len(index_to_item)):
            if i in visited:
                continue
            # 粗查：查询一定范围内的候选
            candidates = tree.query_ball_point(centers[i], r=min_distence * 2)
            cluster = []
            for j in candidates:
                if j in visited:
                    continue
                # 精查：bounding box 级别判断
                if get_min_distance(index_to_item[i], index_to_item[j]) <= min_distence:
                    cluster.append(index_to_item[j])
                    visited.add(j)
            clusters.append(cluster)

        self.text_cluster_list = clusters
        print(f"共有文本簇：{len(clusters)}")
        return clusters


    
    
    def semantic_localization_from_text_clusters(self,key:str="",min_distence=2000)->List[QueryItem]:
        """
        根据语意匹配文本簇
        """
        text_cluster_list=self.text_clusters(min_distence=min_distence)
        result_clusters:List[List[QueryItem]]=[]
        
        for cluser in text_cluster_list:
            for item in cluser:
                if (key=="" or key==None or key in item.text):
                    result_clusters.append(cluser)
                    break
        
        return result_clusters
        
    def fill_in_the_blanks(self,cluster:List[QueryItem],scale=0.5):
        """
        解决完型填空问题
        :param scale 表示value元素因占据改行高的都少比例
        """
        # 找出有填空的对象
        marker_query_list:List[QueryItem]=[]
        result:List[QueryItem]=[]
        remove_idx=set()
        for i in range(len(cluster)):
            item=cluster[i]
            if has_fill_marker(item.text):
                marker_query_list.append(item)
                result.append(item)
                remove_idx.add(i)
                
        for masker_query in marker_query_list:
            values=[]
            for idx in range(len(cluster)):
                if idx in remove_idx:
                    continue
                overlap_len=0
                p=cluster[idx]
                y1,y2=masker_query.bounds.miny,masker_query.bounds.maxy
                y3,y4=p.bounds.miny,p.bounds.maxy
                
                if y2>=y3 and y2<=y4:
                    overlap_len=y2-y3
                elif (y2>=y4 and y3>=y1) or (y2<=y4 and y1>=y3):
                    overlap_len=y4-y3
                elif y4>=y1 and y3<=y1:
                    overlap_len=y1-y3
                try:
                    if (overlap_len==0 and y4==y3) or (overlap_len/(y4-y3)>=scale and masker_query.bounds.minx<=p.bounds.minx and p.bounds.maxx<=masker_query.bounds.maxx):
                        remove_idx.add(idx)
                        values.append(cluster[idx])
                except:
                    pass
            if values and len(values)>0:
                values.sort(key=lambda p:p.bounds.maxx)
                masker_query.text=fill_in_the_blanks(masker_query.text,[value.text for value in values])
        
        for idx in range(len(cluster)):
            if idx not in remove_idx:
                result.append(cluster[idx])
        return result
        


    def text_cluster_to_content(self,cluster:List[QueryItem],min_distence=200):
        """
        将簇转换成文本内容
        """
        if not cluster:
            return ""
        # 解决完型填空
        cluster=self.fill_in_the_blanks(cluster)
        cluster=layout_coordinate_points(cluster,min_distense=min_distence)
        pre_node=None
        text=""
        for point in cluster:
            if not pre_node:
                pre_node = point.bounds

            if not (
                abs(pre_node.miny - point.bounds.miny) <= min_distence or
                abs(pre_node.maxy - point.bounds.miny) <= min_distence
            ):
                pre_node = point.bounds
                text += "\n"

            text += point.text
            pre_node = point.bounds
        
        return text
        
        
        
    def load(self):
        if self.content is not None:
            return self.content
        # 开始解析内容，获取图纸中所有文本内容，内容按从上到下，从左到右排列
        pass
        