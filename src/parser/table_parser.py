"""
表格抽取器
"""

import tqdm
from parser.base import Parser
from vjmap.services import MapTableExtractService,MapTableExtractParams,TableItem
from typing import List

class MapTableparser(Parser):
    def __init__(self,mapid:str,version:str="v1",geom:bool=True,**kwargs):
        super(Parser).__init__(**kwargs)
        self.mapid=mapid
        self.version=version
        self.geom=geom
        self.table_item_list=[]
        self.table_content_list=[]
        self.map_table_extract_service=MapTableExtractService(mapid=mapid,version=version,geom=geom)
    
    
    def extract_table_item_list(self)->List[TableItem]:
        if self.table_item_list and len(self.table_item_list)>0:
            return self.table_item_list
        params = MapTableExtractParams(
                mapid=self.mapid
        )
        self.table_item_list=self.map_table_extract_service.extract(params=params)
        return self.table_item_list
    
    def extract_table_to_content_list(self):
        if self.table_content_list and len(self.table_content_list)>0:
            return self.table_content_list
        self.table_item_list=self.extract_table_item_list()
        for table_item in self.table_item_list:
            item_row=['|'.join(row) for row in table_item.datas]
            table_content="\n".join(item_row)
            self.table_content_list.append(table_content)
        return self.table_content_list
        
        
