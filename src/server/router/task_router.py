"""
任务管理路由模块
提供任务的创建、查询、启动、停止、删除等功能
"""

from fastapi import APIRouter, Form, Body, HTTPException, Path
from database.repository import task_repository as repo
from .response import BaseResponse, ListResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from server.task_exec.tasks import CADIdentifyTask
from database.models.task_model import TaskStatus
import threading
import os
from conf.config import AGENT_MODEL_NAME,DATA_TMP_DIR
from datetime import datetime


# 任务响应模型
class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    task_description: str = Field(..., description="任务描述")
    task_params: Dict[str, Any] = Field(default_factory=dict, description="任务参数")
    task_level: int = Field(0, description="任务优先级，0为最高")
    task_status: str = Field(..., description="任务状态")
    task_progress: int = Field(0, description="任务进度百分比")
    task_result: Optional[Dict[str, Any]] = Field(None, description="任务执行结果")
    update_time: str = Field(..., description="更新时间")
    create_time: str = Field(..., description="创建时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_20231201_001",
                "task_name": "CAD图纸识别任务",
                "task_description": "识别CAD图纸中的文字和标注信息",
                "task_params": {"input_file": "drawing.dwg", "confidence": 0.8},
                "task_level": 0,
                "task_status": "completed",
                "task_progress": 100,
                "task_result": {"extracted_text": "示例文字", "annotations": []},
                "update_time": "2023-12-01 10:30:00",
                "create_time": "2023-12-01 10:00:00"
            }
        }


# 创建任务的请求模型
class CreateTaskRequest(BaseModel):
    """创建任务请求模型"""
    task_name: str = Field(..., description="任务名称", min_length=1, max_length=100)
    task_description: str = Field(..., description="任务描述", min_length=1, max_length=500)
    task_params: Dict[str, Any] = Field(default_factory=dict, description="任务参数，JSON格式")
    task_level: int = Field(0, description="任务优先级，0为最高", ge=0, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_name": "CAD图纸识别任务",
                "task_description": "识别CAD图纸中的文字和标注信息",
                "task_params": {"input_file": "drawing.dwg", "confidence": 0.8},
                "task_level": 0
            }
        }


# 任务创建响应模型
class CreateTaskResponse(BaseModel):
    """任务创建响应模型"""
    task_id: str = Field(..., description="新创建的任务ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_20231201_001"
            }
        }


# 任务列表响应模型
class TaskListResponse(BaseResponse):
    """任务列表响应模型"""
    data: List[TaskResponse] = Field(..., description="任务列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": [
                    {
                        "task_id": "task_20231201_001",
                        "task_name": "CAD图纸识别任务",
                        "task_description": "识别CAD图纸中的文字和标注信息",
                        "task_params": {"input_file": "drawing.dwg"},
                        "task_level": 0,
                        "task_status": "completed",
                        "task_progress": 100,
                        "update_time": "2023-12-01 10:30:00",
                        "create_time": "2023-12-01 10:00:00"
                    }
                ]
            }
        }


# 任务详情响应模型
class TaskDetailResponse(BaseResponse):
    """任务详情响应模型"""
    data: TaskResponse = Field(..., description="任务详情")


# 更新任务结果请求模型
class UpdateTaskResultRequest(BaseModel):
    """更新任务结果请求模型"""
    result: Dict[str, Any] = Field(..., description="任务执行结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "result": {
                    "extracted_text": "示例文字内容",
                    "annotations": [
                        {"x": 100, "y": 200, "text": "标注1"},
                        {"x": 300, "y": 400, "text": "标注2"}
                    ],
                    "confidence": 0.95
                }
            }
        }


# 全局任务存储
active_tasks:Dict[str,CADIdentifyTask] = {}
task_lock = threading.Lock()

router = APIRouter()


@router.get(
    "/", 
    response_model=TaskListResponse,
    summary="获取任务列表",
    description="获取系统中所有任务的列表信息，包括任务状态、进度等",
    tags=["任务管理"]
)
def list_tasks():
    """获取任务列表"""
    tasks = repo.get_task_list()
    return BaseResponse(data=tasks)


