import logging

from zenpy import Zenpy
from zenpy.lib import exception
from zenpy.lib.api_objects import Comment, CustomField, Ticket
from zenpy.lib.api_objects import User as ZendeskUser

from helpdesk_client.interfaces import (
    HelpDeskBase,
    HelpDeskComment,
    HelpDeskCustomField,
    HelpDeskException,
    HelpDeskTicket,
    HelpDeskTicketNotFoundException,
    HelpDeskUser,
)


logger = logging.getLogger(__name__)


class ZendeskClientNotFoundException(Exception):
    pass


class ZendeskManager(HelpDeskBase):
    def __init__(self, **kwargs):
        """Create a new Zendesk client - pass credentials in

        :param credentials: The credentials required to create client { token , email, subdomain }
        """
        if not kwargs.get("credentials", None):
            raise ZendeskClientNotFoundException("No Zendesk credentials provided")

        self.client = Zenpy(
            timeout=kwargs.get("credentials").get("timeout", 5),
            email=kwargs.get("credentials")["email"],
            token=kwargs.get("credentials")["token"],
            subdomain=kwargs.get("credentials")["subdomain"],
        )

    def get_or_create_user(self, user: HelpDeskUser = None) -> HelpDeskUser:
        """Get or Create a new Zendesk user   /PS-IGNORE

        :param HelpDeskUser
                full_name: string full name for Zendesk user
                email: string email address text for the Zendesk user

        :returns: HelpDeskUser representing Zendesk user
        """

        transformed_user = self.__transform_helpdesk_user_to_zendesk_user(user)

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
        return self.__transform_zendesk_user_to_helpdesk_user(zendesk_user)

    def create_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Create a new Zendesk ticket in response to a new user question.

        :param ticket: HelpDeskTicket with information to create Zendesk ticket

        :returns: A HelpDeskTicket instance
        """

        zendesk_audit = self.client.tickets.create(
            self.__transform_helpdesk_to_zendesk_ticket(ticket)
        )
        return self.__transform_zendesk_to_helpdesk_ticket(zendesk_audit.ticket)

    def get_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Recover the ticket by Zendesk ID

        :param ticket_id: The Zendesk ID of the Ticket

        :returns: A HelpDeskTicket instance

        :raises:
            HelpDeskTicketNotFoundException: If no ticket is found
        """
        logger.debug(f"Look for Ticket by is Zendesk ID:<{ticket_id}>")  # /PS-IGNORE
        try:
            return self.__transform_zendesk_to_helpdesk_ticket(
                self.client.tickets(id=ticket_id)
            )
        except exception.RecordNotFoundException:
            message = (
                f"Could not find Zendesk ticket with ID:<{ticket_id}>"  # /PS-IGNORE
            )

            logger.debug(message)
            raise HelpDeskTicketNotFoundException(message)

    def close_ticket(self, ticket_id: int) -> HelpDeskTicket:
        """Close a ticket in Zendesk

        :param ticket_id: The Zendesk ticket ID

        :returns: HelpDeskTicket instance
        """
        logger.debug(f"Looking for ticket with ticket_id:<{ticket_id}>")
        ticket = self.get_ticket(ticket_id)

        if ticket.status == "closed":
            logger.warning(f"The ticket:<{ticket.id}> has already been closed!")
        else:
            ticket.status = "closed"
            ticket = self.update_ticket(ticket)
            logger.debug(f"Closed ticket:<{ticket.id}> for ticket_id:<{ticket_id}>")

        return ticket

    def add_comment(self, ticket_id: int, comment: HelpDeskComment) -> HelpDeskTicket:
        """Add a comment to an existing ticket

        :param ticket_id: HelpDeskTicket instance id
        :param comment: Comment text

        :returns: The updated HelpDeskTicket instance
        """
        ticket = self.get_ticket(ticket_id)
        ticket.comment = comment
        return self.update_ticket(ticket)

    def update_ticket(self, ticket: HelpDeskTicket) -> HelpDeskTicket:
        """Update an existing ticket.

        :param ticket: HelpDeskTicket ticket.

        :returns: The updated HelpDeskTicket instance.
        """
        ticket_audit = self.client.tickets.update(
            self.__transform_helpdesk_to_zendesk_ticket(ticket)
        )
        if ticket_audit is None:
            message = f"Could not update ticket with id  {ticket.id}"
            logger.error(message)
            raise HelpDeskTicketNotFoundException(message)

        return self.__transform_zendesk_to_helpdesk_ticket(ticket_audit.ticket)

    def __transform_helpdesk_to_zendesk_ticket(self, ticket: HelpDeskTicket) -> Ticket:
        """Transform from HelpDeskTicket to Zendesk ticket instance

        :param ticket: HelpDeskTicket instance.
        :returns: Zendesk ticket instance.
        """

        custom_fields, comment = None, None

        if ticket.custom_fields:
            custom_fields = [
                CustomField(id=custom_field.id, value=custom_field.value)
                for custom_field in ticket.custom_fields
            ]

        if ticket.comment:
            comment = Comment(
                body=ticket.comment.body,
                author_id=ticket.comment.author_id
                if ticket.comment.author_id
                else ticket.user.id,
                public=ticket.comment.public,
            )

        ticket_user = self.get_or_create_user(ticket.user)

        ticket = Ticket(
            id=ticket.id,
            status=ticket.status,
            recipient=ticket.recipient_email,
            subject=ticket.topic,
            description=ticket.body,
            submitter_id=ticket.user.id,
            assingee_id=ticket.assingee_id,
            priority=ticket.priority,
            requester=ZendeskUser(
                id=getattr(ticket_user, "id", None),
                name=getattr(ticket_user, "full_name", None),
                email=getattr(ticket_user, "email", None),
            ),
            group_id=ticket.group_id,
            external_id=ticket.external_id,  # /PS-IGNORE
            tags=ticket.tags,
            custom_fields=custom_fields,
            comment=comment,
        )

        return ticket

    def __transform_zendesk_to_helpdesk_ticket(self, ticket: Ticket) -> HelpDeskTicket:
        """Transform Zendesk ticket into HelpDeskTicket instance

        :param ticket: Zendesk ticket instance

        :returns: HelpDeskTicket instance.
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

    def __transform_helpdesk_user_to_zendesk_user(
        self, user: HelpDeskUser
    ) -> ZendeskUser:
        """Transform HelpDesk user into Zendesk user

        :param user: HelpDeskUser instance.

        :returns: ZendeskUser instance.
        """
        if user and user.id:
            return ZendeskUser(id=user.id)
        if user and (user.email and user.full_name):
            return ZendeskUser(name=user.full_name, email=user.full_name)
        elif not user or not user.id or not (user.email and user.full_name):
            return self.client.users.me()
        else:
            # This should not be possible so raise exception
            raise HelpDeskException(
                "Cannot transform user to Zendesk user",
            )

    def __transform_zendesk_user_to_helpdesk_user(
        self, user: ZendeskUser
    ) -> HelpDeskUser:
        """Transform HelpDesk user into Zendesk user

        :param user: HelpDeskUser user instance.

        :returns: Zendesk user instance.
        """
        return HelpDeskUser(id=user.id, full_name=user.name, email=user.email)
