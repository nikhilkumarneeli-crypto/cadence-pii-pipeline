
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PIIFinding:
    entity_type: str
    text: str
    start: int
    end: int
    confidence: float
    detector: str
    source: Optional[str] = None

    def to_dict(self):
        return asdict(self)
