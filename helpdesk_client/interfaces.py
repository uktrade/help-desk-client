import datetime

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator, List, Optional, Dict

class Priority(Enum):
    URGENT=10
    HIGH = 8
    NORMAL = 4
    LOW = 2


@dataclass
class HelpDeskTicket:
    id:  int
    requestor: str
    responder: Optional [str]
    topic: str
    email: str
    priority: Priority
    body: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    deleted_at: datetime.datetime
    updated_at: Optional [datetime.datetime]
    closed_at: Optional [datetime.datetime]
    due_at: Optional [datetime.datetime]
    other: Optional [Dict]


class HelpDeskBase(ABC):
    @abstractmethod
    def create_ticket(self) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def close_ticket(self, ticket_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_ticket(self, ticket_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError


class HelpDeskStubbed(HelpDeskBase):
    pass