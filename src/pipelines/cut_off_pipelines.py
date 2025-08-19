import os
import time
from typing import List,Dict
from vjmap.items import EnvelopBounds
from extraction.context import DwgFileContext
from vjmap.services import OpenmapService,OpenMapRequestParams
from vjmap.services import MapPngByBoundsService,MapPngByBoundsParams


class DwgImageCatOffPipeLine:
    def __init__(self,file_context:DwgFileContext):
        assert file_context
        self.file_context=file_context
    
        mapid=file_context.mapid
        self.mapid=mapid
        fileid=file_context.fileid
        self.fileid=fileid
        uploadname=file_context.uploadname
        self.uploadname=uploadname
        openmapService=OpenmapService()
        params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
        while True:
            print(f"正在解析图纸【{file_context.mapid}】")
            open_res=openmapService.openmap(mapid=mapid,params=params)
            open_status=open_res.get('status',None)
            if open_status=='error':
                raise RuntimeError(f"解析图纸失败:{file_context.mapid}")
            elif open_status!='finish':
                time.sleep(6)
                continue
            else:
                break
        self.svc=MapPngByBoundsService(mapid=mapid)
        
        
    
    def invoke(self,keys:List[str],scale=1.02,p_width=1.0,p_height=1.0)->Dict[str,List]:
        if not self.file_context or not self.file_context.text_list or len(self.file_context.text_list)<=0:
            return []
        if not keys or len(keys)<=0:
            return []
        result={}
        for key in keys:
            key_result=[]
            for text_item in self.file_context.text_list:
                if key in text_item.text:
                    bounds=text_item.bounds
                    # 对坐标值进行宽高进行倍率计算
                    deta_p_width=p_width-1
                    deta_p_height=p_height-1
                    deta_height=bounds.height()*deta_p_height
                    deta_width=bounds.width()*deta_p_width
                    bounds.maxx=bounds.maxx+deta_width
                    bounds.maxy=bounds.maxy+deta_height
                    params=MapPngByBoundsParams(
                        bbox=bounds.scale(scale).to_str(),
                        width=512
                    )
                    url=self.svc.map_to_img_url(params=params)
                    save_dir="data/images"
                    image_name=f"{time.time_ns()}.png"
                    flag=self.svc.url_to_img(img_url=url,image_name=image_name,save_dir=save_dir)
                    if flag:
                        save_path=os.path.join(save_dir,image_name)
                        save_path=os.path.abspath(save_path)
                        key_result.append(save_path)
                    else:
                        print("error:解析图片失败")
            result[key]=key_result
        return result
        