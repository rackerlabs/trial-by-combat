import random

from TBC.interfaces.interface_locator import load_interface
import TBC.benchmarks.sql.RandomTransactions.schema as schema
from TBC.types.AST import *
from TBC.core.Task import *

"""
This benchmark performs random transactions against the following schema:

TABLE rTxn (id INT, a INT, b INT, c CHAR(100))
            ^       ^      ^      ^
            |       |      |      |
            |       |      |      | 100 characters of filler text
            |       |      |
            |       |      | a random integer that is written by write queries
            |       |
            |       | an integer between 0 and a_max, used by select queries
            |
            | the primary key

There are two types of queries:

select * from rTxn where a=<some number>;
update rTxn set b=<random number> where a=<some number>;
"""


def get_benchmark(config):

    class RandomTransactions(Task):
        report_stats = False

        def on_start(self):
            self.set_client(load_interface(config['interface']['id'], config['interface']['data']))

        def on_end(self):
            self.client.close()

        ############

        class txn1(Task):

            def on_start(self):
                self.client.start_transaction()

            ####

            class cont(Task):
                weight = config['txn1_continue']
                report_stats = False

                class read(Tasklet):
                    weight = config['txn1_read']
                    def operation(self):
                        tables = [schema.table1]
                        where = BinaryOperation(schema.table1['a'], random.randint(0, config['a_max']), '==')
                        self.client.select(tables, schema.table1.columns, where)
                        self.finish()

                class write(Tasklet):
                    weight = config['txn1_write']
                    def operation(self):
                        set_statements = [BinaryOperation(schema.table1['b'], random.randint(0, 100), '=')]
                        where = BinaryOperation(schema.table1['a'], random.randint(0, config['a_max']), '==')
                        self.client.update(schema.table1, set_statements, where)
                        self.finish()

            ####

            class end(Task):
                weight = config['txn1_end']
                report_stats = False

                class commit(Tasklet):
                    weight = config['txn1_commit']
                    def operation(self):
                        self.client.commit_transaction()
                        self.finish(2)

                class abort(Tasklet):
                    weight = config['txn1_abort']
                    def operation(self):
                        self.client.abort_transaction()
                        self.finish(2)

    return RandomTransactions


def get_preload(config):
    def preload():
        interface = load_interface(config['interface']['id'], config['interface']['data'])
        interface.start_transaction()
        interface.drop_table(schema.table1)
        interface.create_table(schema.table1)
        interface.commit_transaction()
        interface.close()
    return preload


def get_load(config):
    def load(loader_id, total_loaders):
        interface = load_interface(config['interface']['id'], config['interface']['data'])

        rows_per_loader = config['table_size'] / total_loaders
        start_index = loader_id * rows_per_loader
        end_index = start_index + rows_per_loader
        # have the last loader load any leftover rows
        if loader_id + 1 == total_loaders:
            end_index = config['table_size']

        #print 'Loading rows %d to %d' % (start_index, end_index)

        def table1_generator():
            filler = '~' * 100
            for row in xrange(start_index, end_index):
                yield (row, random.randint(0, config['a_max']), 0, filler)

        interface.bulk_load(schema.table1, table1_generator)

        interface.close()
    return load


def get_postload(config):
    def postload():
        interface = load_interface(config['interface']['id'], config['interface']['data'])
        interface.start_transaction()
        interface.create_index('index1', schema.table1, [schema.table1['a']])
        interface.commit_transaction()
        interface.close()
    return postload