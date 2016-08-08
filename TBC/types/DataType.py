class DataType(object):
    def __init__(self):
        self.type = 'generic'
        self.description = ''

    def compare_data_objects(self, other):
        """
        Used to compare two data types
        """
        return self.type == other.type

    def __eq__(self, other):
        if type(other) is str:
            return self.type == other
        else:
            if type(self) is not type(other):
                return False
            else:
                return self.compare_data_objects(other)

    def __str__(self):
        return '<data type: ' + self.type + self.description + '>'


class IntDataType(DataType):
    def __init__(self, auto_increment=False):
        super(IntDataType, self).__init__()
        self.type = 'int'
        self.auto_increment=auto_increment


class FloatDataType(DataType):
    def __init__(self):
        super(FloatDataType, self).__init__()
        self.type = 'float'


class StringDataType(DataType):
    def __init__(self, fixed_length=True, length=255):
        """
        :param fixed_length: should the string be of fixed lenght or variable length?
        :param length: the maximum length if not fixed, otherwise the exact length if it is fixed
        """
        super(StringDataType, self).__init__()
        self.type = 'string'
        self.fixed_length = fixed_length
        self.length = length
        self.description = ', fixed=' + str(fixed_length) + ', length=' + str(length)

    def compare_data_objects(self, other):
        return self.fixed_length == other.fixed_length and self.length == other.length


class BoolDataType(DataType):
    def __init__(self):
        super(BoolDataType, self).__init__()
        self.type = 'bool'
