from database.models.sys_file_model import SysFileModel, FileType
from database.utils import generate_file_id
from database.session import with_session
from conf.config import FILE_SYSTEM_ROOT_PATH
from pathlib import Path
import hashlib
import os
from fastapi import UploadFile
from typing import Optional

# 获取文件的子文件列表
@with_session
def get_file_children_list(session, file_id: str):
    files = session.query(SysFileModel).filter(SysFileModel.file_parent == file_id).all()
    # 将SQLAlchemy模型对象转换为字典格式
    result = []
    for file in files:
        file_dict = {
            'file_id': file.file_id,
            'file_name': file.file_name,
            'file_type': file.file_type.value if file.file_type else None,
            'file_size': file.file_size,
            'file_suffix': file.file_suffix,
            'file_parent': file.file_parent,
            'file_md5': file.file_md5,
            'can_delete': file.can_delete,
            'create_time': file.create_time.isoformat() if file.create_time else None,
            'update_time': file.update_time.isoformat() if file.update_time else None
        }
        result.append(file_dict)
    return result

# 根据文件ID，获取文件信息
@with_session
def get_file_by_id(session, file_id: str):
    file = session.query(SysFileModel).filter_by(file_id=file_id).first()
    if file:
        return {
            'file_id': file.file_id,
            'file_name': file.file_name,
            'file_type': file.file_type.value if file.file_type else None,
            'file_size': file.file_size,
            'file_suffix': file.file_suffix,
            'file_parent': file.file_parent,
            'file_md5': file.file_md5,
            'can_delete': file.can_delete,
            'create_time': file.create_time.isoformat() if file.create_time else None,
            'update_time': file.update_time.isoformat() if file.update_time else None
        }
    return None

# 创建文件夹
@with_session
def create_folder(session, file_name: str, parent_id: str):
    # 构建文件夹的完整路径
    folder_path = _build_folder_path(session, file_name, parent_id)
    
    # 在本地文件系统中创建目录
    try:
        os.makedirs(folder_path, exist_ok=True)
    except Exception as e:
        return {"success": False, "message": f"创建本地目录失败: {str(e)}"}
    
    folder = SysFileModel(
        file_id=generate_file_id(),
        file_name=file_name,
        file_type=FileType.DIRECTORY,
        file_suffix='',
        file_parent=parent_id,
        file_size=0
    )
    session.add(folder)
    session.commit()
    
    # 返回字典格式
    return {
        'file_id': folder.file_id,
        'file_name': folder.file_name,
        'file_type': folder.file_type.value if folder.file_type else None,
        'file_size': folder.file_size,
        'file_suffix': folder.file_suffix,
        'file_parent': folder.file_parent,
        'file_md5': folder.file_md5,
        'create_time': folder.create_time.isoformat() if folder.create_time else None,
        'update_time': folder.update_time.isoformat() if folder.update_time else None
    }

def _build_folder_path(session, file_name: str, parent_id: str) -> str:
    """构建文件夹的完整路径"""
    if parent_id == "root":
        # 如果是根目录，直接在文件系统根路径下创建
        return os.path.join(FILE_SYSTEM_ROOT_PATH, file_name)
    else:
        # 获取父目录信息
        parent_folder = session.query(SysFileModel).filter_by(file_id=parent_id).first()
        if not parent_folder:
            raise ValueError(f"父目录不存在: {parent_id}")
        
        # 递归构建父目录路径
        parent_path = _build_folder_path(session, parent_folder.file_name, parent_folder.file_parent)
        return os.path.join(parent_path, file_name)

