#import pymysql
import MySQLdb

import tempfile
import os
import logging

from TBC.interfaces.sql_interfaces.SQLInterface import *
from TBC.types.Column import Column
from TBC.types.AST import *


class MySQLInterface(SQLInterface):

    def __init__(self, url, port, user, password, database, debug_queries=False, debug_responses=False):
        super(MySQLInterface, self).__init__()

        # self.db = pymysql.connect(url, user, password, database, port=port, local_infile=True)
        self.db = MySQLdb.connect(url, user, password, database, port=port, local_infile=True)
        self.cursor = self.db.cursor()

        self.debug_queries = debug_queries
        self.debug_responses = debug_responses
        self.logger = logging.getLogger()

    def close(self):
        self.db.close()

    def _execute(self, query):
        try:
            if self.debug_queries:
                self.logger.debug(query)
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            if self.debug_responses:
                for result in results:
                    self.logger.debug(result)
            return results
        except Exception as e:
            error_string = 'Exception while executing query: ' + query + '\n' + str(e)
            if 'Deadlock' in error_string:
                self.logger.debug(error_string)
            else:
                self.logger.error(error_string)
            raise SQLException(str(e))

    def stringify_ast(self, ast):
        """
        Recursively convert an abstract syntax tree into a valid MySQL statement
        """

        if type(ast) is UnaryOperation:
            if ast.operator in ('not'):
                return ast.operator.upper() + ' (' + self.stringify_ast(ast.value) + ')'
            elif ast.operator in ('sum', 'count'):
                return ast.operator.upper() + '(' + self.stringify_ast(ast.value) + ')'
            else:
                raise Exception('Unimplemented unary operator ' + str(ast.operator))

        elif type(ast) is BinaryOperation:
            if ast.operator in ('+', '-', '*', '/', '=', '!=', '>', '<', '>=', '<=', 'and', 'or'):
                result = ('(', self.stringify_ast(ast.left_value),
                          ast.operator.upper(), self.stringify_ast(ast.right_value), ')')
                return ' '.join(result)
            elif ast.operator == '==':
                result = ('(', self.stringify_ast(ast.left_value), '=', self.stringify_ast(ast.right_value), ')')
                return ' '.join(result)
            else:
                raise Exception('Unimplemented binary operator ' + str(ast.operator))

        elif type(ast) is Column:
            return ast.get_table_name() + '.' + ast.name

        elif type(ast) is str:
            return '\'' + ast + '\''

        elif type(ast) is bool:
            if ast:
                return '1'
            else:
                return '0'

        elif type(ast) in (int, float):
            return str(ast)

        else:
            raise Exception('Unknown type ' + str(type(ast)))

    def stringify_type(self, type):
        """
        Given a DataType object, return a string representation of the appropriate MySQL type
        :param type: a DataType object
        :return: a MySql representation
        """
        if type == 'int':
            if type.auto_increment:
                return 'INT AUTO_INCREMENT'
            else:
                return 'INT'
        elif type == 'float':
            return 'FLOAT'
        elif type == 'bool':
            return 'BOOLEAN'
        elif type == 'string':
            if type.fixed_length:
                return 'CHAR(' + str(type.length) + ')'
            else:
                return 'VARCHAR(' + str(type.length) + ')'
        else:
            raise Exception('Unknown type ' + str(type))

    def create_table(self, table):
        query = ['CREATE TABLE', table.name, '(']
        primary_specified = False
        for index, column in enumerate(table.columns):
            if column.primary_key:
                primary_specified = True
            query += [column.name, self.stringify_type(column.type)]
            if index + 1 < len(table.columns):
                query.append(',')
            else:
                if primary_specified:
                    query.append(' , PRIMARY KEY (')
                    for column in table.columns:
                        if column.primary_key:
                            query.append(column.name)
                            query.append(',')
                    query.pop(-1)  # remove the last comma
                    query.append(')')
        query.append(')')

        self._execute(' '.join(query))

    def drop_table(self, table):
        query = ['DROP TABLE IF EXISTS', table.name]
        self._execute(' '.join(query))

    def insert(self, table, values):
        query = ['INSERT INTO', table.name, 'VALUES (']
        for index, value in enumerate(values):
            query.append(self.stringify_ast(value))
            if index + 1 < len(values):
                query.append(',')
        query.append(')')
        self._execute(' '.join(query))

    def update(self, table, set_statements, where_statement=None):
        query = ['UPDATE', table.name, 'SET']
        for index, set in enumerate(set_statements):
            left = self.stringify_ast(set.left_value)
            right = self.stringify_ast(set.right_value)
            query += [left, '=', right]
            if index + 1 < len(set_statements):
                query.append(',')
        if where_statement is not None:
            query += ['WHERE', self.stringify_ast(where_statement)]
        self._execute(' '.join(query))

    def select(self, tables, columns, where_statement=None, order_by=None, distinct=False):
        query = ['SELECT']
        if distinct:
            query.append('DISTINCT')
        for index, column in enumerate(columns):
            query.append(self.stringify_ast(column))
            if index + 1 < len(columns):
                query.append(',')
        query.append('FROM')
        for index, table in enumerate(tables):
            query.append(table.name)
            if index + 1 < len(tables):
                query.append(',')
        if where_statement is not None:
            query += ['WHERE', self.stringify_ast(where_statement)]
        if order_by is not None:
            query.append('ORDER BY')
            for index, col in enumerate(order_by):
                query.append(self.stringify_ast(col))
                if index + 1 < len(order_by):
                    query.append(',')
        return self._execute(' '.join(query))

    def delete_rows(self, table, where_statement=None):
        query = ['DELETE FROM', table.name]
        if where_statement is not None:
            query += ['WHERE', self.stringify_ast(where_statement)]
        self._execute(' '.join(query))

    def start_transaction(self):
        self._execute('START TRANSACTION')

    def commit_transaction(self):
        self._execute('COMMIT')

    def abort_transaction(self):
        self._execute('ROLLBACK')

    def csvify(self, row):
        result = []
        for col in row:
            if type(col) is str:
                result.append('"' + col + '"')
            else:
                result.append(str(col))
        return ','.join(result) + '\n'

    def bulk_load(self, table, row_generator):
        datafile = tempfile.NamedTemporaryFile(mode='w', delete=False)
        try:
            # write the data to a CSV file
            for row in row_generator():
                datafile.write(self.csvify(row))
            datafile.close()

            self.start_transaction()
            query = ['LOAD DATA LOCAL INFILE', '\'' + datafile.name + '\'', 'INTO TABLE', table.name,
                     'FIELDS TERMINATED BY \',\'', 'ENCLOSED BY \'"\'', 'LINES TERMINATED BY \'\\n\'']
            self._execute(' '.join(query))
            self.commit_transaction()

        finally:
            os.remove(datafile.name)

    def create_index(self, index_name, table, columns):
        query = ['CREATE INDEX', index_name, 'ON', table.name, '(']
        for index, column in enumerate(columns):
            query.append(column.name)
            if index + 1 < len(columns):
                query.append(',')
        query.append(')')
        self._execute(' '.join(query))

    def get_last_auto_increment_value(self):
        return self._execute('SELECT LAST_INSERT_ID()')
