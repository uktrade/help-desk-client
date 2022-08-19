import json
import logging
import pprint
import requests

from zenpy.lib.api_objects import Comment

from helpdesk_client.zendesk_client import ZenDeskClient
from helpdesk_client.interfaces import HelpDeskTicket, HelpDeskError


class HelpDeskClient():
    def __init__(self, *args, **kwargs):
        self.client = ZenDeskClient(*args, **kwargs)

    def create_helpdesk_ticket(self, ticket: HelpDeskTicket,comment=None) -> HelpDeskTicket:
        #subject, full_name, email_address, payload, service_name, subdomain
        # client, chat_id, user_id, group_id, recipient_email, subject, slack_message_url
        
        if not ticket.user_id:
            if ticket.userdetails:
                ticket.user_id = self.client.get_or_create_user(
                    ticket.userdetails['full_name'],
                    ticket.userdetails['email']
                    )
            else:
                raise HelpDeskError("Ticket has no user id or user details")

        return self.client.create_ticket(ticket,comment)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        return self.client.get_ticket(ticket_id)

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        return self.client.close_ticket(ticket_id)

    def add_comment(self, ticket: HelpDeskTicket, comment: str) -> HelpDeskTicket:
        return self.client.add_comment(ticket,comment)

    def helpdesk_ticket_url(self,helpdesk_ticket_uri, ticket_id):
        # handle trailing slash being there or not (urljoin doesn't).
        return '/'.join([helpdesk_ticket_uri.rstrip('/'), str(ticket_id)])

    @staticmethod
    def helpdesk_oauth( *args,**kwargs) -> json:
        return ZenDeskClient.oauth(*args,**kwargs)