# 上传文件到指定目录
@with_session
def upload_file_to_directory(session, uploaded_file: UploadFile, parent_id: str):
    content = uploaded_file.file.read()
    file_md5 = hashlib.md5(content).hexdigest()
    suffix = Path(uploaded_file.filename).suffix.lstrip('.')
    file_id = generate_file_id()

    # 构建文件的完整保存路径
    save_path = _build_file_save_path(session, uploaded_file.filename, parent_id)
    
    # 确保父目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 保存文件到本地文件系统
    try:
        with open(save_path, 'wb') as f:
            f.write(content)
    except Exception as e:
        return {"success": False, "message": f"保存文件失败: {str(e)}"}

    file = SysFileModel(
        file_id=file_id,
        file_name=uploaded_file.filename,
        file_type=FileType.FILE,
        file_suffix=suffix,
        file_parent=parent_id,
        file_size=len(content),
        file_md5=file_md5
    )
    session.add(file)
    session.commit()

    # 返回字典格式
    return {
        'file_id': file.file_id,
        'file_name': file.file_name,
        'file_type': file.file_type.value if file.file_type else None,
        'file_size': file.file_size,
        'file_suffix': file.file_suffix,
        'file_parent': file.file_parent,
        'file_md5': file.file_md5,
        'create_time': file.create_time.isoformat() if file.create_time else None,
        'update_time': file.update_time.isoformat() if file.update_time else None
    }

def _build_file_save_path(session, filename: str, parent_id: str) -> str:
    """构建文件的完整保存路径"""
    if parent_id == "root":
        # 如果是根目录，直接在文件系统根路径下保存
        return os.path.join(FILE_SYSTEM_ROOT_PATH, filename)
    else:
        # 获取父目录信息
        parent_folder = session.query(SysFileModel).filter_by(file_id=parent_id).first()
        if not parent_folder:
            raise ValueError(f"父目录不存在: {parent_id}")
        
        # 递归构建父目录路径
        parent_path = _build_folder_path(session, parent_folder.file_name, parent_folder.file_parent)
        return os.path.join(parent_path, filename)

def _build_file_path_for_deletion(session, file: SysFileModel) -> str:
    """构建文件删除时的完整路径"""
    if file.file_parent == "root":
        # 如果是根目录下的文件
        return os.path.join(FILE_SYSTEM_ROOT_PATH, file.file_name)
    else:
        # 获取父目录信息
        parent_folder = session.query(SysFileModel).filter_by(file_id=file.file_parent).first()
        if not parent_folder:
            raise ValueError(f"父目录不存在: {file.file_parent}")
        
        # 递归构建父目录路径
        parent_path = _build_folder_path(session, parent_folder.file_name, parent_folder.file_parent)
        return os.path.join(parent_path, file.file_name)


# 递归删除文件或文件夹
@with_session
def delete_file_recursive(session, file_id: str):
    """
    递归删除文件或文件夹
    如果是文件夹，会递归删除其所有子文件和子文件夹
    如果是文件，会删除文件记录和物理文件
    """
    file = session.query(SysFileModel).filter_by(file_id=file_id).first()
    if not file:
        return {"success": False, "message": "文件不存在"}
    
    deleted_files = []
    
    try:
        if file.file_type == FileType.DIRECTORY:
            # 如果是文件夹，先递归删除所有子文件和子文件夹
            deleted_files.extend(_delete_folder_recursive(session, file_id))
        else:
            # 如果是文件，删除物理文件
            if file.file_name:
                # 构建文件的完整路径
                file_path = _build_file_path_for_deletion(session, file)
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    deleted_files.append(str(file_path))
        
        # 删除数据库记录
        session.delete(file)
        session.commit()
        
        return {
            "success": True, 
            "message": "删除成功",
            "deleted_file": {
                'file_id': file.file_id,
                'file_name': file.file_name,
                'file_type': file.file_type.value if file.file_type else None,
                'file_size': file.file_size,
                'file_suffix': file.file_suffix,
                'file_parent': file.file_parent,
                'file_md5': file.file_md5,
                'create_time': file.create_time.isoformat() if file.create_time else None,
                'update_time': file.update_time.isoformat() if file.update_time else None
            },
            "deleted_physical_files": deleted_files
        }
        
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"删除失败: {str(e)}"}


