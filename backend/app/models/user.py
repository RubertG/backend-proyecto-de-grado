from typing import Literal
from pydantic import BaseModel, EmailStr, Field

UserRole = Literal['admin', 'student']

class UserOut(BaseModel):
    id: str
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    role: UserRole
