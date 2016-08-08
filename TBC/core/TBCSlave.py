import sys
import os
import Queue
import logging

from TBC.benchmarks.benchmark_locator import *
from TBC.core.BenchmarkManager import BenchmarkManager
from TBC.core.LoadingManager import LoadingManager
from network_cjl.Network import *


class TBCSlave(object):

    def __init__(self, port, debug=False):
        self.port = port
        self.nm = Network(port)

        self.nm.register_listener('start', self.start_callback)
        self.nm.register_listener('stop', self.stop_callback)
        self.nm.register_listener('shutdown', self.shutdown_callback)
        self.nm.register_listener('load', self.load_callback)

        self.waiting_calls = Queue.Queue()
        self.spin_limiter = 0.01
        self.pm = None
        self.state = 'ready'
        self.logger = logging.getLogger()

        self.debug = debug # fixme: currently ignored

    def call_on_main_thread(self, function, *args, **kwargs):
        """
        Send a function here and it will be called on the main thread
        """
        self.waiting_calls.put((function, args, kwargs))

    def wait_until_finished(self):
        """
        This function will not return until the TBCSlave is ready to exit
        """
        while self.nm.alive:
            try:
                function, args, kwargs = self.waiting_calls.get(block=False)
                function(*args, **kwargs)
            except Queue.Empty:
                time.sleep(self.spin_limiter)

    def start_callback(self, message, (host, port)):
        def start():
            if self.state != 'ready':
                return
            self.state = 'run'
            config = message.payload
            self.logger.info('Executing %s benchmark', config['benchmark'])
            benchmark = get_benchmark(config['benchmark'], config)
            self.pm = BenchmarkManager(config['log_framerate'], config['log_latency_bin_size'])
            self.pm.prepare(benchmark, config['processes_per_node'])
            self.pm.start()
        self.call_on_main_thread(start)

    def stop_callback(self, message, (host, port)):
        if self.state != 'run':
            return
        self.state = 'ready'
        self.logger.info('Stopping benchmark')

        self.pm.close()

        payload = deflate(self.pm.benchmark_log)
        mess = Message('results', payload)
        self.nm.send(mess, (host, port), timeout=0.1, request_ack=True, max_sequential_failures=100)

        self.pm = None

    def load_callback(self, message, (host, port)):
        """
        Expects message.payload to have the form (config, node_number)
        """
        if self.state != 'ready':
            return
        self.state = 'load'

        config, node_number = message.payload
        self.logger.info('Loading %s benchmark', config['benchmark'])

        processes = config['load_processes_per_node']
        load_nodes = config['load_nodes']

        loader = get_benchmark_load(config['benchmark'], config)
        LoadingManager(loader, processes, node_number, load_nodes).run()

        response = Message('finished_loading', None)
        self.nm.send(response, (host, port), request_ack=True, timeout=0.1, max_sequential_failures=100)
        self.logger.info('Finished loading')
        self.state = 'ready'

    def shutdown_callback(self, message, (host, port)):
        self.logger.info('Shutdown command received')
        self.close()

    def close(self):
        if self.pm is not None:
            self.pm.close(soft=False)
        self.nm.close()
        os._exit(0) # running on a remote machine, don't take any chance of orphaned threads

if __name__ == '__main__':

    slave = None

    try:
        port = int(raw_input('Port: '))
        slave = TBCSlave(port, debug=True)
        slave.wait_until_finished()
    finally:
        if slave is not None:
            slave.close()