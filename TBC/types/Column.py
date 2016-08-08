class Column(object):
    def __init__(self, column_name, column_type, primary_key=False):
        """
        Describes a column in a table
        :param column_name: the name of the column
        :param column_type: a DataType object representing the type of the column
        """
        self.name = column_name
        self.type = column_type
        self.primary_key = primary_key

        self.table = None

    def get_table_name(self):
        """
        Returns the name of this column's table
        """
        if self.table is None:
            return None
        else:
            return self.table.name

    def __str__(self):
        table_name = '<None>'
        if self.get_table_name() is not None:
            table_name = self.get_table_name()
        return '<column: table=' + table_name + ', name=' + self.name + ', type=' + str(self.type) + '>'
