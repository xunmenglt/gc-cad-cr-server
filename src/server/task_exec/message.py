from dataclasses import dataclass
from typing import Any,Literal,Dict,Optional





@dataclass
class Message:
    task_id: str
    type: Literal['FAIL', 'FINISH', 'PROGRESS', 'START']
    data: Any
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'type': self.type,
            'data': self.data
        }
    
    @classmethod
    def from_dict(cls,data:Dict[str,Any]):
        return cls(task_id=data.get("task_id"),
                   type=data.get("type"),
                   data=data.get("data"))
    
    