def _delete_folder_recursive(session, folder_id: str):
    """
    递归删除文件夹的内部函数
    返回被删除的物理文件路径列表
    """
    deleted_files = []
    
    # 获取文件夹下的所有子文件和子文件夹
    children = session.query(SysFileModel).filter(SysFileModel.file_parent == folder_id).all()
    
    for child in children:
        if child.file_type == FileType.DIRECTORY:
            # 递归删除子文件夹
            deleted_files.extend(_delete_folder_recursive(session, child.file_id))
        else:
            # 删除物理文件
            if child.file_name:
                # 构建文件的完整路径
                file_path = _build_file_path_for_deletion(session, child)
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    deleted_files.append(str(file_path))
        
        # 删除数据库记录
        session.delete(child)
    
    return deleted_files

@with_session
def get_file_info(session, file_id: str)->Optional[SysFileModel]:
    file = session.query(SysFileModel).filter_by(file_id=file_id).first()
    if file:
        # 在会话关闭前获取所有需要的属性，避免延迟加载问题
        _ = file.file_id
        _ = file.file_name
        _ = file.file_type
        _ = file.file_size
        _ = file.file_suffix
        _ = file.file_parent
        _ = file.file_md5
        _ = file.create_time
        _ = file.update_time
        # 从会话中分离对象，使其可以独立使用
        session.expunge(file)
        return file
    return None

@with_session
def update_file_name(session, file_id: str, file_name: str):
    """
    更新文件名称
    同时更新物理文件名和数据库记录
    """
    # 验证文件是否存在
    file = session.query(SysFileModel).filter_by(file_id=file_id).first()
    if not file:
        return {"success": False, "message": "文件不存在"}
    
    # 验证新文件名是否为空
    if not file_name or file_name.strip() == "":
        return {"success": False, "message": "文件名不能为空"}
    
    # 验证新文件名长度
    if len(file_name) > 255:
        return {"success": False, "message": "文件名长度不能超过255个字符"}
    
    # 检查同级目录下是否已存在同名文件
    existing_file = session.query(SysFileModel).filter(
        SysFileModel.file_parent == file.file_parent,
        SysFileModel.file_name == file_name,
        SysFileModel.file_id != file_id
    ).first()
    
    if existing_file:
        return {"success": False, "message": "同级目录下已存在同名文件"}
    
    try:
        old_file_name = file.file_name
        old_file_path = None
        new_file_path = None
        
        # 如果是文件或目录，都需要重命名物理文件/文件夹
        if file.file_type in [FileType.FILE, FileType.DIRECTORY]:
            # 构建旧文件/文件夹路径
            if file.file_type == FileType.FILE:
                old_file_path = _build_file_path_for_deletion(session, file)
            else:  # FileType.DIRECTORY
                old_file_path = _build_folder_path(session, file.file_name, file.file_parent)
            
            # 构建新文件/文件夹路径
            if file.file_type == FileType.FILE and file.file_suffix:
                new_file_name = f"{file_name}.{file.file_suffix}"
            else:
                new_file_name = file_name
            
            # 构建新文件/文件夹路径
            parent_path = _build_folder_path(session, "", file.file_parent)
            new_file_path = os.path.join(parent_path, new_file_name)
            
            # 重命名物理文件/文件夹
            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
        
        # 更新数据库记录
        file.file_name = file_name
        # 如果是文件且有后缀，更新文件名（不包含后缀）
        if file.file_type == FileType.FILE and file.file_suffix:
            # 文件名不包含后缀
            pass
        else:
            # 如果是文件夹，文件名就是完整名称
            pass
        
        session.commit()
        
        return {
            "success": True,
            "message": "文件名更新成功",
            "data": {
                'file_id': file.file_id,
                'file_name': file.file_name,
                'file_type': file.file_type.value if file.file_type else None,
                'file_size': file.file_size,
                'file_suffix': file.file_suffix,
                'file_parent': file.file_parent,
                'file_md5': file.file_md5,
                'create_time': file.create_time.isoformat() if file.create_time else None,
                'update_time': file.update_time.isoformat() if file.update_time else None
            },
            "old_file_name": old_file_name,
            "new_file_name": file_name
        }
        
    except Exception as e:
        session.rollback()
        # 如果重命名物理文件失败，尝试恢复
        if old_file_path and new_file_path and os.path.exists(new_file_path):
            try:
                os.rename(new_file_path, old_file_path)
            except:
                pass
        return {"success": False, "message": f"更新文件名失败: {str(e)}"}

