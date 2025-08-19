import uuid


def generate_file_id(prefix: str = "file_") -> str:
    """
    生成唯一的 file_id，格式为：<prefix><uuid>
    
    :param prefix: 可选前缀（如 "file_"）
    :return: 字符串形式的 file_id
    """
    return f"{prefix}{uuid.uuid4().hex}"

def generate_task_id(prefix: str = "task_") -> str:
    """
    生成唯一的 task_id，格式为：<prefix><uuid>
    """
    return f"{prefix}{uuid.uuid4().hex}"