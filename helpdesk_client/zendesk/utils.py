from helpdesk_client.interfaces import HelpDeskTicket
from zenpy.lib.api_objects import Comment, Ticket

def transform_to_zen_api_ticket(ticket: HelpDeskTicket) -> Ticket:
    """Transform from HelpDeskTicket to Ticket instance

    :param ticket: HelpDeskTicket with ticket to transfrom.

    :returns: The transformed Ticket instance.
    """
    field_mapping = {
            'id':
                lambda ticket :
                ('id',ticket.id),
            'status':
                lambda ticket :
                ('status',ticket.status),
            'recipient':
                lambda ticket :
                ('recipient',ticket.recipient_email),
            'subject':
                lambda ticket :
                ('subject',ticket.topic),
            'description':
                lambda ticket :
                ('description',ticket.body) ,
            'submitter_id':
                lambda ticket :
                ('submitter_id',ticket.user_id),
            'requester_id':
                lambda ticket :
                ('requester_id',ticket.user_id),
            'assingee_id':
                lambda ticket :
                ('assingee_id',ticket.user_id) ,
            'group_id':
                lambda ticket :
                ('group_id',ticket.other.get('group_id',None)) if
                 ticket.other and isinstance(ticket.other, dict) else None,
            'external_id':
                lambda ticket :
                ('external_id',ticket.other.get('external_id')) if
                ticket.other and ticket.other.get('external_id') else None,
            'tags':
                lambda ticket :
                ('tags',ticket.other.get('tags'))if
                ticket.other and ticket.other.get('tags') else None,
            'custom_fields':
                lambda ticket :
                ('custom_fields',ticket.other.get('custom_fields') ) if
                ticket.other and ticket.other.get('custom_fields') else None,
            'comment':  
                lambda ticket :
                ('comment',
                    Comment(
                        body=ticket.other['comment'][0],
                        author_id=ticket.other['comment'][1]
                    )
                ) if
                ticket.other and ticket.other.get('comment') else None
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


def transform_from_zen_api_ticket(ticket: Ticket) -> HelpDeskTicket:
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
                'user_id':
                    lambda ticket :
                        ('user_id',getattr(ticket,'requester_id')) if
                        getattr(ticket,'requester_id',None) else None,
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
                'other':{
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
                            ('tags',getattr(ticket,'tags' )) if 
                            getattr(ticket,'tags',None) else None,
                    'custom_fields':
                        lambda ticket :
                            ('custom_fields',getattr(ticket,'custom_fields' )) if
                            getattr(ticket,'custom_fields',None) else None,
                    'comment':
                        lambda ticket :
                            ('comment',
                                (ticket.comment.body, ticket.comment.author_id)
                                    if getattr(ticket,'comment' ) else None) if
                                    getattr(ticket,'comment',None) else None
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
