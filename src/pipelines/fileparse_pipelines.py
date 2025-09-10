import sys
import os
import time
import json
import tqdm
from typing import List
from lxml import etree


from pipelines.base import PipeLine
from parser.text_parser import MapTextParser
from parser.table_parser import MapTableparser
from parser.facade_parser import FacadeParser
from rag.module.indexing.loader.pdf_loader import CustomizedOcrPdfLoader
from langchain_community.document_loaders import UnstructuredFileLoader
from conf.config import DATA_TMP_DIR
from utils.file import calculate_file_metadata_md5,file_to_markdown,split_paragraphs

from vjmap.services import UploadMAPService,OpenmapService,OpenMapRequestParams
from vjmap.items import (
    QueryItem
)
from extraction.context import DwgFileContext,BaseFileContext,FacadeContext
from splitter.cad_splitter import TitleBelowTableSplitter
from utils.file import image_to_markdown


class FileParsePipeLine(PipeLine):
    
    def __init__(self,file_path):
        super().__init__()
        self.file_path=file_path
        self.tmp_dir="file_parse"
        self.content_list=[]
        self.paragraphs=[]
        self._tmp_check()
    
    def _tmp_check(self):
        md5=calculate_file_metadata_md5(self.file_path)
        ab_dir=os.path.join(DATA_TMP_DIR,self.tmp_dir)
        os.makedirs(ab_dir,exist_ok=True)
        tmp_file_path=os.path.join(ab_dir,f"{md5}.json")
        
        if os.path.exists(tmp_file_path):
            with open(tmp_file_path,'r',encoding="utf-8") as fp:
                self.content_list=json.loads(fp.read())
                print(f"读取缓存【{tmp_file_path}】")
        
        # 判断是否存在文本列表对象数组
        if hasattr(self,'paragraphs') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_paragraphs.json")
            if os.path.exists(tmp_file_path):
                with open(tmp_file_path,'r',encoding="utf-8") as fp:
                    self.paragraphs=json.loads(fp.read())
                    print(f"读取缓存【{tmp_file_path}】")
                    
        # 判断是否存在标高列表对象数组
        if hasattr(self,'facade_content_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_facade_content_list.json")
            if os.path.exists(tmp_file_path):
                with open(tmp_file_path,'r',encoding="utf-8") as fp:
                    self.facade_content_list=[FacadeContext.from_dict(item) for item in json.loads(fp.read())]
                    print(f"读取缓存【{tmp_file_path}】")
        
        # 判断是否存在文本列表对象数组
        if hasattr(self,'text_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_text_list.json")
            if os.path.exists(tmp_file_path):
                with open(tmp_file_path,'r',encoding="utf-8") as fp:
                    self.text_list=[QueryItem.from_dict(item) for item in json.loads(fp.read())]
                    print(f"读取缓存【{tmp_file_path}】")
                    
        if hasattr(self,'table_content_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_table_content_list.json")
            if os.path.exists(tmp_file_path):
                with open(tmp_file_path,'r',encoding="utf-8") as fp:
                    self.table_content_list=json.loads(fp.read())
                    print(f"读取缓存【{tmp_file_path}】")
                
        
    def _tmp(self):
        md5=calculate_file_metadata_md5(self.file_path)
        ab_dir=os.path.join(DATA_TMP_DIR,self.tmp_dir)
        os.makedirs(ab_dir,exist_ok=True)
        tmp_file_path=os.path.join(ab_dir,f"{md5}.json")
        if not os.path.exists(tmp_file_path) and len(self.content_list)>0:
            with open(tmp_file_path,'w',encoding="utf-8") as fp:
                fp.write(json.dumps(self.content_list,ensure_ascii=False,indent=4))
        # 判断是否存在文本列表对象数组
        if hasattr(self,'text_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_text_list.json")
            if not os.path.exists(tmp_file_path):
                with open(tmp_file_path,'w',encoding="utf-8") as fp:
                    text_list=[item.to_dict() for item in self.text_list]
                    fp.write(json.dumps(text_list,ensure_ascii=False,indent=4))
        # 判断是否存在文本列表对象数组
        if hasattr(self,'paragraphs') and len(self.paragraphs)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_paragraphs.json")
            if not os.path.exists(tmp_file_path):
                with open(tmp_file_path,'w',encoding="utf-8") as fp:
                    fp.write(json.dumps(self.paragraphs,ensure_ascii=False,indent=4))
                    
        # 判断是否存在标高列表对象数组
        if hasattr(self,'facade_content_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_facade_content_list.json")
            if not os.path.exists(tmp_file_path):
                with open(tmp_file_path,'w',encoding="utf-8") as fp:
                    facade_content_list=[item.to_dict() for item in self.facade_content_list]
                    fp.write(json.dumps(facade_content_list,ensure_ascii=False,indent=4))
        
        if hasattr(self,'table_content_list') and len(self.content_list)>0:
            tmp_file_path=os.path.join(ab_dir,f"{md5}_table_content_list.json")
            if not os.path.exists(tmp_file_path):
                with open(tmp_file_path,'w',encoding="utf-8") as fp:
                    fp.write(json.dumps(self.table_content_list,ensure_ascii=False,indent=4))
    
    def invoke(self,**kwargs)->BaseFileContext:
        """执行解析"""
        raise NotImplementedError("请实现invoke方法")

class DwgTextParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str,min_distence:int=2000):
        assert file_path
        self.content_list=[]
        self.text_list=[]
        self.table_content_list=[]
        self.facade_content_list=[]
        uploadService=UploadMAPService()
        vj_res=uploadService.upload_file(file_path)
        if vj_res.get('error',None):
            print(vj_res)
            raise RuntimeError(f"上传图纸失败:{file_path}")
        mapid=vj_res["mapid"]
        self.mapid=mapid
        fileid=vj_res["fileid"]
        self.fileid=fileid
        uploadname=vj_res["uploadname"]
        self.uploadname=uploadname
        super().__init__(file_path)
        if self.content_list and len(self.content_list)>0:
            return
        openmapService=OpenmapService()
        params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
        openmapService.openmap(mapid=mapid,params=params)
        self.min_distence=min_distence
        self.map_text_parser=MapTextParser(mapid=mapid,geom=True)
        self.map_table_parser=MapTableparser(mapid=mapid,geom=True)
        self.facade_parser=FacadeParser(mapid=mapid,geom=True)
        
    
    def invoke(self,**kwargs)->BaseFileContext:
        if self.content_list and len(self.content_list)>0:
            file_context=DwgFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list,
                text_list=self.text_list,
                table_content_list=self.table_content_list,
                fileid=self.fileid,
                mapid=self.mapid,
                uploadname=self.uploadname,
                paragraphs=self.paragraphs,
                facade_content_list=self.facade_content_list
            )
            return file_context
        try:
            clusters=self.map_text_parser.text_clusters(min_distence=self.min_distence)
            for cluster in clusters:
                content=self.map_text_parser.text_cluster_to_content(cluster=cluster,min_distence=200)
                self.content_list.append(content)
            table_contents=self.map_table_parser.extract_table_to_content_list()
            self.table_content_list=table_contents
            self.text_list=self.map_text_parser.text_list
            
            label=kwargs.get("label",None)
            if label and label=="建筑设计总说明":
                table_title_list=["技术经济指标","结构设计等级","建筑分类等级",'结构类型、设计分类等级']
                for title in tqdm.tqdm(table_title_list,desc=f"正在抽取【{label}】相关表格"):
                    title_splitter=TitleBelowTableSplitter(
                        title=title,
                        text_list=self.text_list,
                        mapid=self.mapid
                    )
                    path=title_splitter.save_to_image()
                    if path:
                        res=image_to_markdown(image_path=path)
                        if res:
                            self.paragraphs.append({
                                "title": title,
                                "content": res
                            })
            if label and "立面" in label:
                self.facade_content_list=self.facade_parser.load()
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=DwgFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list,
            text_list=self.text_list,
            table_content_list=self.table_content_list,
            facade_content_list=self.facade_content_list,
            fileid=self.fileid,
            mapid=self.mapid,
            uploadname=self.uploadname
        )
        return file_context
    
class DwgTextParseByMapIdAndFileIdPipeLine(FileParsePipeLine):
    def __init__(self,mapid:str,fileid:str,uploadname:str,min_distence:int=2000):
        assert mapid and fileid and uploadname
        self.mapid=mapid
        self.fileid=fileid
        self.uploadname=uploadname
        self.content_list=[]
        self.text_list=[]
        self.table_content_list=[]
        self.facade_content_list=[]
        self.file_path=""
        super().__init__(self.file_path)
        if self.content_list and len(self.content_list)>0:
            return
        openmapService=OpenmapService()
        params=OpenMapRequestParams(fileid=fileid,uploadname=uploadname)
        openmapService.openmap(mapid=mapid,params=params)
        self.min_distence=min_distence
        self.map_text_parser=MapTextParser(mapid=mapid,geom=True)
        self.map_table_parser=MapTableparser(mapid=mapid,geom=True)
        self.facade_parser=FacadeParser(mapid=mapid,geom=True)
        
    
    def invoke(self,**kwargs)->BaseFileContext:
        if self.content_list and len(self.content_list)>0:
            file_context=DwgFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list,
                text_list=self.text_list,
                table_content_list=self.table_content_list,
                fileid=self.fileid,
                mapid=self.mapid,
                uploadname=self.uploadname,
                paragraphs=self.paragraphs,
                facade_content_list=self.facade_content_list
            )
            return file_context
        try:
            clusters=self.map_text_parser.text_clusters(min_distence=self.min_distence)
            for cluster in clusters:
                content=self.map_text_parser.text_cluster_to_content(cluster=cluster,min_distence=200)
                self.content_list.append(content)
            table_contents=self.map_table_parser.extract_table_to_content_list()
            self.table_content_list=table_contents
            self.text_list=self.map_text_parser.text_list
            
            label=kwargs.get("label",None)
            if label and label=="建筑设计总说明":
                table_title_list=["技术经济指标","结构设计等级","建筑分类等级",'结构类型、设计分类等级']
                for title in tqdm.tqdm(table_title_list,desc=f"正在抽取【{label}】相关表格"):
                    title_splitter=TitleBelowTableSplitter(
                        title=title,
                        text_list=self.text_list,
                        mapid=self.mapid
                    )
                    path=title_splitter.save_to_image()
                    if path:
                        res=image_to_markdown(image_path=path)
                        if res:
                            self.paragraphs.append({
                                "title": title,
                                "content": res
                            })
            if label and "立面" in label:
                self.facade_content_list=self.facade_parser.load()
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=DwgFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list,
            text_list=self.text_list,
            table_content_list=self.table_content_list,
            facade_content_list=self.facade_content_list,
            fileid=self.fileid,
            mapid=self.mapid,
            uploadname=self.uploadname
        )
        return file_context
    
    def _tmp_check(self):
        pass
    def _tmp(self):
        pass
    
class DocParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.content_list=[]
        self.paragraphs=[]
        super().__init__(file_path)
        
    
    def invoke(self,**kwargs)->BaseFileContext:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list,
                paragraphs=self.paragraphs
            )
            return file_context
        try:
            # loader=CustomizedOcrDocLoader(file_path=self.file_path)
            # documents=loader.load()
            # contents=[document.page_content for document in documents]
            md_content=file_to_markdown(file_path=self.file_path)
            paragraphs=split_paragraphs(md_content)
            contents=[paragraph['content'] for paragraph in paragraphs]
            self.content_list=contents
            self.paragraphs=paragraphs  
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list,
            paragraphs=self.paragraphs
        )
        return file_context
    
class TXTParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.content_list=[]
        super().__init__(file_path)
        
    
    def invoke(self,**kwargs)->List[str]:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list
            )
            return file_context
        try:
            loader=UnstructuredFileLoader(file_path=self.file_path)
            documents=loader.load()
            contents=[document.page_content for document in documents]
            self.content_list=contents
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list
        )
        return file_context
    
class PDFParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.content_list=[]
        super().__init__(file_path)
    
    def invoke(self,**kwargs)->List[str]:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list
            )
            return file_context
        try:
            loader=CustomizedOcrPdfLoader(file_path=self.file_path)
            documents=loader.load()
            contents=[document.page_content for document in documents]
            self.content_list=contents
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list
        )
        return file_context

class XmlFParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.content_list=[]
        super().__init__(file_path)
    
    def invoke(self,**kwargs)->List[str]:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list
            )
            return file_context
        try:
            tree = etree.parse(self.file_path)  # 替换为你的文件路径
            nodes = tree.xpath('//*')  # 获取所有节点
            matched_values = []
            for node in nodes:
                matched_values.append("|".join(node.attrib.values()))
            self.content_list=matched_values
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list
        )
        return file_context


class PngParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.paragraphs=[]
        super().__init__(file_path)
        
    def invoke(self,**kwargs)->List[str]:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list,
                paragraphs=self.paragraphs
            )
            return file_context
        try:
            res=image_to_markdown(image_path=self.file_path,data_type="png")
            self.content_list=[res]
            self.paragraphs=[{
                "title":"OLE",
                "content":res
            }]
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list,
            paragraphs=self.paragraphs
        )
        return file_context
    
class JpegParsePipeLine(FileParsePipeLine):
    def __init__(self,file_path:str):
        assert file_path
        self.file_path=file_path
        self.content_list=[]
        super().__init__(file_path)
        
    def invoke(self,**kwargs)->List[str]:
        if self.content_list and len(self.content_list)>0:
            file_context=BaseFileContext(
                file_path=self.file_path,
                text_content_list=self.content_list,
                paragraphs=self.paragraphs
            )
            return file_context
        try:
            res=image_to_markdown(image_path=self.file_path,data_type="jpeg")
            self.content_list=[res]
            self.paragraphs=[{
                "title":"OLE",
                "content":res
            }]
        except Exception as e:
            print(e)
            raise RuntimeError("执行异常")
        finally:
            self._tmp()
        file_context=BaseFileContext(
            file_path=self.file_path,
            text_content_list=self.content_list,
            paragraphs=self.paragraphs
        )
        return file_context 



