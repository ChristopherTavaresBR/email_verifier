from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class BaseConfig:
    headless: bool
    total_emails: int
    total_steps: int
    
    @abstractmethod
    def get_verification_url(self) -> str:
        pass
