import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Priority(Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TicketType(Enum):
    QUESTION = "question"
    INCIDENT = "incident"
    PROBLEM = "problem"
    TASK = "task"


class Status(Enum):
    CLOSED = "closed"
    NEW = "new"
    PENDING = "pending"
    OPEN = "open"


@dataclass
class HelpDeskUser:
    id: Optional[int]
    full_name: Optional[str]
    email: Optional[str]


@dataclass
class HelpDeskComment:
    body: str
    public: bool = True
    author_id: Optional[int]


@dataclass
class HelpDeskCustomField:
    id: int
    value: str


@dataclass
class HelpDeskGroup:
    created_at: Optional[datetime.datetime]
    default: Optional[bool]
    deleted: Optional[bool]
    description: Optional[str]
    id: Optional[int]
    is_public: Optional[bool]
    name: str
    updated_at: Optional[datetime.datetime]
    url: Optional[str]


@dataclass
class HelpDeskTicket:
    subject: str
    id: int
    description: Optional[str]
    user: Optional[HelpDeskUser]
    group_id: Optional[int]
    external_id: Optional[int]
    assignee_id: Optional[int]
    comment: Optional[HelpDeskComment]
    tags: Optional[List[str]]
    custom_fields: Optional[List[HelpDeskCustomField]]
    recipient_email: Optional[str]
    responder: Optional[str]
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]
    due_at: Optional[datetime.datetime]
    status: Optional[Status]
    priority: Optional[Priority]
    ticket_type: Optional[TicketType]


class HelpDeskException(Exception):
    pass


class HelpDeskTicketNotFoundException(Exception):
    pass


class HelpDeskBase(ABC):
    @abstractmethod
    def get_or_create_user(self, user: HelpDeskUser) -> HelpDeskUser:
        raise NotImplementedError

    @abstractmethod
    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def add_comment(self, ticket_id: int, comment: HelpDeskComment) -> HelpDeskTicket:
        raise NotImplementedError

    @abstractmethod
    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError


class HelpDeskStubbed(HelpDeskBase):
    def __init__(self, *args, **kwargs) -> None:
        self.id = 1
        self._next_ticket_id = 2
        self._tickets: Dict[int, HelpDeskTicket] = {}
        self._users: Dict[int, HelpDeskUser] = {}
        self._next_user_id = 1

    def get_or_create_user(self, user: HelpDeskUser) -> HelpDeskUser:

        if user.id:
            user_id = user.id
        else:
            user_id = self._next_user_id
            self._next_user_id += 1

        if not self._users[user_id]:
            self._users[user_id] = user

        return self._users[user_id]

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        ticket.created_at = datetime.datetime.now()
        self._tickets[self._next_ticket_id] = ticket
        ticket.id = self._next_ticket_id

        self._next_ticket_id += 1

        return ticket

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        if self._tickets.get(ticket_id):
            return self._tickets.get(ticket_id)
        else:
            raise HelpDeskTicketNotFoundException

    def add_comment(self, ticket_id: int, comment: HelpDeskComment) -> HelpDeskTicket:
        if self._tickets.get(ticket_id):
            self._tickets[ticket_id].comment = comment
            self._tickets[ticket_id].updated_at = datetime.datetime.now()
            return self._tickets[ticket_id]
        else:
            raise HelpDeskTicketNotFoundException

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:

        if self._tickets.get(ticket_id):
            self._tickets[ticket_id].status = Status.CLOSED
            self._tickets[ticket_id].updated_at = datetime.datetime.now()
            return self._tickets[ticket_id]
        else:
            raise HelpDeskTicketNotFoundException

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:

        if self._tickets.get(ticket.id):
            self._tickets[ticket.id] = ticket
            self._tickets[ticket.id].updated_at = datetime.datetime.now()
            return self._tickets[ticket.id]
        else:
            raise HelpDeskTicketNotFoundException
