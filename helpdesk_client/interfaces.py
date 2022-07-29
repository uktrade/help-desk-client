import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class Priority(IntEnum):
    URGENT = 10
    HIGH = 8
    NORMAL = 4
    LOW = 2


@dataclass
class HelpDeskTicket:
    requestor: str
    topic: str
    email: str
    priority: Priority
    body: str
    created_at: datetime.datetime
    deleted_at: datetime.datetime
    id: Optional[int] = None
    responder: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
    closed_at: Optional[datetime.datetime] = None
    due_at: Optional[datetime.datetime] = None
    other: Optional[dict] = None


class HelpDeskError(Exception):
    pass


class HelpDeskBase(ABC):
    @abstractmethod
    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def close_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError


class HelpDeskStubbed(HelpDeskBase):
    def __init__(self) -> None:
        self._next_ticket_id = 1
        self._tickets: dict[int, HelpDeskTicket] = {}

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        self._tickets[self._next_ticket_id] = ticket
        ticket.id = self._next_ticket_id

        self._next_ticket_id += 1

        return ticket

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        return self._tickets[ticket_id]

    def close_ticket(self, ticket_id: int) -> None:
        ticket = self._tickets[ticket_id]
        ticket.closed_at = datetime.datetime.now()

        return None

    def delete_ticket(self, ticket_id: int) -> None:
        del self._tickets[ticket_id]

        return None

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        if ticket.id is None:
            raise HelpDeskError("Ticket has no ID")

        ticket.updated_at = datetime.datetime.now()

        self._tickets[ticket.id] = ticket

        return ticket
