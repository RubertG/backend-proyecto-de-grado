from pydantic import BaseModel, Field
from typing import Optional

class GuideBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content_html: Optional[str] = None
    order: int = Field(ge=0)
    topic: Optional[str] = None
    is_active: bool = True

class GuideCreate(GuideBase):
    pass

class GuideUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_html: str | None = None
    order: int | None = Field(default=None, ge=0)
    topic: str | None = None
    is_active: bool | None = None

class GuideOut(GuideBase):
    id: str
