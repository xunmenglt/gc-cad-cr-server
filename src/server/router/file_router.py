"""
文件管理路由模块
提供文件和文件夹的上传、创建、删除、查看等功能
"""
import os
import sys
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Query, Path
from database.repository import sys_file_repository as repo
from .response import BaseResponse, ListResponse
from typing import List, Optional
from pydantic import BaseModel, Field

# 文件响应模型
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
                "file_type": "dwg",
                "file_size": 1024000,
                "file_suffix": "dwg",
                "file_parent": "root",
                "file_md5": "d41d8cd98f00b204e9800998ecf8427e",
                "can_delete": True,
                "create_time": "2023-12-01T10:00:00",
                "update_time": "2023-12-01T10:00:00"
            }
        }


# 文件列表响应模型
class FileListResponse(BaseResponse):
    """文件列表响应模型"""
    data: List[FileResponse] = Field(..., description="文件列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
                "data": [
                    {
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
                    },
                    {
                        "file_id": "folder_20231201_001",
                        "file_name": "CAD图纸",
                        "file_type": "D",
                        "file_size": 0,
                        "file_suffix": "",
                        "file_parent": "root",
                        "file_md5": None,
                        "can_delete": False,
                        "create_time": "2023-12-01T09:00:00",
                        "update_time": "2023-12-01T09:00:00"
                    }
                ]
            }
        }


# 创建文件夹请求模型
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


# 更新文件名请求模型
class UpdateFileNameRequest(BaseModel):
    """更新文件名请求模型"""
    file_id: str = Field(..., description="文件ID", min_length=1)
    file_name: str = Field(..., description="新的文件名称", min_length=1, max_length=255)
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file_20231201_001",
                "file_name": "新文件名"
            }
        }


# 文件上传响应模型
class FileUploadResponse(BaseResponse):
    """文件上传响应模型"""
    data: FileResponse = Field(..., description="上传的文件信息")


# 删除操作响应模型
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


# 删除操作响应模型
class DeleteResponse(BaseResponse):
    """删除操作响应模型"""
    data: DeleteResult = Field(..., description="删除操作结果")


router = APIRouter()


@router.get(
    "/", 
    response_model=FileListResponse,
    summary="获取文件列表",
    description="获取指定目录下的所有文件和文件夹列表",
    tags=["文件管理"]
)
def list_files(parent_id: str = Query("root", description="父目录ID，默认为root")):
    """获取文件列表"""
    try:
        files = repo.get_file_children_list(parent_id)
        return BaseResponse(data=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.post(
    "/create-folder", 
    response_model=BaseResponse,
    summary="创建文件夹",
    description="在指定目录下创建新的文件夹",
    tags=["文件管理"]
)
def create_folder(
    file_name: str = Form(..., description="文件夹名称"), 
    parent_id: str = Form("root", description="父目录ID，默认为root")
):
    """创建文件夹"""
    try:
        folder = repo.create_folder(file_name=file_name, parent_id=parent_id)
        if isinstance(folder, dict) and not folder.get("success", True):
            raise HTTPException(status_code=400, detail=folder.get("message", "创建文件夹失败"))
        return BaseResponse(data=folder)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文件夹时发生错误: {str(e)}")


@router.post(
    "/upload", 
    response_model=FileUploadResponse,
    summary="上传文件",
    description="上传文件到指定目录",
    tags=["文件管理"]
)
def upload_file(
    parent_id: str = Form(..., description="上传到的目录ID"), 
    uploaded_file: UploadFile = File(..., description="要上传的文件")
):
    """上传文件"""
    try:
        # 验证文件
        if uploaded_file.size == 0:
            raise HTTPException(status_code=400, detail="文件为空")
        
        file = repo.upload_file_to_directory(uploaded_file=uploaded_file, parent_id=parent_id)
        if isinstance(file, dict) and not file.get("success", True):
            raise HTTPException(status_code=400, detail=file.get("message", "上传文件失败"))
        return BaseResponse(data=file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传文件时发生错误: {str(e)}")


@router.delete(
    "/{file_id}", 
    response_model=DeleteResponse,
    summary="删除文件或文件夹",
    description="删除指定的文件或文件夹（递归删除）",
    tags=["文件管理"]
)
def delete_file(file_id: str = Path(..., description="要删除的文件或文件夹ID")):
    """删除文件或文件夹"""
    try:
        result = repo.delete_file_recursive(file_id)
        return BaseResponse(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件时发生错误: {str(e)}")
    
@router.post(
    "/update_file_name",
    response_model=BaseResponse,
    summary="更新文件名称",
    description="更新文件名称",
    tags=["文件管理"]
)
def update_file_name(request: UpdateFileNameRequest):
    """更新文件名称"""
    try:
        # 调用数据库仓库函数更新文件名
        result = repo.update_file_name(file_id=request.file_id, file_name=request.file_name)
        
        if isinstance(result, dict) and not result.get("success", True):
            raise HTTPException(status_code=400, detail=result.get("message", "更新文件名失败"))
        
        return BaseResponse(data=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新文件名时发生错误: {str(e)}")
    

    