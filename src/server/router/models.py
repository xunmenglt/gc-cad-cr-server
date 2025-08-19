"""
API模型定义
包含所有接口的请求和响应模型
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


# ===================
# 基础响应模型
# ===================

class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(200, description="API状态码")
    msg: str = Field("success", description="API状态消息")
    data: Any = Field(None, description="API数据")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": None
            }
        }


# ===================
# 任务相关模型
# ===================

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


class TaskListResponse(BaseResponse):
    """任务列表响应模型"""
    data: List[TaskResponse] = Field(..., description="任务列表")


class TaskDetailResponse(BaseResponse):
    """任务详情响应模型"""
    data: TaskResponse = Field(..., description="任务详情")


# ===================
# 文件相关模型
# ===================

class FileResponse(BaseModel):
    """文件响应模型"""
    file_id: str = Field(..., description="文件ID")
    file_name: str = Field(..., description="文件名称")
    file_type: str = Field(..., description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    file_suffix: Optional[str] = Field(None, description="文件后缀")
    file_parent: str = Field(..., description="父目录ID")
    file_md5: Optional[str] = Field(None, description="文件MD5值")
    can_delete: bool = Field(True, description="是否可以删除")
    create_time: str = Field(..., description="创建时间")
    update_time: str = Field(..., description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_20231201_001",
                "file_name": "drawing.dwg",
                "file_type": "F",
                "file_size": 1024000,
                "file_suffix": "dwg",
                "file_parent": "root",
                "file_md5": "d41d8cd98f00b204e9800998ecf8427e",
                "can_delete": True,
                "create_time": "2023-12-01T10:00:00",
                "update_time": "2023-12-01T10:00:00"
            }
        }


class CreateFolderRequest(BaseModel):
    """创建文件夹请求模型"""
    file_name: str = Field(..., description="文件夹名称", min_length=1, max_length=100)
    parent_id: str = Field("root", description="父目录ID，默认为root")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_name": "新建文件夹",
                "parent_id": "root"
            }
        }


class DeleteResult(BaseModel):
    """删除操作结果模型"""
    success: bool = Field(..., description="删除是否成功")
    message: str = Field(..., description="操作结果消息")
    deleted_count: Optional[int] = Field(None, description="删除的文件数量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "文件删除成功",
                "deleted_count": 1
            }
        }


class FileListResponse(BaseResponse):
    """文件列表响应模型"""
    data: List[FileResponse] = Field(..., description="文件列表")


class FileUploadResponse(BaseResponse):
    """文件上传响应模型"""
    data: FileResponse = Field(..., description="上传的文件信息")


class DeleteResponse(BaseResponse):
    """删除操作响应模型"""
    data: DeleteResult = Field(..., description="删除操作结果")


# ===================
# 系统信息模型
# ===================

class SystemInfo(BaseModel):
    """系统信息模型"""
    message: str = Field(..., description="系统名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="运行状态")
    docs: str = Field(..., description="API文档地址")
    redoc: str = Field(..., description="ReDoc文档地址")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "广诚CAD内容识别服务",
                "version": "1.0.0",
                "status": "running",
                "docs": "/docs",
                "redoc": "/redoc"
            }
        }


class HealthCheck(BaseModel):
    """健康检查模型"""
    status: str = Field(..., description="健康状态")
    timestamp: str = Field(..., description="检查时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2023-12-01T10:00:00Z"
            }
        } 