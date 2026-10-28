from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator


class CriticResult(BaseModel, extra="forbid"):
    passed: bool = Field(strict=True)
    issues: list[Annotated[str, Field(pattern=r"\S")]]

    @model_validator(mode="after")
    def validate_verdict(self) -> Self:
        if self.passed != (not self.issues):
            raise ValueError("Passed must be true if and only if there are no issues")
        return self
