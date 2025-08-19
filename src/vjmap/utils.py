import os
import re
from typing import List
from .items import (
    QueryItem,
    GeoPoint,
    EnvelopBounds
)
from functools import cmp_to_key
from conf.config import VJMAP_ACCESS_TOKEN,VJMAP_SERVICEURL

# 获取基础服务地址
def getServiceUrl():
    if os.environ.get("VJMAP_SERVICEURL"):
        return os.environ["VJMAP_SERVICEURL"]
    else:
        return VJMAP_SERVICEURL
    
def getAccessToken():
    if os.environ.get("VJMAP_ACCESS_TOKEN"):
        return os.environ["VJMAP_ACCESS_TOKEN"]
    else:
        return VJMAP_ACCESS_TOKEN
    
    
    
def geoPointFromString(point_str:str)->List[GeoPoint]:
    point=[]
    res=point_str.split(";")
    for item in res:
        p=item.split(",")
        x=float(p[0])
        y=float(p[1])
        point.append(GeoPoint(x=x,y=y))
    return point 

def get_min_distance(point1:QueryItem, point2:QueryItem):
        x1, y1, x2, y2 = point1.bounds.minx, point1.bounds.miny, point1.bounds.maxx, point1.bounds.maxy
        x3, y3, x4, y4 = point2.bounds.minx, point2.bounds.miny, point2.bounds.maxx, point2.bounds.maxy

        points1 = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        points2 = [(x3, y3), (x4, y3), (x4, y4), (x3, y4)]

        def calculate_distance(px1, py1, px2, py2):
            return ((px1 - px2) ** 2 + (py1 - py2) ** 2) ** 0.5

        def is_overlap(interval1, interval2):
            p1, p2 = interval1
            p3, p4 = interval2
            return (
                (p1 >= p3 and p1 <= p4) or
                (p2 >= p3 and p2 <= p4) or
                (p3 >= p1 and p3 <= p2) or
                (p4 >= p1 and p4 <= p2)
            )

        min_distance = float('inf')

        # Calculate point-to-point distances
        for px1, py1 in points1:
            for px2, py2 in points2:
                distance = calculate_distance(px1, py1, px2, py2)
                if distance < min_distance:
                    min_distance = distance

        # Check for overlapping intervals along x and y axes
        if is_overlap((y1, y2), (y3, y4)):
            for px1 in [x1, x2]:
                for px2 in [x3, x4]:
                    distance = abs(px1 - px2)
                    if distance < min_distance:
                        min_distance = distance

        if is_overlap((x1, x2), (x3, x4)):
            for py1 in [y1, y2]:
                for py2 in [y3, y4]:
                    distance = abs(py1 - py2)
                    if distance < min_distance:
                        min_distance = distance

        return min_distance
    
def layout_coordinate_points(points:List[QueryItem],min_distense=200):
    def compare(a:QueryItem, b:QueryItem):
        p1 = a.bounds
        p2 = b.bounds
        
        if p1.maxx == p2.maxx:
            return p2.miny-p1.miny
        
        if (abs(p1.miny - p2.miny) <= min_distense or
            abs(p1.maxy - p2.miny) <= min_distense or
            abs(p1.miny - p2.maxy) <= min_distense):
            return p1.minx - p2.minx
        
        return p2.miny - p1.miny
    # 使用 cmp_to_key 将比较函数转换为 key 函数
    points.sort(key=cmp_to_key(compare))
    return points
    
def caculate_envelop_bounds(points:List[EnvelopBounds])->EnvelopBounds:
    res=EnvelopBounds()
    res.minx=float('inf')
    res.miny=float('inf')
    res.maxx=float('-inf')
    res.maxy=float('-inf')
    
    for point in points:
        res.minx=min(point.minx,res.minx)
        res.miny=min(point.miny,res.miny)
        res.maxx=max(point.maxx,res.maxx)
        res.maxy=max(point.maxy,res.maxy)
        
    return res
        


def has_fill_marker(text):
    """
    判断字符串中是否包含填空标识。
    参数:
        text (str): 要检查的字符串。

    返回:
        bool: 如果包含填空标识返回 True，否则返回 False。
    """
    pattern = r"_{2,}"  # 匹配两个或更多连续的下划线
    return bool(re.search(pattern, text))


def fill_in_the_blanks(text:str="",values:List[str]=[]):
    if not text:
        return ""
    if not has_fill_marker(text):
        return text
    # 动态填充值的生成函数
    def dynamic_replacement(match):
        nonlocal values
        # 记录替换的次数（可用全局变量或函数属性）
        value=match.group()
        if values:
            value=values[0]
            values=values[1:]
        return f"{value}"
    pattern = r"_{2,}"
    replaced_text = re.sub(pattern, dynamic_replacement, text)
    return replaced_text