import TBC.benchmarks.kvs.RandomRW.RandomRW as RandomRW
import TBC.benchmarks.sql.RandomTransactions.RandomTransactions as RandomTransactions
import TBC.benchmarks.sql.sysbench.sysbench as sysbench

_benchmarks = {
    'RandomRW': {
        'preload': RandomRW.get_preload,
        'load': RandomRW.get_load,
        'benchmark': RandomRW.get_benchmark,
        'default_config': 'TBC/benchmarks/kvs/RandomRW/config.yaml'
    },
    'RandomTransactions': {
        'preload': RandomTransactions.get_preload,
        'load': RandomTransactions.get_load,
        'postload': RandomTransactions.get_postload,
        'benchmark': RandomTransactions.get_benchmark,
        'default_config': 'TBC/benchmarks/sql/RandomTransactions/config.yaml'
    },
    'sysbench': {
        'preload': sysbench.get_preload,
        'load': sysbench.get_load,
        'postload': sysbench.get_postload,
        'benchmark': sysbench.get_benchmark,
        'default_config': 'TBC/benchmarks/sql/sysbench/config.yaml'
    }
}

def _noop(*args, **kwargs):
    """
    No Op funciton, acts as a placeholder
    """
    return

def get_benchmark_preload(benchmark, config):
    """
    Get the function that should be called prior to loading (for single threaded use)
    :param benchmark:
    :param config:
    :return:
    """
    if 'preload' in _benchmarks[benchmark]:
        return _benchmarks[benchmark]['preload'](config)
    else:
        return _noop


def get_benchmark_load(benchmark, config):
    """
    Get the function that loads the database (for multithreaded use)
    :param benchmark: the benchmark name
    :return: a load function.  This function accepts a config argument.
    """
    if 'load' in _benchmarks[benchmark]:
        return _benchmarks[benchmark]['load'](config)
    return _noop


def get_benchmark_postload(benchmark, config):
    """
    Get the function that should be called after loading (for single threaded use)
    :param benchmark:
    :param config:
    :return:
    """
    if 'postload' in _benchmarks[benchmark]:
        return _benchmarks[benchmark]['postload'](config)
    else:
        return _noop


def get_benchmark(benchmark, config):
    """
    Return a benchmark
    :param benchmark: the benchmark name
    :return: a benchmark Task (or a function that returns one)
    """
    return _benchmarks[benchmark]['benchmark'](config)


def get_default_config(benchmark):
    """
    Get the file path of the default configuration file for the benchmark
    :param benchmark: the benchmark name
    :return: the file path of the default configuration file
    """
    return _benchmarks[benchmark]['default_config']
