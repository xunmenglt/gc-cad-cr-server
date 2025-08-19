# 导入数据相关操作
import os
import database.repository.task_repository as task_repo
import database.repository.sys_file_repository as file_repo
from database.models.task_model import TaskStatus, TaskModel
from database.models.sys_file_model import FileType
import multiprocessing
import signal
import queue
from typing import Callable,Dict,Any
from conf.config import FILE_SYSTEM_ROOT_PATH,FILE_SYSTEM_MAPPING_DIR,PROJECT_MAPPING
import time
import json
import logging
from extraction.identifier import CADContentIdentifier
from field_resgister import FIELDS_POOL
from server.task_exec.message import Message
import threading

# 配置日志
import os
from datetime import datetime

# 创建日志目录
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

# 配置日志格式
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# 配置文件处理器
log_file = os.path.join(log_dir, f"task_exec_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format, date_format))

# 配置控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format, date_format))

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 添加文件处理器
root_logger.addHandler(file_handler)

# 添加控制台处理器
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f"日志文件路径: {log_file}")


def realfile_name_in_mapping(file_name:str):
    for key,value in PROJECT_MAPPING.items():
        if file_name in value:
            return key
    return None


def _cad_identify_worker(task_id: str, queue: multiprocessing.Queue, params: Dict[str, Any]):
    """CAD识别任务的工作函数（独立于类）"""
    import traceback
    import sys
    
    logger.info(f"工作进程开始执行任务: {task_id}")
    logger.info(f"接收到的参数: {params}")
    
    start_time = time.time()
    project_dir = params.get("project_path")
    agent_model_name = params.get("agent_model_name")
    output_dir = params.get("output_dir")
    
    logger.info(f"工作目录: {project_dir}")
    logger.info(f"使用模型: {agent_model_name}")
    logger.info(f"输出目录: {output_dir}")
    
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"输出目录已创建/确认: {output_dir}")
    
    try:
        logger.info(f"开始执行CAD识别任务...")
        # 发送开始执行消息
        queue.put(Message(task_id=task_id, type="START", data=params).to_dict())
        logger.info(f"已发送开始消息到主进程")
        
        
        # TODO: 实际的CAD识别逻辑
        identifier = CADContentIdentifier(
            project_dir=project_dir,
            output_dir=output_dir,
            agent_model_name=agent_model_name,
        )
        result = identifier.extract_filds(FIELDS_POOL,queue=queue,task_id=task_id,output_dir=output_dir)
        
        # 模拟任务执行
        # logger.info(f"开始模拟任务执行（100步）...")
        # for i in range(100):
        #     time.sleep(1)
        #     progress = i + 1
        #     logger.info(f"进度: {progress}/100 ({progress}%)")
        #     queue.put(Message(task_id=task_id, type="PROGRESS", data={"progress": progress}).to_dict())

        # 发送结束执行消息
        logger.info(f"任务执行完成！")
        queue.put(Message(task_id=task_id, type="FINISH", data=result).to_dict())
        logger.info(f"已发送完成消息到主进程")
        # 结果本地存储一份
        output_path = os.path.join(output_dir, f"{result['project_name']}.json")
        # 判断一下文件是否存在
        if not os.path.exists(output_path):
            logger.error(f"结果文件不存在: {output_path}")
            # 本地存储一下，防止下次任务执行的时候重复执行
            try:
                with open(output_path, 'w', encoding="utf-8") as fp:
                    json.dump(result, fp, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"结果文件保存失败: {e}")
        else:
            logger.info(f"结果文件已存在: {output_path}")
        logger.info(f"结果已保存至: {output_path}")
        
    except Exception as e:
        # 获取完整的错误信息和堆栈跟踪
        error_info = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "sys_info": {
                "python_version": sys.version,
                "platform": sys.platform
            }
        }
        
        logger.error(f"任务执行出错: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"完整堆栈跟踪:\n{traceback.format_exc()}")
        
        # 发送失败消息，包含详细的错误信息
        queue.put(Message(task_id=task_id, type="FAIL", data=error_info).to_dict())
        logger.info(f"已发送失败消息到主进程")
        
        # 确保错误信息被记录到日志文件
        logger.error(f"任务 {task_id} 执行失败，详细错误信息已发送到主进程")


class CADIdentifyTask:
    def __init__(self, task_id: str, agent_model_name: str, output_dir: str, success_callback: Callable, fail_callback: Callable):
        self.task_id = task_id
        self.agent_model_name = agent_model_name
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.task = self._task_info()
        # 进程消息队列
        try:
            multiprocessing.set_start_method("spawn")
        except RuntimeError:
            # 如果已经设置过了，忽略错误
            pass
        self.manager = multiprocessing.Manager()
        # 进程消息队列，用于接收消息
        self.queue = self.manager.Queue()
        # 启动的任务进程
        self.process = None
        # 成功回调
        self.success_callback = success_callback
        # 失败回调
        self.fail_callback = fail_callback
        self.watch_thread = None
        self._stop_event = threading.Event()  # 停止标志
        
    def _task_info(self) -> TaskModel:
        task = task_repo.get_task_info(self.task_id)
        if not task:
            raise ValueError(f"任务不存在: {self.task_id}")
        # 确保在返回前访问所有需要的属性，避免延迟加载问题
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
        return task
    
    def can_run(self):
        if self.task.task_status == TaskStatus.PENDING:
            return True
        return False
    
    def start(self):
        # 判断当前任务是否可以运行
        if not self.can_run():
            raise ValueError(f"任务不能运行: {self.task_id}")
        # 验证任务参数
        self._validate_params(self.task.task_params)
        # 有了项目参数之后，可以获取项目信息
        project_path = self._get_project_path(self.task.task_params.get("project_id"))
        task_params = {
            "project_path": project_path,
            "task_id": self.task_id,
            "agent_model_name": self.agent_model_name,
            "output_dir": self.output_dir
        }
        
        logger.info(f"启动任务进程: {self.task_id}")
        logger.info(f"项目路径: {project_path}")
        logger.info(f"模型名称: {self.agent_model_name}")
        logger.info(f"输出目录: {self.output_dir}")
        logger.info(f"任务参数: {task_params}")
        
        # 注册任务
        self.process = multiprocessing.Process(
            target=_cad_identify_worker,
            name=f"cad_identify_{self.task_id}",
            args=(self.task_id,self.queue, task_params)
        )
        self.process.start()
        
        logger.info(f"任务进程已启动，PID: {self.process.pid}")
        
    def _validate_params(self, params: Dict[str, Any]):
        if not params.get("project_id"):
            raise ValueError("项目参数不能为空")
        
    def _get_project_path(self, project: str):
        file_info = file_repo.get_file_info(project)
        if not file_info:
            raise ValueError(f"项目不存在: {project}")
        if file_info.file_type != FileType.DIRECTORY:
            raise ValueError(f"项目不是文件夹: {project}")
        # 判断项目是否在映射目录中
        realfile_name=realfile_name_in_mapping(file_info.file_name)
        if realfile_name:
            project_path = os.path.join(FILE_SYSTEM_MAPPING_DIR, realfile_name)
        else:
            project_path = os.path.join(FILE_SYSTEM_ROOT_PATH, file_info.file_name)
        if not os.path.exists(project_path):
            logger.error(f"项目不存在: {project_path}")
            raise ValueError(f"项目不存在: {project}")
        return project_path

    def stop(self):
        """停止任务进程"""
        try:
            # 更新任务状态
            task_repo.update_task_status(self.task_id, TaskStatus.FAILED)
            
            if self.process and self.process.is_alive():
                # 1. 首先尝试优雅终止
                self.process.terminate()
                
                # 2. 等待进程结束，设置超时
                self.process.join(timeout=5)  # 等待5秒
                
                # 3. 如果进程仍然存活，强制终止
                if self.process.is_alive():
                    logger.warning(f"进程 {self.process.pid} 未响应 SIGTERM，强制终止")
                    self.process.kill()  # 发送 SIGKILL
                    self.process.join(timeout=2)  # 再等待2秒
            
            # 4. 清理资源
            if hasattr(self, 'queue') and self.queue:
                # Manager().Queue() 返回的是代理对象，没有 close() 方法
                # 只需要设置为 None 即可
                self.queue = None
                
            if hasattr(self, 'manager') and self.manager:
                # 关闭 manager
                self.manager.shutdown()
                self.manager = None
                
            if hasattr(self, 'watch_thread') and self.watch_thread:
                self.watch_thread.join(timeout=1)
                self._stop_event.set()
                
            self.process = None
            
        except Exception as e:
            logger.error(f"停止任务时发生错误: {e}")
            # 确保进程被终止
            if self.process and self.process.is_alive():
                try:
                    self.process.kill()
                except:
                    pass
        
    def _handle_start(self, data: Dict[str, Any]):
        """处理开始消息"""
        logger.info(f"收到开始消息: {data}")
        task_repo.update_task_status(self.task_id, TaskStatus.RUNNING)
        logger.info(f"任务状态已更新为运行中")
    
    def _handle_progress(self, progress: int):
        """处理进度消息"""
        logger.info(f"收到进度消息: {progress}%")
        task_repo.update_task_status(self.task_id, TaskStatus.RUNNING)
        task_repo.update_task_progress(self.task_id, progress)
        logger.info(f"任务进度已更新: {progress}%")
    
    def _handle_finish(self, data: Any):
        """处理完成消息"""
        logger.info(f"收到完成消息: {data}")
        task_repo.update_task_status(self.task_id, TaskStatus.COMPLETED)
        logger.info(f"任务状态已更新为已完成")
        # TODO 保存结果
        task_repo.update_task_result(self.task_id, data)
        self.success_callback(self.task)
        logger.info(f"任务成功完成！")
    
    def _handle_fail(self, data: Any):
        """处理失败消息"""
        logger.info(f"收到失败消息: {data}")
        task_repo.update_task_status(self.task_id, TaskStatus.FAILED)
        logger.info(f"任务状态已更新为失败")
        self.fail_callback(self.task)
        if isinstance(data,dict):
            task_repo.update_task_result(self.task_id, data)
        logger.error(f"任务执行失败: {data}")

    def _handle_message(self, message: Message):
        """统一的消息处理入口"""
        if message.type == "START":
            self._handle_start(message.data)
        elif message.type == "PROGRESS":
            self._handle_progress(message.data.get("progress"))
        elif message.type == "FINISH":
            self._handle_finish(message.data)
        elif message.type == "FAIL":
            self._handle_fail(message.data)
        
    def _watch_message(self):
        """监听消息队列的线程"""
        logger.info(f"开始监听任务消息队列...")
        while not self._stop_event.is_set():
            try:
                message = self.queue.get(timeout=1)  # 添加超时避免无限等待
                logger.info(f"收到消息: {message}")
                self._handle_message(Message.from_dict(message))
            except queue.Empty:
                # 队列为空，这是正常的超时情况，不需要记录
                continue
            except Exception as e:
                # 其他异常，记录详细信息
                logger.warning(f"消息处理异常: {e}")
                logger.warning(f"异常类型: {type(e).__name__}")
                logger.warning(f"异常详情: {str(e)}")
                # 如果是消息反序列化问题，记录消息内容
                if "from_dict" in str(e) or "Message" in str(e):
                    logger.warning(f"消息反序列化失败，消息内容: {message if 'message' in locals() else '未知'}")
                continue
        logger.info(f"消息监听线程已停止")
       
    def run(self):
        """启动任务"""
        self.start()
        self._stop_event.clear()
        self.watch_thread = threading.Thread(target=self._watch_message, daemon=True)
        self.watch_thread.start()
        # 不阻塞
        return True