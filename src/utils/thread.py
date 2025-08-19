import os
from contextlib import contextmanager
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed

@contextmanager
def xthread(worker_num:int=6) -> ThreadPoolExecutor:
    """上下文管理器用于自动获取 ThreadPoolExecutor, 避免错误"""
    worker_num=max(os.cpu_count()*2,worker_num)
    pool = ThreadPoolExecutor(max_workers=worker_num)
    try:
        yield pool
    except:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    finally:
        pool.shutdown()