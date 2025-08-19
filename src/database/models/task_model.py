import enum
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey, UniqueConstraint 
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from sqlalchemy.sql import func


from database.base import Base
from database.utils import generate_task_id

class TaskStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


class TaskModel(Base):
    """
    任务表模型，对应 task 表
    """

    __tablename__ = 'task'
    __table_args__ = (
        UniqueConstraint('task_name', name='uniq_task_name'),
    )

    task_id = Column(String(64), primary_key=True, default=generate_task_id, comment='任务ID')
    task_name = Column(String(255), comment='任务名称')
    task_description = Column(String(255), comment='任务描述')
    task_params = Column(JSON, comment='任务参数')
    task_level = Column(Integer, default=0, comment='任务级别，约高越重要')
    task_status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, comment='任务状态')
    task_progress = Column(Integer, default=0, comment='任务进度')
    task_result = Column(JSON, comment='任务结果')
    task_create_time = Column(DateTime, default=func.now(), comment='任务创建时间')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    create_time = Column(DateTime, default=func.now(), comment='创建时间')
    
    def __repr__(self):
        return (
            f"<TaskModel(task_id='{self.task_id}', task_name='{self.task_name}', task_status='{self.task_status}', "
            f"task_progress='{self.task_progress}', create_time='{self.create_time}')>"
        )