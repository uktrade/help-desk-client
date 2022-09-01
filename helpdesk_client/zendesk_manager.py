# -*- coding: utf-8 -*-
import json
import logging
import pprint
import requests

from zenpy import Zenpy
from zenpy.lib import exception
from zenpy.lib.api_objects import Comment, Ticket, CustomField, User as ZendeskUser

from helpdesk_client.interfaces import HelpDeskBase, HelpDeskComment, HelpDeskTicket,HelpDeskUser,HelpDeskError,HelpDeskCustomField



class ZenDeskManager(HelpDeskBase):
    def __init__(self, **kwargs):
        """Create a new zendesk client can pass credentials or existing client

        :param client: pass existing Zenpy client or None
         OR
        :param credentials: The credentials required to create client { token , email, subdomain}

        if no client or credentials created sets client to None

        """
        def build_client(credentials):
            return Zenpy(
                timeout=5,
                email=credentials['email'],
                token=credentials['token'],
                subdomain=credentials['subdomain']
            ) if credentials else None

        self.client = kwargs.get('client',build_client(kwargs.get('credentials',None)))

    def get_or_create_user(self, user: HelpDeskUser = None) -> HelpDeskUser:
        """Get or Create a new zendesk user   /PS-IGNORE

        :param HelpDeskUser
                full_name: string full name for Zendesk user.
                email: string email address text for the Zendesk user.

        :returns: HelpDeskUser for zendesk user.
        """
        print(user)
        zendesk_user = self.transform_to_zendesk_user(user)
        print(zendesk_user)
        return self.transform_to_helpdesk_user(self.client.users.create_or_update(zendesk_user))

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Create a new zendesk ticket in response to a new user question.

        :param ticket: HelpDeskTicket with information to create

        :returns: A HelpDeskTicket instance.
        """

        ticket.user = self.get_or_create_user(ticket.user)

        #add comment if included
        if ticket.comment and not ticket.comment.author_id:
            ticket.comment.author_id = ticket.user.id

        issue = self.transform_to_zendesk_api_ticket(ticket)
        ticket_audit = self.client.tickets.create(issue)
        return self.transform_from_zendesk_api_ticket(ticket_audit.ticket)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Recover the ticket by it's ID in zendesk.

        :param ticket_id: The Zendesk ID of the Ticket.

        :returns: A HelpDeskTicket instance or None if nothing was found.
        """
        log = logging.getLogger(__name__)
        returned = None
        log.debug(f'Look for Ticket by is Zendesk ID:<{ticket_id}>') #debug line /PS-IGNORE
        try:
            returned = self.client.tickets(id=ticket_id)
        except exception.RecordNotFoundException:
            log.debug(f'Ticket not found by is Zendesk ID:<{ticket_id}>') #debug line /PS-IGNORE

        return self.transform_from_zendesk_api_ticket(returned)

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Close a ticket in zendesk.

        :param ticket_id: The Zendesk Ticket ID.

        :returns: None or HelpDeskTicket instance closed.
        """
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

    def add_comment(self, ticket_id: int, comment: HelpDeskComment) -> HelpDeskTicket:
        """Add a new comment to an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :param comment: The HelpDeskComment for the Zendesk comment.

        :returns: The updated HelpDeskTicket instance.
        """
        if not comment.author_id:
            comment.author_id = self.client.users.me().id
        ticket = self.get_ticket(ticket_id)
        ticket.comment = comment
        return self.update_ticket(ticket)

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Update an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :returns: The updated HelpDeskTicket instance.
        """
        ticket = self.transform_to_zendesk_api_ticket(ticket)
        ticket_audit = self.client.tickets.update(ticket)
        return self.transform_from_zendesk_api_ticket(ticket_audit.ticket) if ticket_audit else None

    def transform_to_zendesk_api_ticket(self,ticket: HelpDeskTicket) -> Ticket:
        """Transform from HelpDeskTicket to Ticket instance

        :param ticket: HelpDeskTicket with ticket to transfrom.

        :returns: The transformed Ticket instance.
        """
        field_mapping = {
                'id':
                    lambda ticket : ('id',ticket.id),
                'status':
                    lambda ticket : ('status',ticket.status),
                'recipient':
                    lambda ticket : ('recipient',ticket.recipient_email),
                'subject':
                    lambda ticket : ('subject',ticket.topic),
                'description':
                    lambda ticket : ('description',ticket.body) ,
                'submitter_id':
                    lambda ticket : ('submitter_id',ticket.user.id),
                'requester_id':
                    lambda ticket : ('requester_id',ticket.user.id),
                'assingee_id':
                    lambda ticket : ('assingee_id',ticket.user.id) ,
                'requester':
                    lambda ticket: ('requester',ZendeskUser(
                        id=ticket.user.id,
                        name=ticket.user.full_name,
                        email=ticket.user.email,
                    )),
                'group_id':
                    lambda ticket : ('group_id',ticket.group_id),
                'external_id':
                    lambda ticket : ('external_id',ticket.external_id),
                'tags':
                    lambda ticket : ('tags',ticket.tags),
                'custom_fields':
                    lambda ticket :
                    ('custom_fields', [ 
                        CustomField(id=custom_field.id,value=custom_field.value)
                        for custom_field in  ticket.custom_fields] ) if
                    ticket.custom_fields else None,
                'comment':
                    lambda ticket :
                    ('comment',
                        Comment(
                            body=ticket.comment.body,
                            author_id=ticket.comment.author_id if
                                ticket.comment.author_id else self.client.users.me().id,
                            public=ticket.comment.public
                        )
                    ) if
                    ticket.comment else None
        }


        # creates a list of tuples (field, value)
        # mapping the fields from the HelpDeskTicket to Ticket object
        # that are passed into ZenPy ticket object to set the tickets data
        return Ticket(
            **dict(
                [fieldtuple for function in field_mapping.values()
                    if (fieldtuple := function(ticket))
                if fieldtuple is not None
                ])
        )


    def transform_from_zendesk_api_ticket(self, ticket: Ticket) -> HelpDeskTicket:
        """Transform from Ticket to HelpDeskTicket instance

        :param ticket: Ticket instance with ticket to transfrom.

        :returns: The transformed HelpDeskTicket instance.
        """
        field_mapping = {
                    'id':
                        lambda ticket :
                            ('id',getattr(ticket,'id')) if
                            getattr(ticket,'id') else None,
                    'status':
                        lambda ticket :
                            ('status',getattr(ticket,'status')) if
                            getattr(ticket,'status',None) else None,
                    'recipient_email':
                        lambda ticket :
                            ('recipient_email',getattr(ticket,'recipient' )) if
                            getattr(ticket,'recipient',None) else None,
                    'topic':
                        lambda ticket :
                            ('topic',getattr(ticket,'subject')) if
                            getattr(ticket,'subject') else None,
                    'body':
                        lambda ticket :
                            ('body',getattr(ticket,'description')) if
                            getattr(ticket,'description') else None,
                    'user':
                        lambda ticket :
                            ('user',HelpDeskUser(
                                id=ticket.requester.id,
                                full_name=ticket.requester.name,
                                email=ticket.requester.email,
                            )) if
                            getattr(ticket,'requester',None) else None,
                    'created_at':
                        lambda ticket :
                            ('created_at',getattr(ticket,'created_at')) if
                            getattr(ticket,'created_at',None) else None,
                    'updated_at':
                        lambda ticket :
                            ('updated_at',getattr(ticket,'updated_at')) if
                            getattr(ticket,'updated_at',None) else None,
                    'priority':
                        lambda ticket :
                            ('priority',getattr(ticket,'priority')) if
                            getattr(ticket,'priority',None) else None,
                    'due_at':
                        lambda ticket :
                            ('due_at',getattr(ticket,'due_at')) if
                            getattr(ticket,'due_at',None) else None,
                    'group_id':
                        lambda ticket :
                            ('group_id',getattr(ticket,'group_id' )) if
                            getattr(ticket,'group_id',None) else None,
                    'external_id':
                        lambda ticket :
                            ('external_id',(getattr(ticket,'external_id' ))) if
                            getattr(ticket,'external_id',None) else None,
                    'tags':
                        lambda ticket :
                            ('tags',getattr(ticket,'tags')) if
                            getattr(ticket,'tags',None) else None,
                    'custom_fields':
                        lambda ticket :
                            ('custom_fields',[
                                HelpDeskCustomField(id=custom_field.id,value=custom_field.value)
                                for custom_field in getattr(ticket,'custom_fields' )
                            ]) if
                            getattr(ticket,'custom_fields',None) else None,
                    'comment':
                        lambda ticket :
                            ('comment',
                                HelpDeskComment(
                                    body=ticket.comment.body,
                                    author_id=ticket.comment.author_id,
                                    public=ticket.comment.public
                                )
                                if getattr(ticket,'comment',None) else None),
                    'other':{
                    }
            }
        def map_field(function,ticket,field):
            if isinstance(function, dict):
                # If mapping to dictinary process nested fields and
                # return a tuple with the field and nested dictionary
                
                return (field,
                    dict([
                            fieldtuple for nested_field in function
                            if (fieldtuple := map_field(function[nested_field],ticket,nested_field))
                            if fieldtuple is not None
                            ]))
            else:
                # return field and value tuple
                return function(ticket)

        if not ticket:
            return None
        return HelpDeskTicket( **dict([
                    fieldtuple for field,function in field_mapping.items()
                    if (fieldtuple := map_field(function,ticket,field))
                    if fieldtuple is not None #filters out fields which were not in the ticket
                    ]
                ))

    def transform_to_zendesk_user(self,user:HelpDeskUser) -> ZendeskUser:
        # if no user details use cached user
        if user and user.id:
            return ZendeskUser(id=user.id)
        elif user and (user.email and user.full_name):
            return ZendeskUser(name=user.full_name,email=user.full_name)
        elif not user or not user.id or not (user.email and user.full_name):
            return self.client.users.me()

    def transform_to_helpdesk_user(self,user:ZendeskUser) -> HelpDeskUser:
        return HelpDeskUser(id=user.id,full_name=user.name,email=user.email
        )

    @staticmethod
    def oauth(subdomain:str, redirect_uri, credentials, code= None) -> json:
        """Complete the Zendesk OAuth process recovering the access_token needed to
        perform API requests to the Zendesk Support API.

        :param subdomain: Zendesk Subdomain

        :param redirect_uri: Uri to redirect after oauth.

        :param credentials required for oauth { client_id & client_secret }.

        :returns: data in json format
        """
        log = logging.getLogger(__name__)

        if not code:
            log.error("The code parameter was missing in the request!")
            return '{ "error": "The code parameter was missing in the request!"}'

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
        return data