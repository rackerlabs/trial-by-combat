from TBC.interfaces.Interface import Interface

class SQLException(Exception):
    pass

class SQLInterface(Interface):

    def __init__(self):
        super(SQLInterface, self).__init__()

    def close(self):
        pass

    def create_table(self, table):
        """
        Create a new table
        :param table: a Table object
        """
        raise Exception('create_table is not implemented')

    def drop_table(self, table):
        """
        Delete a table.  This should not fail if the table doesn't exist
        :param table: the Table to drop
        """
        raise Exception('drop_table is not implemented')

    def insert(self, table, values):
        """
        Insert a new row into a table
        :param table: the table to insert into
        :param values: a tuple of values to be inserted
        """
        raise Exception('insert is not implemented')

    def update(self, table, set_statements, where_statement=None):
        """
        Update one or more rows in the database
        :param table: the table it update
        :param set_statements: a list of ASTs
        :param where_statements: an abstract syntax tree that evaluates to a binary value.
                                    This value may be None if there is no where clause needed
        """
        raise Exception('update is not implemented')

    def select(self, tables, columns, where_statement=None, order_by=None, distinct=False):
        """
        Select certain values from a table
        :param tables: a list of tables to be selected from
        :param columns: a list of ColumnDescriptions, the columns that should be returned
        :param where_statement: an abstract syntax tree that evaluates to a binary value.
                                    This value may be None if there is no where clause needed
        :param order_by: a list of columns that should be used to order the result.  This value may be None
                            if there is no order_by clause
        :param distinct: if True then this select statement should only return distinct values
        :return: a list of tuples with the values from the database
        """
        raise Exception('select is not implemented')

    def delete_rows(self, table, where_statement=None):
        """
        Delete rows from a table
        :param table: the table to delete from
        :param where_statement: an abstract syntax tree that evaluates to a binary value.
                                    This value may be None if there is no where clause needed
        """
        raise Exception('delete is not implemented')

    def start_transaction(self):
        """
        Start a transaction
        """
        raise Exception('start_transaction is not implemented')

    def commit_transaction(self):
        """
        Commit a transaction
        """
        raise Exception('commit_transaction is not implemented')

    def abort_transaction(self):
        """
        Abort a transaction
        :return:
        """
        raise Exception('abort_transaction is not implemented')

    def create_index(self, index_name, table, columns):
        """
        Add an index to one or more columns
        :param index_name: the name of the index
        :param table: a Table
        :param columns: a list of Columns
        """
        raise Exception('add_index is not implemented')

    def get_last_auto_increment_value(self):
        """
        Return the last value that was generatead using auto-increment
        :return: int
        """
        raise Exception('get_last_auto_increment_value is not implemented')

    def bulk_load(self, table, row_generator):
        """
        Implement this function to speed up the initial loading of the database.  If not implemented,
        the default behavior is to use the insert method
        :param table: the table that things should be inserted into
        :param row_generator: all rows in the row_generator should be added to the table
        """
        self.start_transaction()
        for row in row_generator():
            self.insert(table, row)
        self.commit_transaction()
