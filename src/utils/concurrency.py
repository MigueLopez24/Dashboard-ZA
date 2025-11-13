import atexit
from concurrent.futures import ThreadPoolExecutor

_shared_executor = None

def get_shared_executor(max_workers: int = 20):
    
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = ThreadPoolExecutor(max_workers=max_workers)
        atexit.register(lambda: _shared_executor.shutdown(wait=True))
    return _shared_executor
