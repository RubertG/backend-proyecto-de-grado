from pydantic import BaseModel, Field
from typing import Literal, Optional

ExerciseType = Literal['command', 'dockerfile', 'conceptual']

class ExerciseBase(BaseModel):
    guide_id: str
    title: str = Field(min_length=1, max_length=255)
    content_html: Optional[str] = None
    difficulty: str = Field(min_length=1, max_length=50)
    expected_answer: str = Field(min_length=1)
    ai_context: Optional[str] = None
    type: ExerciseType
    is_active: bool = True
    enable_structural_validation: bool = True
    enable_llm_feedback: bool = True

class ExerciseCreate(ExerciseBase):
    pass

class ExerciseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_html: str | None = None
    difficulty: str | None = Field(default=None, min_length=1, max_length=50)
    expected_answer: str | None = Field(default=None, min_length=1)
    ai_context: str | None = None
    type: ExerciseType | None = None
    is_active: bool | None = None
    enable_structural_validation: bool | None = None
    enable_llm_feedback: bool | None = None

class ExerciseOut(ExerciseBase):
    id: str