@router.post(
    "/create", 
    response_model=BaseResponse,
    summary="创建新任务",
    description="创建一个新的CAD图纸识别任务",
    tags=["任务管理"]
)
def create_task(request: CreateTaskRequest = Body(..., description="任务创建参数")):
    """创建新任务"""
    try:
        task = repo.create_task(
            task_name=request.task_name,
            task_description=request.task_description,
            task_params=request.task_params,
            task_level=request.task_level
        )
        return BaseResponse(data=task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get(
    "/{task_id}", 
    response_model=TaskDetailResponse,
    summary="获取任务详情",
    description="根据任务ID获取任务的详细信息，包括执行结果等",
    tags=["任务管理"]
)
def get_task(task_id: str = Path(..., description="任务ID")):
    """获取任务详情"""
    task = repo.get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return BaseResponse(data=task)


@router.delete(
    "/{task_id}", 
    response_model=BaseResponse,
    summary="删除任务",
    description="删除指定的任务，注意：正在运行的任务无法删除",
    tags=["任务管理"]
)
def delete_task(task_id: str = Path(..., description="要删除的任务ID")):
    """删除任务"""
    result = repo.delete_task(task_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return BaseResponse(data=result)


@router.post(
    "/{task_id}/stop", 
    response_model=BaseResponse,
    summary="停止任务",
    description="停止正在运行的任务",
    tags=["任务管理"]
)
def stop_task(task_id: str = Path(..., description="要停止的任务ID")):
    """停止任务"""
    try:
        with task_lock:
            # 检查任务是否在运行
            if task_id not in active_tasks:
                if repo.get_task_info(task_id).task_status == TaskStatus.RUNNING:
                    repo.update_task_status(task_id, TaskStatus.FAILED)
                    return BaseResponse(code=200, msg="任务已停止")
                else:
                    raise HTTPException(status_code=404, detail="任务未在运行")
            
            # 获取任务实例并停止
            task = active_tasks[task_id]
            task.stop()
            
            # 从活跃任务中移除
            active_tasks.pop(task_id, None)
                
            return BaseResponse(code=200, msg="任务停止成功")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务时发生错误: {str(e)}")


def _handle_task_completion(task_id: str, success: bool):
    """处理任务完成回调"""
    try:
        with task_lock:
            # 从活跃任务中移除
            active_tasks.pop(task_id, None)
            # 更新任务状态
            if success:
                repo.update_task_status(task_id, TaskStatus.COMPLETED)
            else:
                repo.update_task_status(task_id, TaskStatus.FAILED)
                
    except Exception as e:
        # 记录错误但不抛出异常，避免影响任务执行
        print(f"处理任务完成回调时发生错误: {e}")


@router.post(
    "/{task_id}/startup", 
    response_model=BaseResponse,
    summary="启动任务",
    description="启动待执行的任务，开始CAD图纸识别处理",
    tags=["任务管理"]
)
def startup_task(task_id: str = Path(..., description="要启动的任务ID")):
    """启动任务"""
    print(f"启动任务: {task_id}")
    try:
        with task_lock:
            # 检查任务是否已经在运行
            if task_id in active_tasks:
                raise HTTPException(status_code=400, detail="任务已在运行中")
            
            # 获取任务信息
            task_info = repo.get_task_info(task_id)
            if not task_info:
                raise HTTPException(status_code=404, detail="任务不存在")
            
            # 检查任务状态
            if task_info.task_status != TaskStatus.PENDING:
                raise HTTPException(status_code=400, detail="任务状态不允许启动")
            
            # 检查是否有其他任务在运行
            if active_tasks:
                raise HTTPException(status_code=500, detail="系统已有任务在运行，稍后重试")
            
            try:
                # 创建任务实例
                output_dir=os.path.join(DATA_TMP_DIR,"extract_results")
                os.makedirs(output_dir, exist_ok=True)
                task = CADIdentifyTask(
                    task_id=task_id,
                    agent_model_name=AGENT_MODEL_NAME,
                    output_dir=output_dir,
                    success_callback=lambda x: _handle_task_completion(task_id, True),
                    fail_callback=lambda x: _handle_task_completion(task_id, False)
                )
                # 启动任务
                task.run()
                active_tasks[task_id] = task
                
                return BaseResponse(code=200, msg="任务启动成功", data=None)
                
            except Exception as e:
                print(f"启动任务时发生错误: {e}")
                if task_id in active_tasks:
                    del active_tasks[task_id]
                raise HTTPException(status_code=500, detail=f"任务启动失败: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"启动任务时发生错误: {e}")
        if task_id in active_tasks:
            del active_tasks[task_id]
        raise HTTPException(status_code=500, detail=f"服务器异常: {str(e)}")
    

@router.post(
    "/{task_id}/update_result", 
    response_model=BaseResponse,
    summary="更新任务结果",
    description="更新任务的执行结果数据",
    tags=["任务管理"]
)
def update_task_result(
    task_id: str = Path(..., description="任务ID"), 
    request: UpdateTaskResultRequest = Body(..., description="任务结果数据")
):
    """更新任务结果数据"""
    try:
        repo.update_task_result(task_id, request.result)
        return BaseResponse(data=request.result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务结果失败: {str(e)}")






