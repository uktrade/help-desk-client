from importlib import import_module

from helpdesk_client.interfaces import HelpDeskBase


def get_helpdesk_interface(class_path) -> HelpDeskBase:
    """Give access to an instantiated helpdesk class

    :param class_path: The Python import path to the helpdesk class
    """
    parts = class_path.split(".")
    module_string = ".".join(parts[:-1])
    cls_string = parts[-1]

    module = import_module(module_string)
    cls = getattr(module, cls_string)

    return cls
