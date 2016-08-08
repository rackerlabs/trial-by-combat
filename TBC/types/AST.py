"""
Abstract Syntax Tree
"""

class UnaryOperation(object):
    """
    Represents an operation such as (not A)
    """
    def __init__(self, value, operator):
        """
        :param value: the value on which the operator is acting
        :param operator: a string from the set ('not', 'sum', 'count')
        """
        self.value = value
        self.operator = operator

    def __str__(self):
        return '(' + self.operator + str(self.value) + ')'

class BinaryOperation(object):
    """
    Represents an operation such as (A + B) or (5 - 4.5) or (X and Y)
    """
    def __init__(self, left_value, right_value, operator):
        """
        :param left_value: the expression on the left side of the operator
        :param right_value: the expression on the right side of the operator
        :param operator: a string from the set ('+', '-', '*', '/', '==', '=', '!=', '>', '<', '>=', '<=', 'and', 'or')

        Note: '==' is the equality operator, '=' is the assignment operator

        """
        self.left_value = left_value
        self.right_value = right_value
        self.operator = operator

    def __str__(self):
        return '(' + str(self.left_value) + ' ' + str(self.operator) + ' ' + str(self.right_value) + ')'
