from datetime import datetime
from pydantic import BaseModel as Base, ConfigDict



class UserResponse(Base):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
