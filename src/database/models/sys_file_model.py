from sqlalchemy import (
    Column,
    Integer, 
    String, 
    BigInteger, 
    DateTime, 
    func,
    UniqueConstraint,
    Enum as SAEnum,
    Boolean
)
import enum
from database.base import Base




class FileType(enum.Enum):
    DIRECTORY = 'D'
    FILE = 'F'

class SysFileModel(Base):
    """
    系统文件表模型，对应 sys_file 表
    """
    __tablename__ = 'sys_file'
    __table_args__ = (
        UniqueConstraint('file_name', 'file_parent', name='uniq_name_in_folder'),
    )


    file_id = Column(String(64), primary_key=True, comment='文件ID')
    file_md5 = Column(String(64), comment='文件md5值')
    file_name = Column(String(255), comment='文件名称')
    file_size = Column(BigInteger, comment='文件大小')
    file_type = Column(SAEnum(FileType), comment='文件类型(D目录，F文件)')
    file_suffix = Column(String(16), comment='文件后缀')
    file_parent = Column(String(64), default='root', nullable=False, comment='父目录ID（默认 root 表示顶层）')
    can_delete = Column(Boolean, default=True, comment='是否可以删除')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (
            f"<SysFileModel(file_id='{self.file_id}', file_name='{self.file_name}', file_type='{self.file_type}', "
            f"file_size='{self.file_size}', create_time='{self.create_time}')>"
        )
