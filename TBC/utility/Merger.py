import copy


def merge_dicts(dict1, dict2, recycle=True):
    """
    Recursively merge two dictionaries.  dict2's values will override dict1's
    :param recycle: if True then write the merged dictionary into dict1, otherwise do not modify dict1
    :return: a single dictionary
    """

    assert type(dict1) is dict and type(dict2) is dict, \
        'Only dictionaries can be merged with this function, not %s and %s' % (str(type(dict1)), str(type(dict2)))

    if not recycle:
        # don't modify the original dictionary passed to us
        result = copy.deepcopy(dict1)
    else:
        result = dict1

    for key in dict2:
        value = dict2[key]
        if key not in result or type(value) is not dict or type(result[key]) is not dict:
            result[key] = value
        else:
            result[key] = merge_dicts(result[key], value, recycle=True)
    return result
