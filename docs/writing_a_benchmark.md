[RandomRW.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/interfaces/interface_locator.py
[RandomTransactions.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/benchmarks/sql/RandomTransactions/RandomTransactions.py
[sysbench.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/benchmarks/sql/RandomTransactions/RandomTransactions.py
[benchmark_locator.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/benchmarks/benchmark_locator.py

# Writing a Benchmark

Writing a benchmark is simple.  This document details the main concepts needed for writting a benchmark.

Sometimes an example is the best way to understand something.  For a full but simple example, see [RandomRW.py]

## Writing a Task

A benchmark is made up of a collection of Tasks.  A Task is a unit of work and can be further sub-divided into nested Tasks.  Each Task has a weight; during execution the benchmark randomly selects Tasks to perform with a probability corresponding to their weights.
 
A benchmark is itself a 'giant' Task.  A benchmark needs to be wrapped in a 'factory' function.  This function accepts configuration data that can be used to help construct the benchmark.

~~~~
from TBC.core.Task import *
 
def get_benchmark(config):
 
    # config is the result of running yaml.load() on the benchmark's configuration file
    # configuration options can be accessed via square bracket syntax, i.e. config['key']
 
    class MyBenchmark(Task):
        pass
~~~~

### Nesting Tasks

Tasks may be nested inside other tasks.

~~~~
class MyBenchmark(Task):
     
    class sub_task_one(Task):  
        weight = 5
 
        class op1(Tasklet):
            weight = 9
            def operation(self):
                # perform operation 1
                pass
 
        class op2(Tasklet):
            # 1 is the default weight if it is not defined
            def operation(self):
                # perform operation 2
                pass
                self.finish()   # this call causes sub_task_one() to finish executing
 
    class sub_task_two(Task):
        pass
        # ...
~~~~

One a Task begins, it will execute continuously until the finish() function is called (see the end of class op2 above).  If finish() is never called then the Task will continue executing until the benchmark is ended.

finish() accepts an optional argument: depth.  The default value if not specified is 1.  The depth is used to cause parent Tasks to end.  finish(1) causes the parent Task of the Tasklet to close.  finish(2) causes the parent Task and grandparent Task to close, and so on.


A good example on how to use nested Tasks and the finish() command can be found in [RandomTransactions.py].

### on\_start() and on\_end()

You may optionally define the functions on\_start() and on\_end() inside a Task class.  If defined, on\_start() will be called immediately before a Task is started.  If defined, on\_end() is called immediately after a Task becomes finished (i.e. finish() is invoked).

~~~~
class my_task(Task):
     
    def on_start(self):
        pass
        # do initialization
        # maybe start a transaction
 
    def on_end(self):
        pass
        # do cleanup
        # maybe commit changes (or roll them back)
~~~~

### fail()

Sometimes a task fails.  To indicate to the benchmark that a Tasklet has failed, call fail().  fail() has an optional depth parameter that defaults to 0.  Setting the depth to 1 will also cause the parent Task to fail.  Setting it to 2 will cause the grandparent to fail, and so on.

Calling fail() against a Task will cause it to stop executing.

~~~~
class my_task(Task):
    class operation_one(Tasklet):
        def operation(self):
            if error_condition:
                self.fail()
            else:
                # ...
~~~~

### Fixme: write about setting a client

## Writing a Tasklet

Tasklets are leaf nodes within a Task hierarchy.  A Tasklet describes a small unit of work to be performed by the benchmark.  Tasklets contain actual code to be executed (as opposed to Tasks which do not directly contain benchmark code).

~~~~
class MyBenchmark(Task):
    class operation_one(Tasklet):
        weight = 9                  # optional parameter, specifies frequency of execution
        def operation(self):
            # perform operation 1
            pass
 
    class operation_two(Tasklet):
        weight = 1
        def operation(self):
            # perform operation 2
            pass
~~~~

## preload(), load(), and postload()

These are the functions that are called in order to load the benchmark.  They should be defined in the same file as the benchmark class.  Each function should be wrapped in a "factory" function (see the example below).

preload() and postload() are run on a single thread.  load() is run on multiple threads if specified in the configuration files.  preload() and postload() are optional and do not need to be defined.  load() is not optional.

Below is an example lifted from [sysbench.py].

~~~~
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
~~~~

## Installing a new benchmark

In order to use a benchmark you must first put it in a place where Trial By Combat can find it.  Modify the data structure "_benchmarks" at the top of [benchmark_locator.py] in order to use a custom benchmark.