'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-02 12:26:50
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-03 07:57:40
FilePath: /RAG_service/utils/request_backof.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import logging
import time
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(max_attempts = 3,base_delay = 1.0):
    """自定义重试装饰器，实现指数退避"""
    def decoration(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decoration

def timeout_handler(time_seconds = 30.0):
    """超时控制装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_signal_handler(signum, frame):
                raise TimeoutError(f"操作超时 ({time_seconds}秒)")
            
            # 设置超时信号
            old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(int(time_seconds))
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # 取消超时
                return result
            except TimeoutError:
                logger.error(f"操作超时: {time_seconds}秒")
                raise
            finally:
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator
