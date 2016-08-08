import time

from TBC.types.Table import *
from TBC.types.AST import *
from TBC.types.Column import *
from TBC.types.DataType import *

_stats = ['average_latency',
          'average_throughput',
          '50.0th_percentile_latency',
          '90.0th_percentile_latency',
          '99.0th_percentile_latency',
          '99.9th_percentile_latency']

_history_table = Table('history')
_history_table.add_column(Column('id', IntDataType(auto_increment=True), primary_key=True))
_history_table.add_column(Column('benchmark_id', StringDataType(fixed_length=False)))
_history_table.add_column(Column('timestamp', FloatDataType()))

_history_stats_table = Table('history_stats')
_history_stats_table.add_column(Column('id', IntDataType(auto_increment=True), primary_key=True))
_history_stats_table.add_column(Column('benchmark', IntDataType())) # foreign key to history.id
_history_stats_table.add_column(Column('event', StringDataType()))
for stat in _stats:
    _history_stats_table.add_column(Column(stat.replace('.', '_'), FloatDataType()))


class Historian(object):
    """
    This class is responsible for storing a summary of past benchmarks
    This is useful for identifying trends in database runs
    """

    def __init__(self, sql_interface):
        self.interface = sql_interface

    def setup_table(self):
        """
        Call this to setup the Historian's database table
        """
        self.interface.start_transaction()
        self.interface.drop_table(_history_table)
        self.interface.drop_table(_history_stats_table)
        self.interface.create_table(_history_table)
        self.interface.create_index('index1', _history_table, [_history_table['timestamp']])
        self.interface.create_table(_history_stats_table)
        self.interface.create_index('index2', _history_stats_table, [_history_stats_table['benchmark']])
        self.interface.commit_transaction()

    def record(self, benchmark_id, summary):
        """
        Record  a statistic
        :param benchmark_id: the ID of the benchmark that the summary describes
        :param summary: of the form {'average_latency': value, 'average_throughput': value, ...}
        """

        self.interface.start_transaction()

        # make an entry for the benchmark in the history table
        values = [0, benchmark_id, time.time()]
        self.interface.insert(_history_table, values)

        benchmark = int(self.interface.get_last_auto_increment_value()[0][0])

        for event in summary:
            values = [0, benchmark, str(event)]
            for stat in _stats:
                values.append(summary[event][stat])
            self.interface.insert(_history_stats_table, values)

        self.interface.commit_transaction()

    def get_statistics_list(self, benchmark_id, event, stat, max_age=None):
        """
        Return a list of statistics for a particular benchmark type
        :param benchmark_id: the ID of the benchmark to get stats for
        :param event: the event to gather data on. (e.g. RandomRW/read)
        :param stat: the statistic to return. (e.g. 'average_latency')
        :param max_age: a number, in seconds.  Do not return results that are older than this
        :return: a list of stats
        """

        assert stat in _stats, 'Invalid stat %s' % stat

        tables = [_history_table, _history_stats_table]
        columns = [_history_stats_table[stat]]

        join_clause = BinaryOperation(_history_table['id'], _history_stats_table['benchmark'], '==')
        benchmark_id_clause = BinaryOperation(_history_table['benchmark_id'], benchmark_id, '==')
        event_clause = BinaryOperation(_history_stats_table['event'], event, '==')
        where = BinaryOperation(BinaryOperation(join_clause, benchmark_id_clause, 'and'), event_clause, 'and')

        if max_age is not None:
            max_age_clause = BinaryOperation(_history_table['timestamp'], time.time() - max_age, '>=')
            where = BinaryOperation(where, max_age_clause, 'and')

        result = self.interface.select(tables, columns, where, order_by=[_history_table['timestamp']])

        clean_result = []
        for value in result:
            clean_result.append(value[0])

        return clean_result

    def clean(self, benchmark_id, max_age):
        """
        Delete all entries older than max age
        :param benchmark_id: the id of the benchmark to clean
        :param max_age: an amount of time in seconds
        """

        self.interface.start_transaction()

        # gather all benchmarks that are too old
        id_clause = BinaryOperation(_history_table['benchmark_id'], str(benchmark_id), '==')
        max_age_clause = BinaryOperation(_history_table['timestamp'], time.time() - max_age, '<=')
        where = BinaryOperation(id_clause, max_age_clause, 'and')
        old_ids = self.interface.select([_history_table], [_history_table['id']], where_statement=max_age_clause)
        self.interface.delete_rows(_history_table, where_statement=max_age_clause)

        # delete each old benchmark
        for old_id in old_ids:
            where = BinaryOperation(_history_stats_table['benchmark'], int(old_id[0]), '==')
            self.interface.delete_rows(_history_stats_table, where_statement=where)

        self.interface.commit_transaction()
