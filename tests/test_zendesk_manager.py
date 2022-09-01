import datetime
import unittest
from unittest import mock

import pytest
from helpdesk_client.interfaces import HelpDeskTicket, HelpDeskComment, HelpDeskCustomField, HelpDeskUser
from helpdesk_client.zendesk_manager import ZenDeskManager
from zenpy.lib import exception
from zenpy.lib.api_objects import Ticket
from zenpy.lib.api_objects import User as ZendeskUser


class FakeUserResponse(object):
    def __init__(self, user_id):
        self.id = user_id

class FakeTicket(object):
    def __init__(self, ticket_id):
        self.id = ticket_id
        self.status = 'open'
        self.description = 'fakedescription'
        self.subject = 'fakesubject'
        self.requester_id = 1234

class FakeTicketAudit(object):
    def __init__(self, ticket):
        self.ticket = ticket

class FakeApi(object):
    """Aid testing tickets without using Zendesk API directly.
    """
    class FakeUsers(object):
        def __init__(self, me=None, users=[]):
            self._me = me
            self._users: dict[int,ZendeskUser] = dict([(user.id,user) for user in users])
            self._next_userid = 1


        def create_or_update(self,zendesk_user:ZendeskUser)->ZendeskUser:
            if zendesk_user.id:
                userid = zendesk_user.id
            else:
                zendesk_user.id = userid = self._next_userid
                self._next_userid +=1
            self._users[userid] = zendesk_user
            return zendesk_user

        def me(self):
            return self._me

    class FakeTicketCRUD(object):
        def __init__(self, parent, ticket_audit=None):
            self.ticket_audit = ticket_audit
            self._next_ticket_id = 1
            self.parent = parent

        def update(self, ticket):
            """No actual update performed
            """
            tickettoupdate = self.parent._tickets.get(ticket.id,None)
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
            self.parent._tickets[ticket.id]=ticket
            self._next_ticket_id += 1
            return FakeTicketAudit(ticket)

        def __call__(self, id:int) -> Ticket:
            """Recover a specific ticket.
            """
            ticket = self.parent._tickets.get(id,None)
            if ticket:
                return ticket
            else:
                raise exception.RecordNotFoundException

    def __init__(self, tickets=[], me=None, ticket_audit=None):
        self.results = tickets
        self.users = self.FakeUsers(me)
        self._tickets: dict[int, FakeTicket] = dict([(ticket.id,ticket) for ticket in tickets])
        self.tickets = self.FakeTicketCRUD(self, ticket_audit)

        for ticket in tickets:
            self._tickets[ticket.id]=ticket

    def search(self, chat_id, type):
        return self.results

