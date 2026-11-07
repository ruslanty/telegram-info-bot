from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserInfo:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


@dataclass(frozen=True, slots=True)
class ChatInfo:
    id: int
    type: str
    title: str | None = None
