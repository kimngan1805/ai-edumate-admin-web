import os
import time
import threading
from pathlib import Path
from typing import Union

def auto_cleanup(file_path: Union[str, Path], timeout: int = 1800):
    """
    Schedule automatic cleanup of a file after timeout seconds
    """
    def cleanup_file():
        time.sleep(timeout)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_file, daemon=True)
    cleanup_thread.start()