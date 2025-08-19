import os
import sys
import json
from fastapi import UploadFile
from database.utils import generate_file_id
from database.repository import sys_file_repository as repo
from io import BytesIO
sys.path.append(os.getcwd())

def recursive_dir_and_file_2db(current_dir_childrn,parentId,current_dir):
    # 获取当前dir下的一级目录和文件
    files=os.listdir(current_dir)
    print(files)
    for file in files:
        file_path=os.path.join(current_dir,file)
        if os.path.isdir(file_path):
            item={
                "file_id":generate_file_id(),
                "file_name":os.path.basename(file_path),
                "file_path":file_path,
                "parent_id":parentId,
                "file_type":"directory",
                "children":[]
            }
            recursive_dir_and_file_2db(item['children'],item['file_id'],file_path)
        else:
            item={
                "file_id":generate_file_id(),
                "file_name":os.path.basename(file_path),
                "file_path":file_path,
                "parent_id":parentId,
                "file_type":"file",
                "children":[]
            }
        current_dir_childrn.append(item)  
    
def save_files(files,current_parent_id):
    for file in files:
        file_type=file['file_type']
        if file_type=='directory':
            rs=repo.create_folder(file['file_name'],current_parent_id)
            file['file_id']=rs['file_id']
            save_files(file['children'],file['file_id'])
        else:
            file_path=file['file_path']
            with open(file_path, "rb") as f:
                file_content = f.read()
            upload_file = UploadFile(
                filename=file['file_name'],
                file=BytesIO(file_content)
            )
            repo.upload_file_to_directory(upload_file,current_parent_id)
            upload_file.file.close() 

if __name__ == "__main__":
    # 测试存储
    dir_path=os.path.join(os.getcwd(),"data/tmp/gc/真实的5个项目")
    dir_map={
            "file_id":"root",
            "file_name":"root",
            "file_type":"directory",
            "parent_id":"root",
            "file_path":dir_path,
            "children":[]
        }
    current_dir_childrn=dir_map['children']
    recursive_dir_and_file_2db(current_dir_childrn,dir_map['file_id'],dir_path)
    print(dir_map)
    print(json.dumps(dir_map,indent=4,ensure_ascii=False))
    
    # 存储数据
    files=dir_map['children']
    save_files(files,dir_map['file_id'])
    