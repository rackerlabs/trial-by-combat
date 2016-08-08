from TBC.types.DataType import *
from TBC.types.Column import Column
from TBC.types.Table import Table

table1 = Table('sysbench')
table1.add_column(Column('id', IntDataType()))
table1['id'].primary_key = True
table1.add_column(Column('k', IntDataType()))
table1.add_column(Column('c', StringDataType(fixed_length=True, length=120)))
table1.add_column(Column('pad', StringDataType(fixed_length=True, length=60)))
