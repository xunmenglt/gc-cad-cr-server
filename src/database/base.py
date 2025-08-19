import os
import json
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from conf.config import DB_ROOT_PATH


# 确保数据库文件所在目录存在
db_dir = os.path.dirname(DB_ROOT_PATH)
if not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_ROOT_PATH}"


engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def create_tables():
    Base.metadata.create_all(bind=engine)