import datetime
import json
from dataclasses import dataclass
from typing import List, Optional

import requests


class HaloClientNotFoundException(Exception):
    pass


@dataclass
class Ticket:
    id: int
    summary: str
    user_id: int
    status_id: Optional[int]  # todo get status id from halo
    priority_id: Optional[int]  # todo get priority id from halo
    emailcclist: Optional[List[str]]
    details: Optional[str]
    agent_id: Optional[int]
    team_id: Optional[int]
    ticket_tags: Optional[str]
    third_party_id: Optional[int]  # /PS-IGNORE
    custom_fields: Optional[List[object]]
    # comment:
    tickettype_id: Optional[int]
    datecreated: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None


class RecordNotFoundException(Exception):
    pass


class Halo(object):
    access_token: str
    scope: List[str]
    subdomain: str
    token_type: str
    created_at: datetime.datetime

    class HaloUsers(object):
        def __init__(self, parent) -> None:
            self.parent = parent

        def __call__(self, id: int = 0) -> object:
            if id != 0:
                request_url = (
                    f"https://{self.parent.subdomain}.haloitsm.com/api/users/{id}"
                )
                response = requests.get(
                    request_url,
                    headers={"Authorization": f"Bearer {self.parent.access_token}"},
                )
                user = response.json()
                return user
            else:
                return None

        def create_or_update(self, user: object) -> object:
            request_url = f"https://{self.parent.subdomain}.haloitsm.com/api/users"
            response = requests.post(
                request_url,
                data=json.dumps(user),
                headers={
                    "Authorization": f"Bearer {self.parent.access_token}",
                    "Content-Type": "application/json",
                },
            )
            user_data = response.json()
            return user_data

    class HaloTickets(object):
        def __init__(self, parent) -> None:
            self.parent = parent

        def __call__(self, id: int = 0) -> object:
            if id != 0:
                request_url = (
                    f"https://{self.parent.subdomain}.haloitsm.com/api/tickets/{id}"
                )
                response = requests.get(
                    request_url,
                    headers={
                        "Authorization": f"Bearer {self.parent.access_token}",
                    },
                )
                ticket = response.json()
                return ticket
            else:
                return None

        def create(self, tickets: List[Ticket]) -> List[Ticket]:
            request_url = f"https://{self.parent.subdomain}.haloitsm.com/api/tickets"
            response = requests.post(
                request_url,
                data=json.dumps(tickets),
                headers={
                    "Authorization": f"Bearer {self.parent.access_token}",
                    "Content-Type": "application/json",
                },
            )
            ticket_data = response.json()
            return ticket_data

        def update(self, ticket: object) -> object:
            if not ticket.id:
                return None

            request_url = f"https://{self.parent.subdomain}.haloitsm.com/api/tickets"
            response = requests.post(
                request_url,
                data=[json.dumps(ticket)],
                headers={
                    "Authorization": f"Bearer {self.parent.access_token}",
                    "Content-Type": "application/json",
                },
            )
            ticket_data = response.json()
            return ticket_data

    def _authenticate(self, credentials):
        data = {"scope": (credentials.get("scope", "all")).join(" ")}
        if credentials.get("grant_type") == "client_credentials":
            data["client_id"] = credentials.get("client_id")
            data["client_secret"] = credentials.get("client_secret")
            data["grant_type"] = credentials.get("grant_type")
        # can extend credential support
        else:
            raise HaloClientNotFoundException("Invalid credential grant type")

        request_url = f"https://{credentials.get('subdomain')}.haloitsm.com/auth/token"

        response = requests.post(
            request_url,
            data=json.dumps(data),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        response_data = None
        if response.status_code == 200:
            response_data = response.json()
            self.access_token = response_data["access_token"]
            self.token_type = response_data["token_type"]
            self.scope = response_data["scope"].split(" ")

        return response_data

    def reauthenticate(self, credentials):
        self._authenticate(credentials)

    def __init__(self, credentials):
        self._authenticate(credentials)
        self.subdomain = credentials.get("subdomain")
        self.users = self.HaloUsers(self)
        self.tickets = self.HaloTickets(self)
