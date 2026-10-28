from pydantic import BaseModel


class MatchItem(BaseModel, extra="forbid"):
    requirement: str
    explanation: str


class MatchResult(BaseModel, extra="forbid"):
    matches: list[MatchItem]
    gaps: list[MatchItem]
