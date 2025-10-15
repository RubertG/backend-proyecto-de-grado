from pydantic import BaseModel, Field
from typing import Optional


class AttemptUser(BaseModel):
    id: str
    name: str
    email: str
    role: str

class AttemptBase(BaseModel):
    exercise_id: str
    submitted_answer: Optional[str] = None
    completed: bool = False

class AttemptCreate(AttemptBase):
    pass

class AttemptOut(AttemptBase):
    id: str
    # user_id se mantiene para compatibilidad interna, pero para el frontend se provee 'user'
    user_id: Optional[str] = None
    user: AttemptUser
    structural_validation_passed: bool | None = None
    structural_validation_errors: list[str] | None = None
    structural_validation_warnings: list[str] | None = None
    llm_feedback: str | None = None  # Se mantiene el campo pero no se genera aquí