FILE_PARSE_PIPELINE_MAPPING={
    ".doc":DocParsePipeLine,
    ".docx":DocParsePipeLine,
    ".pdf":PDFParsePipeLine,
    ".txt":TXTParsePipeLine,
    ".dwg":DwgTextParsePipeLine,
    ".xml":XmlFParsePipeLine,
    ".png":PngParsePipeLine,
    ".jpg":JpegParsePipeLine,
    ".jpeg":JpegParsePipeLine,
}

def get_file_parse_pipeline(file_name_or_path)->PipeLine:
    name, ext = os.path.splitext(file_name_or_path)
    if ext in FILE_PARSE_PIPELINE_MAPPING:
        return FILE_PARSE_PIPELINE_MAPPING[ext]
    else:
        raise RuntimeError(f"后缀为【{ext}】的文件解析PipeLine不存在")


if __name__=="__main__":
    import json
    file_path="/opt/data/private/liuteng/code/gc-cad-cr/data/input/罗湖外国语学校/建筑设计总说明/建筑设计总说明.dwg"
    pipeline=get_file_parse_pipeline(file_path)(file_path)
    contents=pipeline.invoke()
    with open('/opt/data/private/liuteng/code/gc-cad-cr/data/tmp/e/a.json','w',encoding="utf-8") as fp:
        fp.write(json.dumps(contents,ensure_ascii=False,indent=4))
    file_path="/opt/data/private/liuteng/code/gc-cad-cr/data/input/罗湖外国语学校/招标文件/招标文件.docx"
    pipeline=get_file_parse_pipeline(file_path)(file_path)
    contents=pipeline.invoke()
    with open('/opt/data/private/liuteng/code/gc-cad-cr/data/tmp/e/b.json','w',encoding="utf-8") as fp:
        fp.write(json.dumps(contents,ensure_ascii=False,indent=4))