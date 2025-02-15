#queue_manager
from dataclasses import dataclass
from queue import Queue
from typing import Optional, TypeVar, Generic, Any
import threading
import time
import uuid
from datetime import datetime

T = TypeVar('T')

@dataclass
class QueueItem(Generic[T]):
    """Represents an item in the verification queue with metadata"""
    id: str
    data: T
    timestamp: float
    status: str = 'pending'
    result: Optional[dict[str, Any]] = None

class VerificationQueues:
    """Contains queues for email verification process"""
    def __init__(self) -> None:
        self.email_queue: Queue[QueueItem[str]] = Queue()
        self.result_queue: Queue[QueueItem[str]] = Queue()
        self.active_verifications: dict[str, QueueItem[str]] = {}
        self._lock: threading.Lock = threading.Lock()

    def add_verification(self, email: str) -> QueueItem[str]:
        """Adds a new verification request to the queue"""
        verification_id = str(uuid.uuid4())
        item = QueueItem[str](
            id=verification_id,
            data=email,
            timestamp=time.time()
        )
        with self._lock:
            self.active_verifications[verification_id] = item
            self.email_queue.put(item)
        return item

    def update_verification(self, verification_id: str, result: dict[str, Any]) -> Optional[QueueItem[str]]:
        """Updates the verification result and status"""
        with self._lock:
            if verification_id in self.active_verifications:
                item = self.active_verifications[verification_id]
                item.status = 'completed'
                item.result = result
                self.result_queue.put(item)
                return item
        return None

    def get_verification_status(self, verification_id: str) -> Optional[QueueItem[str]]:
        """Retrieves the current status of a verification"""
        with self._lock:
            return self.active_verifications.get(verification_id)

    def cleanup_old_verifications(self, max_age: int = 3600) -> None:
        """Removes verifications older than max_age seconds"""
        current_time = time.time()
        with self._lock:
            expired = [
                vid for vid, item in self.active_verifications.items()
                if current_time - item.timestamp > max_age
            ]
            for vid in expired:
                del self.active_verifications[vid]

class QueueManager:
    """Singleton manager for all verification queues"""
    _instance: Optional['QueueManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.queues: dict[str, VerificationQueues] = {}
        self._cleanup_thread: threading.Thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()

    def __new__(cls) -> 'QueueManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(QueueManager, cls).__new__(cls)
                    cls._instance.__init__()
        return cls._instance

    def create_queues_for_service(self, service_name: str) -> VerificationQueues:
        """Creates or returns existing queues for a service"""
        with self._lock:
            if service_name not in self.queues:
                self.queues[service_name] = VerificationQueues()
            return self.queues[service_name]

    def get_queues(self, service_name: str) -> Optional[VerificationQueues]:
        """Retrieves queues for a specific service"""
        return self.queues.get(service_name)

    def _cleanup_loop(self) -> None:
        """Periodically cleans up old verifications"""
        while True:
            try:
                for queues in self.queues.values():
                    queues.cleanup_old_verifications()
                time.sleep(300)
            except Exception as e:
                print(f"Error in cleanup loop: {e}")

def create_response(
    success: bool, 
    data: Optional[dict[str, Any]] = None, 
    error: Optional[str] = None, 
    status_code: int = 200
) -> tuple[dict[str, Any], int]:
    """Creates a standardized response format"""
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
        
    return response, status_code