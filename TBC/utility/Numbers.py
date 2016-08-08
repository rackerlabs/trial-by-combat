import math


def significant_figures(x, n):
    """
    Returns x rounded to n significant figures.

    Borrowed in part from https://mail.python.org/pipermail/tutor/2009-September/071393.html
    """
    if x == 0.0:
        return 0.0
    else:
        return round(x, int(n - math.ceil(math.log10(abs(x)))))


class Infinity(object):
    """
    This object can be used in integer and floating point operations
    """

    def __init__(self, positive=True):
        self.positive = positive

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True

    def __gt__(self, other):
        return self.positive

    def __ge__(self, other):
        return self.positive

    def __lt__(self, other):
        return not self.positive

    def __le__(self, other):
        return not self.positive

    def __neg__(self):
        self.positive = not self.positive

    def __add__(self, other):
        result = Infinity()
        result.positive = self.positive
        return result

    def __radd__(self, other):
        result = Infinity()
        result.positive = not self.positive
        return result

    def __sub__(self, other):
        result = Infinity()
        result.positive = self.positive
        return result

    def __rsub__(self, other):
        result = Infinity()
        result.positive = not self.positive
        return result

    def __mul__(self, other):
        if other > 0:
            if self.positive:
                return Infinity()
            else:
                return Infinity(False)
        elif other < 0:
            if self.positive:
                return Infinity(False)
            else:
                return Infinity()
        else:
            raise Exception('INFINITY * 0 is undefined')

    def __rmul__(self, other):
        return self.__mul__(other)

    def __div__(self, other):
        if other > 0:
            if self.positive:
                return Infinity()
            else:
                return Infinity(False)
        elif other < 0:
            if self.positive:
                return Infinity(False)
            else:
                return Infinity()
        elif type(other) is Infinity:
            raise Exception('INFINITY / INFINITY is undefined')
        else:
            return Infinity()

    def __rdiv__(self, other):
        if type(other) is Infinity:
            raise Exception('INFINITY / INFINITY is undefined')
        else:
            return 0

    def __str__(self):
        if self.positive:
            return 'INFINITY'
        else:
            return '-INFINITY'


class ApproximateFloat(object):
    """
    This object allows floating point comparison to be 'fuzzed'.  For example, using ApproximateFloats
    5.00000000000001 == 5.0
    """

    def __init__(self, value, threshold=0.0000001):
        self.value = value
        self.threshold = threshold

    def __eq__(self, other):
        if type(other) is ApproximateFloat:
            return abs(self.value - other.value) < self.threshold
        else:
            return abs(self.value - other) < self.threshold

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if type(other) is ApproximateFloat:
            return self.value - other.value > self.threshold
        else:
            return self.value - other > self.threshold

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __lt__(self, other):
        if type(other) is ApproximateFloat:
            return other.value - self.value > self.threshold
        else:
            return other - self.value > self.threshold

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __neg__(self):
        self.value = -1 * self.value

    def __add__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(self.value + other.value, threshold=self.threshold)
        else:
            return ApproximateFloat(self.value + other, threshold=self.threshold)

    def __radd__(self, other):
        self.__add__(other)

    def __sub__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(self.value - other.value, threshold=self.threshold)
        else:
            return ApproximateFloat(self.value - other, threshold=self.threshold)

    def __rsub__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(other.value - self.value, threshold=self.threshold)
        else:
            return ApproximateFloat(other - self.value, threshold=self.threshold)

    def __mul__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(other.value * self.value, threshold=self.threshold)
        else:
            return ApproximateFloat(other * self.value, threshold=self.threshold)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __div__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(other.value / self.value, threshold=self.threshold)
        else:
            return ApproximateFloat(other / self.value, threshold=self.threshold)

    def __rdiv__(self, other):
        if type(other) is ApproximateFloat:
            return ApproximateFloat(self.value / other.value, threshold=self.threshold)
        else:
            return ApproximateFloat(self.value / other, threshold=self.threshold)

    def __str__(self):
        return str(self.value)
