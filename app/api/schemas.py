from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    keywords: str = ""

    @field_validator("keywords", mode="before")
    @classmethod
    def _normalize_keywords(cls, v: str) -> str:
        seen: list[str] = []
        for part in (v or "").split(","):
            kw = part.strip().lower()
            if kw and kw not in seen: # remoive duplicates
                seen.append(kw)
        return ",".join(seen)


class AccountRead(ORMModel):
    id: int
    name: str
    created_at: datetime


class SourceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)


class SourceRead(ORMModel):
    id: int
    key: str
    name: str
    created_at: datetime


class SourceLinkCreate(BaseModel):
    source_id: int


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    account_id: int


class UserRead(ORMModel):
    id: int
    name: str
    email: str
    account_id: int
    created_at: datetime


class EventCreate(BaseModel):
    account_id: int
    source_id: int
    payload: str = Field(min_length=1)


class EventRead(ORMModel):
    id: int
    account_id: int
    source_id: int
    payload: str
    created_at: datetime
