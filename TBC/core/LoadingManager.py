import multiprocessing
import time

class LoadingManager(object):
    """
    This class is responsible for spinning up, spinning down, and coordinating loading processes on
    a single node.
    """

    def __init__(self, loader, num_processes, node_number, total_nodes):
        self.loader = []
        self.processes = []

        begin_loader_id = num_processes * node_number
        total_loaders = num_processes * total_nodes

        for pnum in xrange(num_processes):
            proc = multiprocessing.Process(target=loader, args=(begin_loader_id+pnum, total_loaders))
            self.processes.append(proc)

        self.node_number = node_number


    def run(self):
        for index, proc in enumerate(self.processes):
            proc.start()
        for proc in self.processes:
            proc.join()
