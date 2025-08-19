import math
import os
import tqdm
import logging
from typing import List,Dict,Any,Literal
import time
from extraction.context import (
    ProjectContext,
    BaseFileContext,
    DwgFileContext,
    BusinessModelItem,
    BusinessModel
)
import random
from pipelines.fileparse_pipelines import get_file_parse_pipeline
from utils.file import get_all_files_in_dir,calculate_file_metadata_md5
from extraction.fields import Field
from utils.thread import xthread,as_completed
from server.task_exec.message import Message
import json



class CADContentIdentifier:
    """CAD内容识别器"""
    
    def __init__(self,project_dir:str,output_dir:str,agent_model_name:str="",extraction_model_name:str=""):
        self.project_dir=project_dir # 项目目录地址
        self.agent_model_name=agent_model_name # AI代理模型
        self.extraction_model_name=extraction_model_name # 抽取模型
        self.project_context=None
        # 初始化项目上下文
        project_name=os.path.basename(project_dir)
        self.project_name=project_name
        self.output_path=os.path.join(output_dir,f"{project_name}.json")
        if os.path.exists(self.output_path):
            self.is_use_tmp=True
        else:
            self.is_use_tmp=False
        self._init_project_context()
    
    
    def _init_document_context(self,label="招标文件")->List[BaseFileContext]:
        document_contexts=[]
        directory=os.path.join(self.project_dir,label)
        if not (os.path.exists(directory) and os.path.isdir(directory)):
            raise ValueError(f"项目{self.project_dir}】中不存在目标【{label}】目录")
        file_paths=get_all_files_in_dir(directory=directory,allowed_extensions=['.dwg','.docx','.doc','.xml'])
        for file_path in tqdm.tqdm(file_paths,desc=f"正在解析【{label}】"):
            pipeline_clazz=get_file_parse_pipeline(file_name_or_path=file_path)
            pipeline=pipeline_clazz(file_path)
            
            file_context=pipeline.invoke(label=label)
                
            
            # # 读取文本内容
            # text_content_list=pipeline.invoke()
            
            # # 表格内容
            # table_content_list=[]
            # text_list=[]
            
            # ext=os.path.splitext(file_path)[-1].lower()
            
            # file_context_clazz=BaseFileContext
            # if ext and "dwg" in ext:
            #     file_context_clazz=DwgFileContext
            #     text_content_list,text_list,table_content_list=text_content_list
            #     # TODO：处理表格上下文
            
            # file_context=file_context_clazz(
            #     file_path=file_path,
            #     text_content_list=text_content_list
            # )
            # if table_content_list and len(table_content_list)>0:
            #     file_context.table_content_list=table_content_list
            # if text_list and len(text_list)>0:
            #     file_context.text_list=text_list
            document_contexts.append(file_context)
            
        return document_contexts
            
    
    def _init_project_context(self)->ProjectContext:
        """初始化项目上下文"""
        if self.is_use_tmp:
            return
        if self.project_context:
            return
        tender_document_context=self._init_document_context("招标文件")
        building_design_document_context=self._init_document_context("建筑设计总说明")
        basement_document_context=self._init_document_context("地下室")
        defense_document_context=self._init_document_context("人防")
        construction_cost_document_context=self._init_document_context("计价文件")
        
        business_model_map={}
        business_model=None
        
        business_dir=os.path.join(self.project_dir,"业态")
        
        if business_dir and os.path.exists(business_dir) and os.path.isdir(business_dir):
            # 获取当前目录下的所有子目录
            subdirs = [name for name in os.listdir(business_dir) if os.path.isdir(os.path.join(business_dir, name))]
            for business_name in subdirs:
                building_label="/".join(["业态",business_name,"建筑"])
                structure_label="/".join(["业态",business_name,"结构"])
                facade_label="/".join(["业态",business_name,"立面"])
                building_context=self._init_document_context(label=building_label)
                structure_context=self._init_document_context(label=structure_label)
                facade_context=self._init_document_context(label=facade_label)
                business_model_map[business_name]=BusinessModelItem(
                    building_model_name=business_name,
                    building=building_context,
                    structure=structure_context,
                    facade=facade_context
                )
            if len(business_model_map)>0:
                business_model=BusinessModel(
                    model_names=subdirs,
                    models=business_model_map
                )
                
        else:
            raise FileNotFoundError("业态信息不存在，请检查目录接口")
        
        self.project_context=ProjectContext(
            root_dir=self.project_dir,
            tender_document_context=tender_document_context,
            building_design_document_context=building_design_document_context,
            basement_document_context=basement_document_context,
            defense_document_context=defense_document_context,
            construction_cost_document_context=construction_cost_document_context,
            business_model=business_model
        )
    
    
    def extract_filds(self, fields: Dict[str, Field], worker_num=1, **kwargs) -> Dict[Literal["general","business_type","project_name"], Any]:
        result = {
            "project_name": "",
            "general": {},
            "business_type": {}
        }

        # 注入代理模型
        for key, field in fields.items():
            if hasattr(field, "agent_model_name"):
                field.agent_model_name = self.agent_model_name

        # 配置日志
        logger = logging.getLogger(__name__)

        # 总任务数
        total_tasks = len(fields)
        if total_tasks == 0:
            logger.warning("没有字段需要抽取")
            return result

        # 检查 tqdm 版本是否支持 callbacks 参数
        import tqdm
        tqdm_version = tqdm.__version__
        logger.info(f"tqdm 版本: {tqdm_version}")

        def progress_callback(progress_info):
            current = progress_info['n']
            total = progress_info['total']
            percentage = (current / total) * 100 if total > 0 else 0
            desc = progress_info.get('desc', '')
            logger.info(f"进度更新: {desc} - {current}/{total} ({percentage:.1f}%)")

            if kwargs.get("queue") and kwargs.get("task_id"):
                kwargs["queue"].put(
                    Message(
                        task_id=kwargs["task_id"],
                        type="PROGRESS",
                        data={"progress": math.floor(percentage)}
                    ).to_dict()
                )

        try:
            pd = tqdm.tqdm(total=total_tasks, desc="字段抽取", unit="task", callbacks=[progress_callback])
        except Exception as e:
            logger.warning("tqdm 版本不支持 callbacks 参数，使用兼容模式")
            pd = tqdm.tqdm(total=total_tasks, desc="字段抽取", unit="task")
            original_update = pd.update
            def new_update(n=1):
                result = original_update(n)
                if kwargs.get("queue") and kwargs.get("task_id"):
                    percentage = (pd.n / pd.total) * 100 if pd.total > 0 else 0
                    kwargs["queue"].put(
                        Message(
                            task_id=kwargs["task_id"],
                            type="PROGRESS",
                            data={"progress": math.floor(percentage)}
                        ).to_dict()
                    )
                return result
            pd.update = new_update

        output_path = os.path.join(kwargs["output_dir"], f"{self.project_name}.json")

        if not self.is_use_tmp:
            logger.info(f"不使用缓存，开始抽取: {output_path}")
            for _, field in fields.items():
                field.parse(context=self.project_context, pd=pd)
            pd.close()

            # 正常抽取逻辑（省略，保持不变）
            for key, field in fields.items():
                if field.is_hidden:
                    continue
                field_id = field.field_id if field.field_id else key

                is_general = getattr(field, "is_general", False)
                if is_general:
                    result["general"][field_id] = {
                        "chinese_name": field.name,
                        "value": field.value,
                        "candidates": field.candidates
                    }
                else:
                    end_value = {"chinese_name": field.name}
                    try:
                        for k, v in field.value.items():
                            candidates = v.get('candidates', [])
                            if field_id == "building_area":
                                total_area = v.get('value', {}).get("total", 0)
                                if total_area <= 0:
                                    total_area = field.default_value
                                other_info = {ik: iv for ik, iv in v.get('value', {}).items() if ik != "total"}
                                end_value[k] = {
                                    "value": total_area,
                                    "other_info": other_info,
                                    "candidates": candidates
                                }
                            else:
                                end_value[k] = {
                                    "value": v['value'] if v['value'] else field.default_value,
                                    "candidates": candidates
                                }
                    except Exception as e:
                        logger.error(f"抽取字段【{field.name}】失败: {e}")
                        raise
                    result["business_type"][field_id] = end_value

            result["project_name"] = self.project_context.project_name

        else:
            # ===== 使用缓存模式：模拟耗时，动态 sleep 控制 =====
            logger.info(f"使用缓存，模拟抽取过程: {output_path}")

            # --- 动态 sleep 参数 ---
            min_total = 120.0   # 2 分钟
            max_total = 240.0   # 6 分钟
            min_sleep = 1.0     # 最小每次 sleep
            max_sleep = 20.0    # 最大每次 sleep
            elapsed_time = 0.0

            for i, (_, field) in enumerate(fields.items()):
                remaining = total_tasks - i
                pd.desc = f"正在抽取【{field.name}】"

                if remaining <= 0:
                    break

                # 计算剩余平均时间范围
                min_needed_per = (min_total - elapsed_time) / remaining if remaining > 0 else 0
                max_allowed_per = (max_total - elapsed_time) / remaining if remaining > 0 else float('inf')

                # 调整本次可 sleep 范围
                low_bound = max(min_sleep, min_needed_per - 2.0)
                high_bound = min(max_sleep, max_allowed_per + 2.0)

                # 确保 low <= high
                sleep_time = random.uniform(low_bound, max(high_bound, low_bound + 0.1))
                sleep_time = round(sleep_time, 2)

                logger.debug(f"第 {i+1}/{total_tasks} 次模拟：sleep {sleep_time}s (累计 ≈{elapsed_time + sleep_time:.2f}s)")
                time.sleep(sleep_time)
                elapsed_time += sleep_time

                pd.update(1)  # 更新进度条

            pd.close()

            # 读取缓存结果
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as fp:
                    result = json.load(fp)
            else:
                logger.warning(f"缓存文件不存在: {output_path}，返回空结果")
                result["project_name"] = self.project_name

        return result

