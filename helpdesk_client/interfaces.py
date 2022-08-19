import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
import json
from typing import Optional


class Priority(IntEnum):
    URGENT = 10
    HIGH = 8
    NORMAL = 4
    LOW = 2


@dataclass
class HelpDeskTicket:  
    topic: str 
    body: str
    created_at: Optional[datetime.datetime] = None
    id: Optional[int] = None
    user_id: Optional[int] = None
    userdetail: Optional[dict] = None
    priority: Optional[Priority] = None
    recipient_email: Optional[str] = None
    responder: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
    status: Optional[str] = None
    due_at: Optional[datetime.datetime] = None
    other: Optional[dict] = None

class HelpDeskError(Exception):
    pass


class HelpDeskBase(ABC):

    @abstractmethod
    def get_or_create_user(self, full_name: str, email_address: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def create_ticket(self, ticket: HelpDeskTicket, comment: Optional[str]) -> HelpDeskTicket:
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
    def add_comment(self, ticket: HelpDeskTicket, comment: str) -> HelpDeskTicket:
        raise NotImplementedError 

    @abstractmethod
    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError

    @staticmethod
    def oauth(subdomain:str, redirect_uri: str, credentials: dict, code: str) -> json:
        raise NotImplementedError


class HelpDeskStubbed(HelpDeskBase):
    def __init__(self) -> None:
        self._next_ticket_id = 1
        self._tickets: dict[int, HelpDeskTicket] = {}
        self._next_user_id = 1

    def get_or_create_user(self, full_name: str, email_address: str) -> int:
        user_id = self._next_user_id
        self._next_user_id += 1
        return user_id

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
