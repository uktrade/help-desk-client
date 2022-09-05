# -*- coding: utf-8 -*-
import json
import logging
import pprint

import requests
from zenpy import Zenpy
from zenpy.lib import exception
from zenpy.lib.api_objects import Comment, CustomField, Ticket
from zenpy.lib.api_objects import User as ZendeskUser

from helpdesk_client.interfaces import (
    HelpDeskBase,
    HelpDeskComment,
    HelpDeskCustomField,
    HelpDeskError,
    HelpDeskTicket,
    HelpDeskUser,
)


logger = logging.getLogger(__name__)


class ZenDeskManager(HelpDeskBase):
    def __init__(self, **kwargs):
        """Create a new zendesk client can pass credentials or existing client

        :param client: pass existing Zenpy client or None
         OR
        :param credentials: The credentials required to create client { token , email, subdomain}

        if no client or credentials created sets client to None

        """

        self.client = (
            Zenpy(
                timeout=kwargs.get("credentials").get("timeout", 5),
                email=kwargs.get("credentials")["email"],
                token=kwargs.get("credentials")["token"],
                subdomain=kwargs.get("credentials")["subdomain"],
            )
            if kwargs.get("credentials")
            else None
        )

    def get_or_create_user(self, user: HelpDeskUser = None) -> HelpDeskUser:
        """Get or Create a new zendesk user   /PS-IGNORE

        :param HelpDeskUser
                full_name: string full name for Zendesk user.
                email: string email address text for the Zendesk user.

        :returns: HelpDeskUser for zendesk user.
        """

        transformed_user = self.__transform_helpdesk_to_zendesk_user(user)

        if transformed_user is None:
            logger.error("No Zendesk user to retrieve")  # Error log /PS-IGNORE,
            return None
        elif transformed_user.id:
            zendesk_user = self.client.users(id=transformed_user.id)
        else:
            zendesk_user = self.client.users.create_or_update(transformed_user)

        if zendesk_user is None:
            logger.error("No Zendesk user found")  # Error log /PS-IGNORE,
            return None
        return self.__transform_zendesk_to_helpdesk_user(zendesk_user)

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Create a new zendesk ticket in response to a new user question.

        :param ticket: HelpDeskTicket with information to create

        :returns: A HelpDeskTicket instance.
        """

        zendesk_audit = self.client.tickets.create(
            self.__transform_helpdesk_to_zendesk_ticket(ticket)
        )
        return self.__transform_zendesk_to_helpdesk_ticket(zendesk_audit.ticket)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Recover the ticket by it's ID in zendesk.

        :param ticket_id: The Zendesk ID of the Ticket.

        :returns: A HelpDeskTicket instance or None if nothing was found.
        """
        logger.debug(
            f"Look for Ticket by is Zendesk ID:<{ticket_id}>"  # debug line /PS-IGNORE
        )
        try:
            return self.__transform_zendesk_to_helpdesk_ticket(
                self.client.tickets(id=ticket_id)
            )
        except exception.RecordNotFoundException:
            logger.debug(
                f"Ticket not found by is Zendesk ID:<{ticket_id}>"  # debug line /PS-IGNORE
            )
            return None

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Close a ticket in zendesk.

        :param ticket_id: The Zendesk Ticket ID.

        :returns: None or HelpDeskTicket instance closed.
        """
        logger.debug(f"Looking for ticket with ticket_id:<{ticket_id}>")
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"The ticket:<{ticket_id}> not found!")
        elif ticket.status == "closed":
            logger.warning(f"The ticket:<{ticket.id}> has already been closed!")
        else:
            ticket.status = "closed"
            ticket = self.update_ticket(ticket)
            logger.debug(f"Closed ticket:<{ticket.id}> for ticket_id:<{ticket_id}>")

        return ticket

    def delete_ticket(self, ticket_id: int) -> None:
        raise NotImplementedError

    def add_comment(self, ticket_id: int, comment: HelpDeskComment) -> HelpDeskTicket:
        """Add a new comment to an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :param comment: The HelpDeskComment for the Zendesk comment.

        :returns: The updated HelpDeskTicket instance.
        """
        ticket = self.get_ticket(ticket_id)
        if ticket:
            ticket.comment = comment
            return self.update_ticket(ticket)
        else:
            return None

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Update an existing ticket.

        :param ticket: HelpDeskTicket with ticket to update.

        :returns: The updated HelpDeskTicket instance.
        """
        ticket_audit = self.client.tickets.update(
            self.__transform_helpdesk_to_zendesk_ticket(ticket)
        )
        if ticket_audit is None:
            logger.error(f"Ticket requested for update not found id {ticket.id}")
            return None

        return self.__transform_zendesk_to_helpdesk_ticket(ticket_audit.ticket)

    def __transform_helpdesk_to_zendesk_ticket(self, ticket: HelpDeskTicket) -> Ticket:
        """Transform from HelpDeskTicket to Ticket instance

        :param ticket: HelpDeskTicket with ticket to transfrom.

        :returns: The transformed Ticket instance.
        """
        field_mapping = {
            "id": lambda ticket: ticket.id,
            "status": lambda ticket: ticket.status,
            "recipient": lambda ticket: ticket.recipient_email,
            "subject": lambda ticket: ticket.topic,
            "description": lambda ticket: ticket.body,
            "submitter_id": lambda ticket: ticket.user.id,
            "assingee_id": lambda ticket: ticket.assingee_id,
            "priority": lambda ticket: ticket.priority,
            "requester": lambda ticket: ZendeskUser(
                id=getattr(ticket.user, "id", None),
                name=getattr(ticket.user, "full_name", None),
                email=getattr(ticket.user, "email", None),
            ),
            "group_id": lambda ticket: ticket.group_id,
            "external_id": lambda ticket: ticket.external_id,  # /PS-IGNORE
            "tags": lambda ticket: ticket.tags,
            "custom_fields": lambda ticket: [
                CustomField(id=custom_field.id, value=custom_field.value)
                for custom_field in ticket.custom_fields
            ]
            if ticket.custom_fields
            else None,
            "comment": lambda ticket: Comment(
                body=ticket.comment.body,
                author_id=ticket.comment.author_id
                if ticket.comment.author_id
                else ticket.user.id,
                public=ticket.comment.public,
            )
            if ticket.comment
            else None,
        }

        # get user from zendesk or create it if it does not exist
        # update user in ticket to one from zendesk as it is used in other fields
        user_from_zendesk = self.get_or_create_user(ticket.user)
        ticket.user = user_from_zendesk

        # creates a list of tuples (field, value)
        # mapping the fields from the HelpDeskTicket to Ticket object
        # that are passed into ZenPy ticket object to set the tickets data
        return Ticket(
            **dict(
                [
                    (field, value)
                    for field, transformation in field_mapping.items()
                    if (value := transformation(ticket))
                    if value is not None
                ]
            )
        )

    def __transform_zendesk_to_helpdesk_ticket(self, ticket: Ticket) -> HelpDeskTicket:
        """Transform from Ticket to HelpDeskTicket instance

        :param ticket: Ticket instance with ticket to transfrom.

        :returns: The transformed HelpDeskTicket instance.
        """
        field_mapping = {
            "id": lambda ticket: getattr(ticket, "id"),
            "status": lambda ticket: getattr(ticket, "status", None),
            "recipient_email": lambda ticket: getattr(ticket, "recipient", None),
            "topic": lambda ticket: getattr(ticket, "subject"),
            "body": lambda ticket: getattr(ticket, "description"),
            "user": lambda ticket: HelpDeskUser(
                id=ticket.requester.id,
                full_name=ticket.requester.name,
                email=ticket.requester.email,
            )
            if getattr(ticket, "requester", None)
            else None,
            "created_at": lambda ticket: getattr(ticket, "created_at", None),
            "updated_at": lambda ticket: getattr(ticket, "updated_at", None),
            "priority": lambda ticket: getattr(ticket, "priority", None),
            "due_at": lambda ticket: getattr(ticket, "due_at", None),
            "assingee_id": lambda ticket: getattr(ticket, "assingee_id", None),
            "group_id": lambda ticket: getattr(ticket, "group_id", None),
            "external_id": lambda ticket: getattr(  # /PS-IGNORE
                ticket, "external_id", None  # /PS-IGNORE
            ),
            "tags": lambda ticket: getattr(ticket, "tags", None),
            "custom_fields": lambda ticket: [
                HelpDeskCustomField(id=custom_field.id, value=custom_field.value)
                for custom_field in getattr(ticket, "custom_fields")
            ]
            if getattr(ticket, "custom_fields", None)
            else None,
            "comment": lambda ticket: HelpDeskComment(
                body=ticket.comment.body,
                author_id=ticket.comment.author_id,
                public=ticket.comment.public,
            )
            if getattr(ticket, "comment", None)
            else None,
        }

        if not ticket:
            return None

        return HelpDeskTicket(
            **dict(
                [
                    (field, value)
                    for field, transformation in field_mapping.items()
                    if (value := transformation(ticket))
                    if value
                    is not None  # filters out fields which were not in the ticket
                ]
            )
        )

    def __transform_helpdesk_to_zendesk_user(self, user: HelpDeskUser) -> ZendeskUser:
        # if no user details use cached user
        if user and user.id:
            return ZendeskUser(id=user.id)
        if user and (user.email and user.full_name):
            return ZendeskUser(name=user.full_name, email=user.full_name)
        elif not user or not user.id or not (user.email and user.full_name):
            return self.client.users.me()
        else:
            # This should not be possible so raise exception
            raise HelpDeskError(
                "Cannot transform user to Zendesk user",
            )

    def __transform_zendesk_to_helpdesk_user(self, user: ZendeskUser) -> HelpDeskUser:
        return HelpDeskUser(id=user.id, full_name=user.name, email=user.email)

    @staticmethod
    def oauth(subdomain: str, redirect_uri, credentials, code=None) -> json:
        """Complete the Zendesk OAuth process recovering the access_token needed to
        perform API requests to the Zendesk Support API.

        :param subdomain: Zendesk Subdomain

        :param redirect_uri: Uri to redirect after oauth.

        :param credentials required for oauth { client_id & client_secret }.

        :returns: data in json format
        """

        if not code:
            logger.error("The code parameter was missing in the request!")
            return '{ "error": "The code parameter was missing in the request!"}'

        request_url = f"https://{subdomain}.zendesk.com/oauth/tokens"
        logger.debug(
            f"Received Zendesk OAuth request code:<{code}>. "  # debug line /PS-IGNORE
            f"Recovering access token from {request_url}. "  # debug line /PS-IGNORE
            f"Redirect URL is {redirect_uri}. "  # debug line /PS-IGNORE
        )

        data = {
            "code": code,
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        response = requests.post(
            request_url,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        logger.debug(f"Result status from Zendesk:<{response.status_code}>")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Result status from Zendesk:\n{pprint.pformat(data)}>")
        return data
