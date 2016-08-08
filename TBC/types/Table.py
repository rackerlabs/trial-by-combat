class Table(object):
    """
    Represents a SQL table
    """

    def __init__(self, name, columns=()):
        """
        :param name: the name of the table
        :param columns: columns to add to the table.  Columns may
         optionally be added later using the add_column() function
        """

        self.name = name

        self.columns = []
        for column in columns:
            self.add_column(column)

    def add_column(self, column):
        column.table = self
        self.columns.append(column)

    def __getitem__(self, column_name):
        """
        Get a column by name
        :param column_name: the name of the column to get
        :return: a Column
        """
        for column in self.columns:
            if column.name == column_name:
                return column
        raise KeyError('Column ' + column_name + ' is not in table ' + self.name)

    def __str__(self):
        result = '<table ' + self.name + '>\n'
        for column in self.columns:
            result += '\t' + str(column)
            result += '\n'
        return result
