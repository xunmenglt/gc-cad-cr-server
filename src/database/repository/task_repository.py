from database.models.task_model import TaskModel, TaskStatus
from database.session import with_session
from typing import List, Dict, Any, Optional

# 获取任务列表
@with_session
def get_task_list(session) -> List[Dict[str, Any]]:
    """获取所有任务列表"""
    tasks = session.query(TaskModel).order_by(TaskModel.create_time.desc()).all()
    result = []
    for task in tasks:
        task_dict = {
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_description': task.task_description,
            'task_params': task.task_params,
            'task_level': task.task_level,
            'task_status': task.task_status.value if task.task_status else None,
            'task_progress': task.task_progress,
            'task_result': task.task_result,
            'create_time': task.create_time.isoformat() if task.create_time else None,
            'update_time': task.update_time.isoformat() if task.update_time else None
        }
        result.append(task_dict)
    return result

# 根据任务ID获取任务详情
@with_session
def get_task_by_id(session, task_id: str) -> Optional[Dict[str, Any]]:
    """根据任务ID获取任务详情"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if task:
        return {
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_description': task.task_description,
            'task_params': task.task_params,
            'task_level': task.task_level,
            'task_status': task.task_status.value if task.task_status else None,
            'task_progress': task.task_progress,
            'task_result': task.task_result,
            'create_time': task.create_time.isoformat() if task.create_time else None,
            'update_time': task.update_time.isoformat() if task.update_time else None
        }
    return None

@with_session
def get_task_info(session, task_id: str) -> Optional[TaskModel]:
    """根据任务ID获取任务详情"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if task:
        # 在会话关闭前获取所有需要的属性，避免延迟加载问题
        _ = task.task_id
        _ = task.task_name
        _ = task.task_description
        _ = task.task_params
        _ = task.task_level
        _ = task.task_status
        _ = task.task_progress
        _ = task.task_result
        _ = task.create_time
        _ = task.update_time
        # 从会话中分离对象，使其可以独立使用
        session.expunge(task)
        return task
    return None

# 创建任务
@with_session
def create_task(session, task_name: str, task_description: str, task_params: Dict[str, Any], task_level: int = 0) -> Dict[str, Any]:
    """创建新任务"""
    task = TaskModel(
        task_name=task_name,
        task_description=task_description,
        task_params=task_params,
        task_level=task_level,
        task_status=TaskStatus.PENDING,
        task_progress=0
    )
    session.add(task)
    session.commit()
    
    return {
        'task_id': task.task_id,
        'task_name': task.task_name,
        'task_description': task.task_description,
        'task_params': task.task_params,
        'task_level': task.task_level,
        'task_status': task.task_status.value if task.task_status else None,
        'task_progress': task.task_progress,
        'task_result': task.task_result,
        'create_time': task.create_time.isoformat() if task.create_time else None,
        'update_time': task.update_time.isoformat() if task.update_time else None
    }


# 停止任务
@with_session
def stop_task(session, task_id: str) -> Dict[str, Any]:
    """停止任务"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return {"success": False, "message": "任务不存在"}
    
    # 只能停止正在运行的任务
    if task.task_status != TaskStatus.RUNNING:
        return {"success": False, "message": "只能停止正在运行的任务"}
    
    task.task_status = TaskStatus.FAILED
    task.task_progress = 0
    
    session.commit()
    
    return {
        "success": True,
        "message": "任务已停止",
        "task": {
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_description': task.task_description,
            'task_params': task.task_params,
            'task_level': task.task_level,
            'task_status': task.task_status.value if task.task_status else None,
            'task_progress': task.task_progress,
            'task_result': task.task_result,
            'create_time': task.create_time.isoformat() if task.create_time else None,
            'update_time': task.update_time.isoformat() if task.update_time else None
        }
    }


# 启动任务
@with_session
def startup_task(session, task_id: str) -> bool:
    """启动任务"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return False
    
    task.task_status = TaskStatus.RUNNING
    session.commit()
    return True

# 更新任务进度
@with_session
def update_task_progress(session, task_id: str, progress: int) -> bool:
    """更新任务进度"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return False
    task.task_progress = progress
    session.commit()
    return True



# 删除任务
@with_session
def delete_task(session, task_id: str) -> Dict[str, Any]:
    """删除任务"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return {"success": False, "message": "任务不存在"}
    
    # 只能删除已完成或失败的任务
    if task.task_status in [TaskStatus.RUNNING]:
        return {"success": False, "message": "不能删除正在运行的任务，请先停止任务"}
    
    session.delete(task)
    session.commit()
    
    return {
        "success": True,
        "message": "任务删除成功",
        "deleted_task": {
            'task_id': task.task_id,
            'task_name': task.task_name,
            'task_description': task.task_description,
            'task_params': task.task_params,
            'task_level': task.task_level,
            'task_status': task.task_status.value if task.task_status else None,
            'task_progress': task.task_progress,
            'task_result': task.task_result,
            'create_time': task.create_time.isoformat() if task.create_time else None,
            'update_time': task.update_time.isoformat() if task.update_time else None
        }
    } 
    
    
# 更新任务状态
@with_session
def update_task_status(session, task_id: str, status: TaskStatus) -> bool:
    """更新任务状态"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return False
    task.task_status = status
    session.commit()
    return True


@with_session
def update_task_result(session, task_id: str, result: Dict[str, Any]) -> bool:
    """更新任务结果"""
    task = session.query(TaskModel).filter_by(task_id=task_id).first()
    if not task:
        return False
    task.task_result = result
    session.commit()
    return True