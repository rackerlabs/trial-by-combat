import random

from TBC.types.DataType import *
from TBC.types.Column import Column
from TBC.types.Table import Table

table1 = Table('RandomTransactions')
table1.add_column(Column('id', IntDataType()))
table1.add_column(Column('a', IntDataType()))
table1.add_column(Column('b', IntDataType()))
table1.add_column(Column('c', StringDataType(fixed_length=True, length=100)))
