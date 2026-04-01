from pydantic import BaseModel
from typing import Optional

class SectionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None