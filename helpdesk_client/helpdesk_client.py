# -*- coding: utf-8 -*-
import json
from helpdesk_client.interfaces import HelpDeskTicket,HelpDeskBase
from helpdesk_client.zendesk.zendesk_manager import ZenDeskManager


class HelpDeskClient():
    def __init__(self, manager: HelpDeskBase):
        self.manager = manager

    def create_helpdesk_ticket(self, ticket: HelpDeskTicket,comment: str=None) -> HelpDeskTicket:
        return self.manager.create_ticket(ticket,comment)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        return self.manager.get_ticket(ticket_id)

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        return self.manager.close_ticket(ticket_id)

    def add_comment(self, ticket: HelpDeskTicket, comment: str) -> HelpDeskTicket:
        return self.manager.add_comment(ticket,comment)

    @staticmethod
    def helpdesk_oauth( *args,**kwargs) -> json:
        return ZenDeskManager.oauth(*args,**kwargs)
