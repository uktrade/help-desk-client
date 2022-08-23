from datetime import datetime
import json
import logging
import pprint
from tokenize import group
import requests

from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket
from zenpy.lib.api_objects import Comment
from zenpy.lib.api_objects import User as ZendeskUser
from zenpy.lib import exception

from helpdesk_client.interfaces import HelpDeskBase, HelpDeskTicket


class ZenDeskClient(HelpDeskBase):
    def __init__(self, *args, client=None,subdomain=None, credentials=None , **kwargs):
        self.client = client if client else Zenpy(
            timeout=5, email=credentials['email'], token=credentials['token'], subdomain=subdomain
        )

    def get_or_create_user(self, full_name: str, email_address: str) -> int:
        zendesk_user = ZendeskUser(name=full_name, email=email_address)
        return self.client.users.create_or_update(zendesk_user).id

    def create_ticket(self, ticket: HelpDeskTicket,comment=None) -> HelpDeskTicket:
        if comment:
            ticket.other['comment'] = {
                'body':comment,
                'author_id':ticket.user_id
            }


        issue = self.transform_to_api_ticket(ticket)
        ticket_audit = self.client.tickets.create(issue)
        return self.transform_from_api_object(ticket_audit.ticket)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        log = logging.getLogger(__name__)
        returned = None
        log.debug(f'Look for Ticket by is Zendesk ID:<{ticket_id}>') #debug line /PS-IGNORE
        try:
            returned = self.client.tickets(id=ticket_id)
        except exception.RecordNotFoundException:
            log.debug(f'Ticket not found by is Zendesk ID:<{ticket_id}>') #debug line /PS-IGNORE

        print(returned)
        return self.transform_from_api_object(returned)

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        log = logging.getLogger(__name__)
        log.debug(f'Looking for ticket with ticket_id:<{ticket_id}>')
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            log.warning(f'The ticket:<{ticket_id}> not found!')
        elif ticket.status == 'closed':
            log.warning(f'The ticket:<{ticket.id}> has already been closed!')
        else:
            ticket.status = 'closed'
            ticket = self.update_ticket(ticket)
            log.debug(f'Closed ticket:<{ticket.id}> for ticket_id:<{ticket_id}>')

        return ticket



    def delete_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    def add_comment(self, ticket: HelpDeskTicket, comment: str) -> HelpDeskTicket:
        requestor = self.client.users.me()
        ticket.other['comment'] = {
                'body':comment,
                'author_id':requestor.id
            }
        return self.update_ticket(ticket)

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        ticket = self.transform_to_api_ticket(ticket)
        ticket_audit = self.client.tickets.update(ticket)
        return self.transform_from_api_object(ticket_audit.ticket) if ticket_audit else None


    @staticmethod
    def oauth(subdomain, redirect_uri, credentials, code= None) -> json:
        log = logging.getLogger(__name__)

        if not code:
            log.error("The code parameter was missing in the request!")
            return '{ "status": "400", "error": "The code parameter was missing in the request!"}'

        request_url = f"https://{subdomain}.zendesk.com/oauth/tokens"
        log.debug(
            f"Received Zendesk OAuth request code:<{code}>. " #debug line /PS-IGNORE
            f"Recovering access token from {request_url}. "   #debug line /PS-IGNORE
            f"Redirect URL is {redirect_uri}. "               #debug line /PS-IGNORE
        )

        data = {
            'code': code,
            'client_id': credentials['client_id'],
            'client_secret': credentials['client_secret'],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }

        response = requests.post(
            request_url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        
        log.debug(f"Result status from Zendesk:<{response.status_code}>")
        response.raise_for_status()
        data = response.json()
        log.debug(f"Result status from Zendesk:\n{pprint.pformat(data)}>")
        print(data)
        return data

    def transform_to_api_ticket(self,ticket: HelpDeskTicket) -> Ticket:
        field_mapping = {
                'group_id': lambda x: x.other['group_id'],
                'external_id': lambda x: x.other['external_id'],
                'tags': lambda x: x.other['tags'],
                'custom_fields': lambda x: x.other.get('custom_fields') or [],
                'comment': lambda x: Comment( body=x.other['comment'].get('body'),
                                            author_id=x.other['comment'].get('author_id')),
        }
        optional_field_mapping = {
                'id': 'id',
                'status': 'status',
                'recipient_email': 'recipient',
        }
            
         
        zenticket = {
            "id": ticket.id,
            "status": ticket.status,
            "subject":ticket.topic,
            "description": ticket.body,
            "submitter_id":ticket.user_id,
            "requester_id":ticket.user_id,
            "assingee_id":ticket.user_id, 
            "recipient": ticket.recipient_email,
        }

        for optional_field,value in optional_field_mapping.items():
            if getattr(ticket,optional_field):
                zenticket[value] = getattr(ticket,optional_field)

        if not getattr(ticket,'other', None):
            return Ticket( **zenticket )
        for other_field in getattr(ticket,'other'):
            zenticket[other_field] = field_mapping[other_field](ticket) if field_mapping.get(other_field) else None

        return Ticket(
            **zenticket
        )


    def transform_from_api_object(self,ticket: Ticket) -> HelpDeskTicket:
        if not ticket:
            return None
        data = {
            'id':getattr(ticket,'id'),
            'topic':getattr(ticket,'subject'),
            'body':getattr(ticket,'description'),
            'created_at': getattr(ticket,'created_at', None),
            'updated_at': getattr(ticket,'updated_at',None),
            'status': getattr(ticket,'status',None),
            'user_id':getattr(ticket,'requester_id',None),
            'priority': getattr(ticket,'priority',None),
            'recipient_email': getattr(ticket,'recipient' , None),
            'due_at': getattr(ticket,'due_at' , None),
            'other': {}
        }
        if getattr(ticket,'custom_fields', None):
            data['other']['custom_fields']= ticket.custom_fields
        
        if getattr(ticket,'comment',None):
            data['other']['comment'] = { 'body':ticket.comment.body, 'author_id':ticket.comment.author_id }
        if getattr(ticket,'external_id',None):
            data['other']['external_id'] = ticket.external_id
        if getattr(ticket,'group_id',None):
            data['other']['group_id'] = ticket.group_id
        if getattr(ticket,'tags',None):
            data['other']['tags'] = ticket.tags

        return HelpDeskTicket( **data ) 