from django.conf import settings
from django.utils.module_loading import import_string

from helpdesk_client.interfaces import HelpDeskBase, HelpDeskStubbed


def get_helpdesk_interface() -> HelpDeskBase:
    """
    Get the People Finder interface from the PEOPLE_FINDER_INTERFACE setting
    """
    if not getattr(settings, "HELPDESK_INTERFACE", None):
        return HelpDeskStubbed()

    interface_class = import_string(settings.HELPDESK_INTERFACE)
    if not issubclass(interface_class, HelpDeskBase):
        raise ValueError("HELPDESK_INTERFACE must inherit from HelpDeskBase")

    return interface_class()
