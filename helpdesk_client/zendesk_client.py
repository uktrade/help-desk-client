import logging
from zenpy import Zenpy

from helpdesk_client.interfaces import HelpDeskBase, HelpDeskTicket


class ZenDeskClient(HelpDeskBase):
    def __init__(self, email, token, subdomain):
        self.client = Zenpy(
            timeout=5, email=email, token=token, subdomain=subdomain
        )
    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        return self.client.tickets.create(ticket)

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        return self.client.tickets.create(ticket)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        raise NotImplementedError

    def close_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    def delete_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        raise NotImplementedError

