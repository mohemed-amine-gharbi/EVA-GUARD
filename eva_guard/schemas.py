"""Contrats de données échangés entre les agents (sérialisables en JSON)."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Alert:
    t: int
    score: float
    suspected_type: Optional[str]
    top_features: list

    def to_dict(self):
        return asdict(self)


@dataclass
class Hypothesis:
    attack: str                      # "eclipse" | "dos_p2p" | "benign" | "unknown"
    confidence: float
    rationale: str
    cited_docs: List[str] = field(default_factory=list)
    evidence_to_check: list = field(default_factory=list)
    backend: str = "offline-rag"

    def to_dict(self):
        return asdict(self)


@dataclass
class Evidence:
    indicator: str
    source: str
    value: float
    threshold: float
    direction: str
    passed: bool


@dataclass
class Decision:
    verdict: str                     # "CONFIRMED" | "NOT_CONFIRMED" | "NO_ALERT"
    attack: Optional[str]
    t_decision: Optional[int]
    reason: str
    evidence: List[Evidence] = field(default_factory=list)
    rule: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        return d
