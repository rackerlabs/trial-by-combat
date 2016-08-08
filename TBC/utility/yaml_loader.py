import yaml
import inspect

def run_function_from_yaml(function, yaml_file):
    """
    Extract the arguments for a function from a yaml file and use it run a function
    :param function: the function to be run
    :param yaml_file: a yaml file with keys corresponding to function arguments
    :return: the return value of the function
    """
    fObj = open(yaml_file, 'r')
    data = yaml.load(fObj)
    fObj.close()
    return run_function_from_data(function, data)


def run_function_from_data(function, data):
    """
    Extract the arguments for a function from a dictionary and use it run a function
    :param function: the function to run
    :param data: a dictionary with keys corresponding to function arguments
    :return: the return value of the function
    """
    all_args, _, _, defaults = inspect.getargspec(function)
    if defaults is None:
        defaults = []
    positional_args = len(all_args) - len(defaults)
    start_pos = 0
    if inspect.ismethod(function):
        start_pos = 1
    args_list = all_args[start_pos:positional_args]
    kwargs_list = all_args[positional_args:]

    args = []
    kwargs = {}
    for arg in args_list:
        args.append(data[arg])
    for kwarg in kwargs_list:
        if kwarg in data:
            kwargs[kwarg] = data[kwarg]

    return function(*args, **kwargs)

def load_class_from_yaml(class_type, yaml_file):
    """
    Similar to run_function_from_yaml except desgined to work with constructors
    :param class_type: the class to be initialized
    :param yaml_file: the yaml file with the arguments
    :return: a new instance of class_type
    """
    fObj = open(yaml_file, 'r')
    data = yaml.load(fObj)
    fObj.close()

    return load_class_from_data(class_type, data)


def load_class_from_data(class_type, data):
    """
    Similar to run_function_from_data except desgined to work with constructors
    :param class_type: the class to be initialized
    :param yaml_file: the dictionary with the arguments
    :return: a new instance of class_type
    :param class_type:
    :param data:
    :return:
    """
    all_args, _, _, defaults = inspect.getargspec(class_type.__init__)
    if defaults is None:
        defaults = []
    positional_args = len(all_args) - len(defaults)
    args_list = all_args[1:positional_args]
    kwargs_list = all_args[positional_args:]

    args = []
    kwargs = {}
    for arg in args_list:
        args.append(data[arg])
    for kwarg in kwargs_list:
        if kwarg in data:
            kwargs[kwarg] = data[kwarg]

    return class_type(*args, **kwargs)