class TestZenDesk(unittest.TestCase):

    def test_zendesk_create_user_and_ticket(self):
        zendeskmanager = ZenDeskManager(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )
        zendeskmanager.client = FakeApi()
        user = HelpDeskUser(full_name='Jim Example', email='test@example.com' ) #test email /PS-IGNORE
        heldeskuser= zendeskmanager.get_or_create_user(user=user)

        assert heldeskuser.id == 1

    # create user & ticket fullname & email errors
    def test_zendesk_create_ticket(self):
        zendeskmanager = ZenDeskManager(
            credentials= {
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain':'subdomain123'
                }
        )

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email='test@example.com', #test email /PS-IGNORE,
            topic='subject123',
            body='Field: value',
            user=user,
            custom_fields=[HelpDeskCustomField(
                id= 123, value='some-service-name'
            )]
        )

        zendeskmanager.client = FakeApi()

        actualticket = zendeskmanager.create_ticket(ticket=ticket)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.custom_fields == [HelpDeskCustomField(
                id= 123, value='some-service-name'
            )]

    def test_zendesk_create_ticket_from_slack(self):
        email =  'test@example.com' #test email /PS-IGNORE

        zendeskmanager = ZenDeskManager(
            client=FakeApi()
        )

        user = HelpDeskUser(id=1234)

        comment = HelpDeskComment(
            body='This is the message on slack message from slack.',
        )

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic='subject123',
            body='subject123',
            user=user,
            external_id= 5678,
            group_id= 7890,
            comment=comment
        )

        actualticket = zendeskmanager.create_ticket(ticket=ticket)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.comment.body == comment.body

    # def test_zendesk_create_ticket_with_custom_fields(self):

    # def test_zendesk_create_ticket_with_all_fields(self):

    def test_zendesk_get_ticket(self,):
        zendeskmanager = ZenDeskManager(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            topic="facesubject",
            body="fakedescription",
            user=user,
            id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskmanager.get_ticket(ticket_id=12345)
        assert actualticket.id ==  ticket.id

    def test_error_zendesk_does_not_get_ticket(self,):

        zendeskmanager = ZenDeskManager(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskmanager.get_ticket(ticket_id=54321)

        assert actualticket is None

    def test_zendesk_add_comment(self):
        email = 'test@example.com',  #test email /PS-IGNORE
        user = HelpDeskUser(id=1234)

        comment = HelpDeskComment(
            body='adding this comment',
            author_id=user.id
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager = ZenDeskManager(
            client=FakeApi(tickets=[fake_ticket], me=FakeUserResponse(user.id), ticket_audit=fake_ticket_audit)
        )

        ticket = HelpDeskTicket(
            id=12345,
            recipient_email=email,
            topic='subject123',
            body='subject123',
            user=user,
            external_id= 5678,
            group_id=7890
        )

        actualticket = zendeskmanager.add_comment(ticket_id=ticket.id,comment=comment)

        assert actualticket.id == ticket.id
        assert actualticket.topic == ticket.topic
        assert actualticket.comment.body == comment.body

    def test_zendesk_update_ticekt(self):
        email = 'test@example.com', #test email /PS-IGNORE

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic='subject123',
            body='Field: updated',
            user=user,
            id=12345
        )
        zendeskmanager = ZenDeskManager(
            credentials= {
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain':'subdomain123'
                },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        updatedticket = zendeskmanager.update_ticket(ticket=ticket)

        assert updatedticket.id ==  ticket.id
        assert updatedticket.body == 'Field: updated'

    def test_error_zendesk_update_ticekt_not_found(self):

        email = 'test@example.com' #test email /PS-IGNORE

        user = HelpDeskUser(id=1234)

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic='subject123',
            body='Field: updated',
            user=user,
            id=54321
        )
        zendeskmanager = ZenDeskManager(
            credentials= {
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        updatedticket = zendeskmanager.update_ticket(ticket=ticket)
        assert updatedticket is None

    def test_zendesk_close_ticket(self):
        zendeskmanager = ZenDeskManager(
            credentials= {
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )
        user = HelpDeskUser(id=1234)
        ticket = HelpDeskTicket(
            topic="fakesubject",
            body="fakedescription",
            user=user,
            id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskmanager.close_ticket(ticket_id=12345)

        assert actualticket.id ==  ticket.id
        assert actualticket.status == 'closed'

    def test_error_zendesk_close_ticket_not_found(self):
        zendeskmanager = ZenDeskManager(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'subdomain': 'subdomain123'
                },
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskmanager.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskmanager.close_ticket(ticket_id=54321)
        assert actualticket is None

    @mock.patch('helpdesk_client.zendesk_manager.requests.post')
    def test_zendesk_oauth_successful_token_exchange(self,requests_post):

        def loads():
            return {
                'access_token': 'my-zd-access-token',
                'token_type': 'bearer',
                'scope': 'impersonate tickets:read tickets:write',
            }

        # mock the OK response from Zendesk
        requests_post.return_value.json = loads

        response = ZenDeskManager.oauth(
            subdomain='subdomain123',
            redirect_uri='https://my.app/oauth',
            credentials={ 'client_id':'testid', 'client_secret':'testsecret'},
            code=1234
            )

        assert response['access_token'] == 'my-zd-access-token'
        assert response['token_type'] == 'bearer'
        assert response['scope'] == 'impersonate tickets:read tickets:write'
