import datetime
import unittest

from zenpy.lib import exception
from zenpy.lib.api_objects import Ticket
from zenpy.lib.api_objects import User as ZendeskUser

from helpdesk_client.interfaces import (
    HelpDeskComment,
    HelpDeskCustomField,
    HelpDeskTicket,
    HelpDeskTicketNotFoundException,
    HelpDeskUser,
    Priority,
    Status,
    TicketType,
)
from helpdesk_client.zendesk_manager import ZendeskManager


class FakeUser(object):
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get("id")
        self.name = kwargs.get("name")
        self.email = kwargs.get("email")


class FakeUserResponse(object):
    def __init__(self, user_id):
        self.id = user_id


class FakeTicket(object):
    def __init__(self, ticket_id, requester=None):
        self.id = ticket_id
        self.status = "open"
        self.description = "fakedescription"
        self.subject = "fakesubject"
        self.requester_id = 1234
        self.requester = requester


class FakeTicketAudit(object):
    def __init__(self, ticket):
        self.ticket = ticket


class FakeApi(object):
    """Aid testing tickets without using Zendesk API directly."""

    class FakeUsers(object):
        def __init__(self, parent, me=None):
            self._me = me
            self._next_userid = 1
            self.parent = parent

        def create_or_update(self, zendesk_user: ZendeskUser) -> ZendeskUser:
            if zendesk_user.id:
                userid = zendesk_user.id
            else:
                zendesk_user.id = userid = self._next_userid
                self._next_userid += 1
            self.parent._users[userid] = zendesk_user
            return zendesk_user

        def me(self):
            return self._me

        def __call__(self, id: int) -> ZendeskUser:
            """Recover a specific user."""
            user = self.parent._users.get(id, None)
            if user:
                return user
            else:
                return None

    class FakeTicketCRUD(object):
        def __init__(self, parent, ticket_audit=None):
            self.ticket_audit = ticket_audit
            self._next_ticket_id = 1
            self.parent = parent

        def update(self, ticket):
            """No actual update performed"""
            tickettoupdate = self.parent._tickets.get(ticket.id, None)
            if tickettoupdate:
                self.parent._tickets[ticket.id] = ticket
                return FakeTicketAudit(ticket)
            else:
                return None

        def create(self, ticket):
            """Pretend to create a zendesk ticket and return the canned
            result.
            """
            ticket.id = self._next_ticket_id
            ticket.created_at = datetime.datetime.now()
            self.parent._tickets[ticket.id] = ticket
            self._next_ticket_id += 1
            return FakeTicketAudit(ticket)

        def __call__(self, id: int) -> Ticket:
            """Recover a specific ticket."""
            ticket = self.parent._tickets.get(id, None)
            if ticket:
                return ticket
            else:
                raise exception.RecordNotFoundException

    def __init__(self, tickets=[], me=None, ticket_audit=None, users=[]):
        self.results = tickets
        self._users: dict[int, FakeUser] = dict([(user.id, user) for user in users])
        self.users = self.FakeUsers(self, me=me)
        self._tickets: dict[int, FakeTicket] = dict(
            [(ticket.id, ticket) for ticket in tickets]
        )
        self.tickets = self.FakeTicketCRUD(self, ticket_audit)

        for ticket in tickets:
            self._tickets[ticket.id] = ticket

    def search(self, chat_id, type):
        return self.results


