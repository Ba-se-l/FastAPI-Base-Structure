from pydantic import BaseModel as Base
from datetime import datetime

from .enum import TokenType

class TokenPayload(Base):
    sub: str 
    type: TokenType
    jti: str | None = None
    iat: datetime
    exp: datetime