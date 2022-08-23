import datetime
import unittest
from unittest import mock
import pytest

from zenpy.lib.api_objects import Ticket
from zenpy.lib import exception
from zenpy.lib.api_objects import User as ZendeskUser

from helpdesk_client.interfaces import HelpDeskTicket
from helpdesk_client.zendesk_client import ZenDeskClient


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
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'custom_field_id':123
                },
            subdomain='subdomain123'
        )
        zendeskclient.client = FakeApi()

        zendeskuserid = zendeskclient.get_or_create_user(
                full_name='Jim Example', email_address='test@example.com' #test email /PS-IGNORE
            )
        
        assert zendeskuserid == 1
    # create user & ticket fullname & email errors

    def test_zendesk_create_ticket(self):
        (
            subject,
            custom_fields,
            description,
            tags,
            email,
        ) = [
                'subject123',
                [{'id': 123, 'value': 'some-service-name'}],
                'Field: value',
                None,
                'test@example.com', #test email /PS-IGNORE
            ]
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123'
                },
            subdomain='subdomain123'
        )

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic=subject,
            body=description,
            user_id=1234,
            other={
                'custom_fields':custom_fields,
                'tags': tags
                },
        )

        zendeskclient.client = FakeApi()

        actualticket = zendeskclient.create_ticket(ticket=ticket)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.other.get('custom_fields') == custom_fields

    def test_zendesk_create_ticket_from_slack(self):
        (
            subject,
            email,
            comment
        ) = [
                'subject123',
                'test@example.com', #test email /PS-IGNORE
                'This is the message on slack message from slack.'
            ]
        zendeskclient = ZenDeskClient(
            client=FakeApi()
        )

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic=subject,
            body=subject,
            user_id=1234,
            
            other={
                    'external_id': 5678,
                    'group_id':7890
                },
        )

        actualticket = zendeskclient.create_ticket(ticket=ticket,comment=comment)
        assert actualticket.id == 1
        assert actualticket.topic == ticket.topic
        assert actualticket.other['comment']['body'] == comment

    # def test_zendesk_create_ticket_with_custom_fields(self):
    # create ticekt with (payload.get('_custom_fields') or []) best way?

    # def test_zendesk_create_ticket_with_all_fields(self):

    def test_zendesk_get_ticket(self,):
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                },
            subdomain='subdomain123'
        )
        ticket = HelpDeskTicket(
            topic="facesubject",
            body="fakedescription",
            user_id=1234,
            id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskclient.get_ticket(ticket_id=12345)
        assert actualticket.id ==  ticket.id

    def test_error_zendesk_does_not_get_ticket(self,):

        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                'custom_field_id':123
                },
            subdomain='subdomain123'
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskclient.get_ticket(ticket_id=54321)

        assert actualticket is None

    def test_zendesk_add_comment(self):
        (
            subject,
            email,
            comment,
            user_id
        ) = (
                'subject123',
                'test@example.com',  #test email /PS-IGNORE
                'adding this comment',
                1234
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient = ZenDeskClient(
            client=FakeApi(tickets=[fake_ticket], me=FakeUserResponse(user_id), ticket_audit=fake_ticket_audit)
        )

        ticket = HelpDeskTicket(
            id=12345, 
            recipient_email=email,
            topic=subject,
            body=subject,
            user_id=user_id,
            other={
                    'external_id': 5678,
                    'group_id':7890,
                },
        )

        actualticket = zendeskclient.add_comment(ticket=ticket,comment=comment)
        print(actualticket)
        assert actualticket.id == ticket.id
        assert actualticket.topic == ticket.topic
        assert actualticket.other['comment']['body'] == comment

    def test_zendesk_update_ticekt(self):
        (
            subject,
            description,
            tags,
            email,
        ) = (
                'subject123',
                'Field: value',
                None,
                'test@example.com', #test email /PS-IGNORE
        )

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic=subject,
            body=description,
            user_id=1234,
            other={
                'tags': tags
                },
        )
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                },
            subdomain='subdomain123'
        )
        ticket = HelpDeskTicket(
            topic="fakesubject",
            body="updated",
            user_id=1234,
            id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)
        
        updatedticket = zendeskclient.update_ticket(ticket=ticket)

        assert updatedticket.id ==  ticket.id
        assert updatedticket.body == 'updated'

    def test_error_zendesk_update_ticekt_not_found(self):
        (
            subject,
            description,
            tags,
            email,
        ) = (
                'subject123',
                'Field: value',
                None,
                'test@example.com', #test email /PS-IGNORE
        )

        ticket = HelpDeskTicket(
            recipient_email=email,
            topic=subject,
            body=description,
            user_id=1234,
            other={
                'tags': tags
                },
        )
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                },
            subdomain='subdomain123'
        )
        ticket = HelpDeskTicket(
            topic="fakesubject",
            body="updated",
            user_id=1234,
            id=54321
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)
        
        updatedticket = zendeskclient.update_ticket(ticket=ticket)
        assert updatedticket is None

    def test_zendesk_close_ticket(self):
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                },
            subdomain='subdomain123'
        )
        ticket = HelpDeskTicket(
            topic="fakesubject",
            body="fakedescription",
            user_id=1234,
            id=12345
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskclient.close_ticket(ticket_id=12345)

        assert actualticket.id ==  ticket.id
        assert actualticket.status == 'closed'
        
    def test_error_zendesk_close_ticket_not_found(self):
        zendeskclient = ZenDeskClient(
            credentials= { 
                'email':'test@example.com', #test email /PS-IGNORE
                'token':'token123',
                },
            subdomain='subdomain123'
        )

        fake_ticket = FakeTicket(ticket_id=12345)
        fake_ticket_audit = FakeTicketAudit(fake_ticket)
        zendeskclient.client = FakeApi(tickets=[fake_ticket], ticket_audit=fake_ticket_audit)

        actualticket = zendeskclient.close_ticket(ticket_id=54321)
        assert actualticket is None

    @mock.patch('helpdesk_client.zendesk_client.requests.post')
    def test_zendesk_oauth_successful_token_exchange(self,requests_post):

        def loads():
            return {
                'access_token': 'my-zd-access-token',
                'token_type': 'bearer',
                'scope': 'impersonate tickets:read tickets:write',
            }

        # mock the OK response from Zendesk 
        requests_post.return_value.json = loads
        
        response = ZenDeskClient.oauth(
            subdomain='subdomain123',
            redirect_uri='https://my.app/oauth',
            credentials={ 'client_id':'testid', 'client_secret':'testsecret'},
            code=1234
            )

        assert response['access_token'] == 'my-zd-access-token'
        assert response['token_type'] == 'bearer'
        assert response['scope'] == 'impersonate tickets:read tickets:write'