class TestZenDesk(unittest.TestCase):
    def test_zendesk_create_user(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )
        zendeskmanager.client = FakeApi()
        user = HelpDeskUser(
            full_name="Jim Example", email="test@example.com"  # test email /PS-IGNORE
        )
        heldeskuser = zendeskmanager.get_or_create_user(user=user)

        assert heldeskuser.id == 1

    def test_zendesk_get_user(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )
        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        zendeskmanager.client = FakeApi(users=[fake_user])
        user = HelpDeskUser(id=1234)
        helpdeskuser = zendeskmanager.get_or_create_user(user=user)

        assert helpdeskuser.id == 1234
        assert helpdeskuser.full_name == "Jim Example"
        assert helpdeskuser.email == "test@example.com"  # test email /PS-IGNORE

    def test_zendesk_get_cached_user(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )
        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        zendeskmanager.client = FakeApi(users=[fake_user], me=FakeUserResponse(1234))
        helpdeskuser = zendeskmanager.get_or_create_user()

        assert helpdeskuser.id == 1234

    def test_error_zendesk_cannot_get_or_create_user(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )
        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        zendeskmanager.client = FakeApi(users=[fake_user])
        user = HelpDeskUser()
        helpdeskuser = zendeskmanager.get_or_create_user(user=user)

        assert helpdeskuser is None

    def test_zendesk_create_ticket(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            }
        )

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email="test@example.com",  # test email /PS-IGNORE,
            topic="subject123",
            body="Field: value",
            user=user,
            custom_fields=[HelpDeskCustomField(id=123, value="some-service-name")],
        )

        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        zendeskmanager.client = FakeApi(users=[fake_user])

        actualticket = zendeskmanager.create_ticket(ticket=ticket)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.custom_fields == [
            HelpDeskCustomField(id=123, value="some-service-name")
        ]

    def test_zendesk_create_ticket_with_all_details(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            }
        )

        user = HelpDeskUser(id=1234)

        comment = HelpDeskComment(
            body="This is the initial ticket comment.",
            public=False,
        )
        ticket = HelpDeskTicket(
            recipient_email="test@example.com",  # test email /PS-IGNORE,
            topic="subject123",
            body="Field: value",
            user=user,
            tags=["tag1", "tag2"],
            external_id=789,
            group_id=456,
            assingee_id=3456,
            comment=comment,
            priority=Priority.NORMAL,
            status=Status.OPEN,
            ticket_type=TicketType.TASK,
            custom_fields=[HelpDeskCustomField(id=123, value="some-service-name")],
        )

        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        zendeskmanager.client = FakeApi(users=[fake_user])

        actualticket = zendeskmanager.create_ticket(ticket=ticket)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.tags == ticket.tags
        assert actualticket.external_id == ticket.external_id
        assert actualticket.group_id == ticket.group_id
        assert actualticket.assingee_id == ticket.assingee_id
        assert actualticket.priority == ticket.priority
        assert actualticket.status == ticket.status
        assert actualticket.comment.author_id == 1234
        assert actualticket.comment.body == ticket.comment.body
        assert actualticket.comment.public == ticket.comment.public
        assert actualticket.custom_fields == [
            HelpDeskCustomField(id=123, value="some-service-name")
        ]

    def test_zendesk_get_ticket(
        self,
    ):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            topic="facesubject", body="fakedescription", user=user, id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit
        )

        actualticket = zendeskmanager.get_ticket(ticket_id=12345)
        assert actualticket.id == ticket.id

    def test_error_zendesk_does_not_get_ticket(
        self,
    ):

        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit
        )

        with self.assertRaises(HelpDeskTicketNotFoundException):
            zendeskmanager.get_ticket(ticket_id=54321)

    def test_zendesk_add_comment(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        user = HelpDeskUser(id=1234)
        comment = HelpDeskComment(body="adding this comment", author_id=user.id)

        fake_user = FakeUser(
            id=1234, name="fakename", email="fake@email.com"  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=12345, requester=fake_user)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket],
            me=FakeUserResponse(user.id),
            ticket_audit=fake_ticket_audit,
            users=[fake_user],
        )

        actualticket = zendeskmanager.add_comment(ticket_id=12345, comment=comment)

        assert actualticket.id == 12345
        assert actualticket.topic == "fakesubject"
        assert actualticket.comment.body == comment.body

    def test_zendesk_add_comment_no_author_id(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )
        comment = HelpDeskComment(body="adding this comment", public=False)

        fake_user = FakeUser(
            id=1234, name="fakename", email="fake@email.com"  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=12345, requester=fake_user)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket],
            me=FakeUserResponse(1234),
            ticket_audit=fake_ticket_audit,
            users=[fake_user],
        )

        actualticket = zendeskmanager.add_comment(ticket_id=12345, comment=comment)

        assert actualticket.id == 12345
        assert actualticket.topic == "fakesubject"
        assert actualticket.comment.body == comment.body
        assert actualticket.comment.public == comment.public
        assert actualticket.comment.author_id == 1234

    def test_error_zendesk_add_comment_not_found(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        user = HelpDeskUser(id=1234)
        comment = HelpDeskComment(body="adding this comment", author_id=user.id)

        fake_user = FakeUser(
            id=1234, name="fakename", email="fake@email.com"  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=98765, requester=fake_user)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)

        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket],
            me=FakeUserResponse(user.id),
            ticket_audit=fake_ticket_audit,
            users=[fake_user],
        )

        with self.assertRaises(HelpDeskTicketNotFoundException):
            zendeskmanager.add_comment(ticket_id=12345, comment=comment)

    def test_zendesk_update_ticekt(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email="test@example.com",  # test email /PS-IGNORE,
            topic="subject123",
            body="Field: updated",
            user=user,
            id=12345,
        )

        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit, users=[fake_user]
        )

        updatedticket = zendeskmanager.update_ticket(ticket=ticket)

        assert updatedticket.id == ticket.id
        assert updatedticket.body == "Field: updated"

    def test_error_zendesk_update_ticekt_not_found(self):

        email = "test@example.com"  # test email /PS-IGNORE

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic="subject123",
            body="Field: updated",
            user=user,
            id=54321,
        )
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        fake_user = FakeUser(
            id=1234,
            name="Jim Example",
            email="test@example.com",  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit, users=[fake_user]
        )

        with self.assertRaises(HelpDeskTicketNotFoundException):
            zendeskmanager.update_ticket(ticket=ticket)

    def test_zendesk_close_ticket(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        fake_user = FakeUser(
            id=123, name="fakename", email="fake@email.com"  # test email /PS-IGNORE
        )
        fake_ticket = FakeTicket(ticket_id=12345, requester=fake_user)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)

        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit, users=[fake_user]
        )

        actualticket = zendeskmanager.close_ticket(ticket_id=12345)

        assert actualticket.id == 12345
        assert actualticket.status == "closed"

    def test_error_zendesk_close_ticket_not_found(self):
        zendeskmanager = ZendeskManager(
            credentials={
                "email": "test@example.com",  # test email /PS-IGNORE
                "token": "token123",
                "subdomain": "subdomain123",
            },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(
            tickets=[fake_ticket], ticket_audit=fake_ticket_audit
        )

        with self.assertRaises(HelpDeskTicketNotFoundException):
            zendeskmanager.close_ticket(ticket_id=54321)
