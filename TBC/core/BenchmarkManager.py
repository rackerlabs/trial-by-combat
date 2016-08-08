import signal
import os
import multiprocessing
import time
import Queue
import sys
import logging

from TBC.core.TaskManager import TaskManager
from TBC.core.IProcMessage import IProcMessage
from TBC.core.Log import *

class BenchmarkManager(object):
    """
    This class is responsible for spinning up, spinning down, and coordinating TaskManagers on a single node
    """

    def __init__(self, log_framerate, log_latency_bin_size):

        self.alive = True
        self.rate_limit = 0.01
        self.soft_stop_timeout = 2
        self.log_framerate = log_framerate
        self.log_latency_bin_size = log_latency_bin_size

        # (Process, in_queue, out_queue)
        # the process pulls things from the in_queue and puts things into the out_queue
        self.processes = []

        self.benchmark_log = None
        self.logger = logging.getLogger()

    def prepare(self, task, number):
        """
        Setup a process but don't start it yet
        :param task: the task that the process will run
        :param number: how many processes to spawn
        """
        for pnum in range(number):
            in_queue = multiprocessing.Queue()
            out_queue = multiprocessing.Queue()
            tm = TaskManager(in_queue, out_queue, task)
            proc = multiprocessing.Process(target=tm.start)
            self.processes.append((proc, in_queue, out_queue))

    def start(self):
        """
        Start all processes.  Warning: this should not be called if some processes have already
        been started.
        """
        self.benchmark_log = Logger(self.log_framerate, self.log_latency_bin_size)

        for proc, in_queue, out_queue in self.processes:
            proc.start()
        self.main_loop()

    def close(self, soft=True):
        self.alive = False
        if soft:
            self.soft_stop()
            time.sleep(self.soft_stop_timeout)
            self.check_for_messages()
        self.hard_stop()
        if soft:
            self.benchmark_log.finish()

    def soft_stop(self):
        """
        Request that all processes stop but do not force them
        """
        m = IProcMessage('stop', None)
        for proc, in_queue, out_queue in self.processes:
            in_queue.put(m)

    def hard_stop(self):
        """
        Force all processes to immediately stop
        """
        for proc, in_queue, out_queue in self.processes:
            try:
                proc.terminate()
            except:
                pass

    def handle_message(self, message):
        if message.type == 'report':
            event, delta_t, failed = message.payload
            self.benchmark_log.log(event, delta_t, failed)

        elif message.type == 'err':
            self.close()
            self.logger.critical(message.payload)
            exit(-1)
        else:
            self.logger.error('Unrecognized message type ' + message.type)
            self.close()
            exit(-1)

    def check_for_messages(self):
        """
        Check all of the queues for messages
        :return: True if at least one message received, otherwise False
        """
        work_done = False
        for proc, in_queue, out_queue in self.processes:
            while True:
                try:
                    message = out_queue.get(block=False)
                    work_done = True
                    self.handle_message(message)
                except Queue.Empty:
                    break
        return work_done

    def main_loop(self):
        while self.alive:
            work_done = self.check_for_messages()
            if not work_done:
                time.sleep(self.rate_limit)
