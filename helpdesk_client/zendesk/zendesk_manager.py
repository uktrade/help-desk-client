# -*- coding: utf-8 -*-
import json
import logging
import pprint
import requests

from zenpy import Zenpy
from zenpy.lib import exception
from zenpy.lib.api_objects import User as ZendeskUser

from helpdesk_client.interfaces import HelpDeskBase, HelpDeskTicket,HelpDeskError
from helpdesk_client.zendesk.utils import transform_from_zen_api_ticket, transform_to_zen_api_ticket


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

    def get_or_create_user(self, full_name: str, email_address: str) -> int:
        """Get or Create a new zendesk user

        :param full_name: string full name for Zendesk user.

        :param email_address: string email address text for the Zendesk user.

        :returns: user_id for zendesk user.
        """
        zendesk_user = ZendeskUser(name=full_name, email=email_address)
        return self.client.users.create_or_update(zendesk_user).id

    def create_ticket(self, ticket: HelpDeskTicket,comment: str =None) -> HelpDeskTicket:
        """Create a new zendesk ticket in response to a new user question.

        :param ticket: HelpDeskTicket with information to create

        :param comment: The text for the Zendesk comment.

        :returns: A HelpDeskTicket instance.
        """

        #if no userid try use user details and get/create user
        if not ticket.user_id:
            if ticket.userdetails:
                ticket.user_id = self.get_or_create_user(
                    ticket.userdetails['full_name'],
                    ticket.userdetails['email']
                    )
            else:
                raise HelpDeskError("Ticket has no user id or user details")

        #add comment if included
        if comment:
            ticket.other['comment'] = (comment,ticket.user_id)


        issue = transform_to_zen_api_ticket(ticket)
        ticket_audit = self.client.tickets.create(issue)
        return transform_from_zen_api_ticket(ticket_audit.ticket)

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

        return transform_from_zen_api_ticket(returned)

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

    def add_comment(self, ticket: HelpDeskTicket, comment: str) -> HelpDeskTicket:
        """Add a new comment to an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :param comment: The text for the Zendesk comment.

        :returns: The updated HelpDeskTicket instance.
        """
        requestor = self.client.users.me()
        ticket.other['comment'] = (comment,requestor.id)
        return self.update_ticket(ticket)

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Update an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :returns: The updated HelpDeskTicket instance.
        """
        ticket = transform_to_zen_api_ticket(ticket)
        ticket_audit = self.client.tickets.update(ticket)
        return transform_from_zen_api_ticket(ticket_audit.ticket) if ticket_audit else None


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
