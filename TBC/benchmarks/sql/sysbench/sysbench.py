import random

from TBC.interfaces.interface_locator import load_interface
import TBC.benchmarks.sql.sysbench.schema as schema
from TBC.types.AST import *
from TBC.core.Task import *
from TBC.interfaces.sql_interfaces.SQLInterface import SQLException


def get_benchmark(config):

    total_special = int(config['table_size'] * config['chance_to_be_special'])
    special_step = int(config['table_size'] / total_special)

    def _get_random_key():

        # really stupid distribution, but it's the sysbench default
        # select config['chance_to_be_special']% of the keys,
        #     return one of these keys config['special_chosen_percentage']% of the time, otherwise return a uniformly
        #     random value
        if config['distribution'] == 'special':

            is_special = random.random() < config['special_chosen_percentage']
            if is_special:
                return random.randint(0, total_special-1) * special_step
            else:
                return random.randint(0, config['table_size'] - 1)

        elif config['distribution'] == 'uniform':
            return random.randint(0, config['table_size']-1)

        else:
            raise KeyError('Distribution type ' + config['distribution'] + ' is not currently implemented.')

    class sysbench(Task):
        report_stats = False

        def on_start(self):
            self.set_client(load_interface(config['interface']['id'], config['interface']['data']))

        def on_end(self):
            self.client.close()

        class Transaction(Task):
            weight = 1

            def on_start(self):
                try:
                    self.client.start_transaction()
                except SQLException as e:
                    self.fail(0)
                    return

                # used to store the number of times each operation has been performed
                self.point_count = 0
                self.range_count = 0
                self.range_sum_count = 0
                self.range_order_count = 0
                self.range_distinct_count = 0
                self.update_index_count = 0
                self.update_non_index_count = 0
                self.delete_count = 0

                # deletes are followed by an insertion
                # use this to pass the index that should be re-inserted
                self.reinsertion_index = None

            def on_end(self):
                try:
                    self.client.commit_transaction()
                except SQLException as e:
                    self.fail(0)
                    return

            class point(Tasklet):
                weight = 1
                def operation(self):
                    where = BinaryOperation(schema.table1['id'], _get_random_key(), '==')

                    try:
                        self.client.select([schema.table1], schema.table1.columns, where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.point_count += 1
                    if self.parent.point_count < config['point_operations']:
                        self.jump('point')
                    else:
                        self.jump('range')

            class range(Tasklet):
                weight = 0
                def operation(self):
                    lower_bound = _get_random_key()
                    upper_bound = lower_bound + config['range_size']
                    ge = BinaryOperation(schema.table1['id'], lower_bound, '>=')
                    le = BinaryOperation(schema.table1['id'], upper_bound, '<=')
                    where = BinaryOperation(ge, le, 'and')

                    try:
                        self.client.select([schema.table1], [schema.table1['c']], where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.range_count += 1
                    if self.parent.range_count < config['range_operations']:
                        self.jump('range')
                    else:
                        self.jump('range_sum')

            class range_sum(Tasklet):
                weight = 0
                def operation(self):
                    lower_bound = _get_random_key()
                    upper_bound = lower_bound + config['range_size']
                    ge = BinaryOperation(schema.table1['id'], lower_bound, '>=')
                    le = BinaryOperation(schema.table1['id'], upper_bound, '<=')
                    where = BinaryOperation(ge, le, 'and')
                    sum_col = UnaryOperation(schema.table1['k'], 'sum')

                    try:
                        self.client.select([schema.table1], [sum_col], where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.range_sum_count += 1
                    if self.parent.range_sum_count < config['range_sum_operations']:
                        self.jump('range_sum')
                    else:
                        self.jump('range_order')

            class range_order(Tasklet):
                weight = 0
                def operation(self):
                    lower_bound = _get_random_key()
                    upper_bound = lower_bound + config['range_size']
                    ge = BinaryOperation(schema.table1['id'], lower_bound, '>=')
                    le = BinaryOperation(schema.table1['id'], upper_bound, '<=')
                    where = BinaryOperation(ge, le, 'and')

                    try:
                        self.client.select([schema.table1], [schema.table1['c']], where, order_by=[schema.table1['c']])
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.range_order_count += 1
                    if self.parent.range_order_count < config['range_order_operations']:
                        self.jump('range_order')
                    else:
                        self.jump('range_distinct')

            class range_distinct(Tasklet):
                weight = 0
                def operation(self):
                    lower_bound = _get_random_key()
                    upper_bound = lower_bound + config['range_size']
                    ge = BinaryOperation(schema.table1['id'], lower_bound, '>=')
                    le = BinaryOperation(schema.table1['id'], upper_bound, '<=')
                    where = BinaryOperation(ge, le, 'and')

                    try:
                        self.client.select([schema.table1],
                                           [schema.table1['c']],
                                           where,
                                           order_by=[schema.table1['c']],
                                           distinct=True)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.range_distinct_count += 1
                    if self.parent.range_distinct_count < config['range_distinct_operations']:
                        self.jump('range_distinct')
                    else:
                        self.jump('update_index')

            class update_index(Tasklet):
                weight = 0
                def operation(self):
                    k_plus_1 = BinaryOperation(schema.table1['k'], 1, '+')
                    set_statement = BinaryOperation(schema.table1['k'], k_plus_1, '=')
                    where = BinaryOperation(schema.table1['id'], _get_random_key(), '==')

                    try:
                        self.client.update(schema.table1, [set_statement], where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.update_index_count += 1
                    if self.parent.update_index_count < config['update_index_operations']:
                        self.jump('update_index')
                    else:
                        self.jump('update_non_index')

            class update_non_index(Tasklet):
                weight = 0
                filler = '~' * 120
                def operation(self):
                    set_statement = BinaryOperation(schema.table1['c'], self.filler, '=')
                    where = BinaryOperation(schema.table1['id'], _get_random_key(), '==')

                    try:
                        self.client.update(schema.table1, [set_statement], where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.update_non_index_count += 1
                    if self.parent.update_non_index_count < config['update_non_index_operations']:
                        self.jump('update_non_index')
                    else:
                        self.jump('delete')

            class delete(Tasklet):
                weight = 0
                def operation(self):
                    self.parent.reinsertion_index = _get_random_key()
                    where = BinaryOperation(schema.table1['id'], self.parent.reinsertion_index, '==')

                    try:
                        self.client.delete_rows(schema.table1, where)
                    except SQLException as e:
                        self.fail(1)
                        return

                    self.parent.delete_count += 1

                    self.jump('insert')


            class insert(Tasklet):
                weight = 0
                def operation(self):
                    values = (self.parent.reinsertion_index,
                              0,
                              ' ',
                              'aaaaaaaaaaffffffffffrrrrrrrrrreeeeeeeeeeyyyyyyyyyy')

                    try:
                        self.client.insert(schema.table1, values)
                    except SQLException as e:
                        self.fail(1)
                        return

                    if self.parent.delete_count < config['delete_operations']:
                        self.jump('delete')
                    else:
                        self.finish()
    return sysbench


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

        def table1_generator():
            pad = 'qqqqqqqqqqwwwwwwwwwweeeeeeeeeerrrrrrrrrrtttttttttt'
            for row in xrange(start_index, end_index):
                yield (row, 0, ' ', pad)

        interface.bulk_load(schema.table1, table1_generator)

        interface.close()
    return load


def get_postload(config):
    def postload():
        interface = load_interface(config['interface']['id'], config['interface']['data'])
        interface.start_transaction()
        interface.create_index('indexK', schema.table1, [schema.table1['k']])
        interface.commit_transaction()
        interface.close()
    return postload
