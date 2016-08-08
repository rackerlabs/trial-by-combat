from TBC.interfaces.sql_interfaces.MySQLInterface import MySQLInterface
from TBC.interfaces.kvs_interfaces.RedisInterface import RedisInterface
from TBC.utility.yaml_loader import *

_interfaces = {
    'MySQL': MySQLInterface,
    'redis': RedisInterface
}

def load_interface(interface_name, data):
    """
    Load an interface
    :param interface_name: a string representing the name of the interface
    :param data: a dictionary of arguments to be used for initializing the interface
    :return: an Interface object of the appropriate type
    """
    if interface_name not in _interfaces:
        raise Exception('Unknown interface')

    return load_class_from_data(_interfaces[interface_name], data)