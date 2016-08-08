import random

from TBC.core.Task import *
from TBC.interfaces.interface_locator import load_interface


def get_benchmark(config):
    class RandomRW(Task):
        report_stats = False

        def on_start(self):
            self.set_client(load_interface(config['interface']['id'], config['interface']['data']))

        def on_end(self):
            self.client.close()

        class read(Tasklet):
            weight = config['read']
            def operation(self):
                self.client.get(str(random.randint(0, config['keys'])))

        class write(Tasklet):
            weight = config['write']
            def operation(self):
                self.client.set(str(random.randint(0, config['keys'])), str(random.randint(0, 1000000)))

    return RandomRW


def get_preload(config):
    def preload():
        interface = load_interface(config['interface']['id'], config['interface']['data'])
        interface.delete_all()
        interface.close()
    return preload


def get_load(config):
    def load(loader_id, total_loaders):
        """
        :param loader_id: the loader number (e.g. 3 --> the 4th loading process).  Starts counting with 0
        :param total_loaders: the total number of loaders
        """

        interface = load_interface(config['interface']['id'], config['interface']['data'])

        keys_per_loader = config['keys'] / total_loaders
        start_index = loader_id * keys_per_loader
        end_index = start_index + keys_per_loader
        # have the last loader load any leftover keys
        if loader_id + 1 == total_loaders:
            end_index = config['keys']

        #print 'loading from %d to %d' % (start_index, end_index)
        def generator():
            for key in xrange(start_index, end_index):
                yield (str(key), str(random.randint(0, 1000000)))

        interface.bulk_load(generator)
        interface.close()
    return load