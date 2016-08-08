import sys
import time
import os
import datetime
import csv
import yaml
import logging
import matplotlib.pyplot as plt

from network_cjl.Network import *
from TBC.core.Log import *
from TBC.core.Historian import Historian
from TBC.benchmarks.benchmark_locator import *
from TBC.interfaces.interface_locator import *
from TBC.utility.Numbers import significant_figures


class TBCMaster(object):

    def __init__(self,
                 port,
                 config,
                 name,
                 log_config=False,
                 csv=False,
                 graph=False,
                 path='./',
                 setup_history=False):
        """
        :param port: The port on which this master should listen
        :param config: a dictionary containing configuration information for this master
        :param name: the name of the benchmark instance that is being run
        :param debug: if True then print network debugging messages
        :param log_config: if True then dump configuration information to a log
        :param csv: if True then dump the results of any benchmarks into a csv file
        :param name: the name of the output directory.  If None then a name will be generated
        :param path: the file path where files should be stored
        :param setup_history: if True then have the Historian setup a new history table
        """
        self.port = port
        self.config = config
        self.log_config = log_config
        self.csv = csv
        self.graph = graph
        self.name = name
        if self.name is None:
            self.name = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')
        self.path = path

        self.datadir = self.path + '/' + self.name
        self.datadir = self.datadir.replace('//', '/')

        if self.csv:
            os.mkdir(self.datadir + '/csv')
        if self.graph:
            os.mkdir(self.datadir + '/graph')

        if self.log_config:
            fObj = open(self.datadir + '/config.yaml', 'w')
            yaml.dump(config, fObj)
            fObj.close()

        self.nm = Network(port)
        self.nm.register_listener('results', self.results_callback)
        self.nm.register_listener('finished_loading', self.finished_loading_callback)
        self.endpoints = []

        self.loaded_nodes = 0
        self.loaded_senders = [] # don't double count if a message is sent more than once
        self.results = []
        self.results_senders = [] # keep track of the endpoint ID of nodes that have already sent results

        self.load_is_finished = False
        self.run_is_finished = False
        self.wait_rate_limiter = 0.01

        self.logger = logging.getLogger()

        self.historian = None
        if 'history' in self.config:
            self.historian = Historian(load_interface(config['history']['interface_id'],
                                                      config['history']['interface_data']))
            if setup_history:
                self.historian.setup_table()


    def add_endpoint(self, (host, port)):
        self.endpoints.append((host, port))

    def start_failure_callback(self, message, (host, port), result):
        if not result:
            self.logger.error('Unable to contact node %s:%d when starting benchmark', host, port)
            self.close()

    def stop_failure_callback(self, message, (host, port), result):
        if not result:
            self.logger.error('Unable to contact node %s:%d when stopping benchmark', host, port)
            self.load_is_finished = True
            self.run_is_finished = True
            self.close()

    def shutdown_failure_callback(self, message, (host, port), result):
        if not result:
            self.logger.error('Unable to contact node %s:%d when shutting down cluster', host, port)

    def load_failure_callback(self, message, (host, port), result):
        if not result:
            self.logger.error('Unable to contact node %s:%d when loading benchmark', host, port)
            self.close(shutdown=True)
            sys.exit(1)

    def load(self):

        assert self.config['load_nodes'] <= len(self.endpoints), \
            'Cannot load on %d nodes, only %d are available.' \
            % (self.config['load_nodes'], len(self.endpoints))

        preload = get_benchmark_preload(self.config['benchmark'], self.config)
        preload()

        for loader_number in xrange(self.config['load_nodes']):
            load_message = Message('load', (self.config, loader_number))

            endpoint = self.endpoints[loader_number]
            self.nm.send(load_message,
                         endpoint,
                         timeout=0.1,
                         request_ack=True,
                         max_sequential_failures=100,
                         callback=self.load_failure_callback)

    def finished_loading_callback(self, message, (host, port)):
        if (host, port) in self.loaded_senders:
            return
        self.loaded_senders.append((host, port))
        self.loaded_nodes += 1
        if self.loaded_nodes == self.config['load_nodes']:
            postload = get_benchmark_postload(self.config['benchmark'], self.config)
            postload()
            self.load_is_finished = True

    def wait_for_load(self):
        """
        This funciton will not return until loading is finished
        """
        while not self.load_is_finished:
            time.sleep(self.wait_rate_limiter)

    def run(self):
        start_message = Message('start', self.config)
        for endpoint in self.endpoints:
            self.nm.send(start_message,
                         endpoint,
                         timeout=1,
                         callback=self.start_failure_callback,
                         max_sequential_failures=3,
                         request_ack=True)

        time.sleep(self.config['duration'])

        stop_message = Message('stop', None)
        for endpoint in self.endpoints:
            self.nm.send(stop_message,
                         endpoint,
                         timeout=1,
                         callback=self.stop_failure_callback,
                         max_sequential_failures=3,
                         request_ack=True)

    def wait_for_run(self):
        """
        This funciton will not return until running is finished
        """
        while not self.run_is_finished:
            time.sleep(self.wait_rate_limiter)

    def close(self, shutdown=True):
        if shutdown:
            shutdown_message = Message('shutdown', None)
            for endpoint in self.endpoints:
                self.nm.send(shutdown_message,
                            endpoint,
                            timeout=1,
                            callback=self.shutdown_failure_callback,
                            request_ack=True,
                            max_sequential_failures=3)
            time.sleep(4)
        self.nm.close()

    def results_callback(self, message, (host, port)):
        if (host, port) in self.results_senders:
            return
        self.results_senders.append((host, port))
        self.results.append(inflate(message.payload, Logger))
        self.logger.info('Recieved logs from %s:%d.  Waiting for %d more nodes to return results.',
                         host, port, len(self.endpoints) - len(self.results))
        if len(self.results) == len(self.endpoints):
            self.analyze_data()

    def analyze_data(self):
        framesize = 1.0 / int(self.config['log_framerate'])

        self.results = clip_logs(self.results, framesize, self.config['log_dead_frames'])
        average_log = average_logs(self.results)

        self.logger.debug(str(average_log))

        self.summarize(average_log)

        event_info = self.extract_frame_event_info(average_log)
        if self.csv:
            self.write_frame_csv(event_info, framesize)
            self.write_latency_csvs(average_log.latency_bins, average_log.latency_bin_size)
        if self.graph:
            self.generate_frame_graphs(event_info, framesize)
            self.generate_latency_graphs(average_log.latency_bins, average_log.latency_bin_size)

        self.run_is_finished = True

    def summarize(self, log):

        # get a set of all event types that were observed
        events = {}
        for frame in log.frames:
            for event in frame.events:
                if event not in events:
                    events[event] = {}

        # extract data from the frames
        for event in events:

            frames_with_event = 0
            total = 0
            total_fails = 0
            total_throughput = 0
            total_latency = 0

            for frame in log.frames:
                if event in frame.events:
                    frames_with_event += 1
                    total += frame.events[event].num
                    total_fails += frame.events[event].failed
                    total_throughput += frame.events[event].tput
                    total_latency += frame.events[event].latency

            events[event]['average_throughput'] = significant_figures(total_throughput / float(frames_with_event), 4)
            events[event]['average_latency'] = significant_figures(total_latency / float(frames_with_event), 4)
            events[event]['fail_percentage'] = significant_figures(total_fails / float(total) * 100, 4)

        # extract data from the latency bins
        percentiles = [0.5, 0.9, 0.95, 0.99, 0.999]
        for event in events:
            total = 0
            for bin in log.latency_bins[event]:
                total += log.latency_bins[event][bin]
            for percentile in percentiles:
                observed = 0
                result = None
                for bin in log.latency_bins[event]:
                    observed += log.latency_bins[event][bin]
                    if float(observed) / total >= percentile:
                        result = bin
                        break
                data_name = str(percentile*100) + 'th_percentile_latency'
                events[event][data_name] = significant_figures(result * log.latency_bin_size, 4)

        summary = ['Benchmark Summary']
        for event in sorted(events.keys()):
            summary.append(event)
            for stat in sorted(events[event].keys()):
                summary.append('\t' + stat.replace('_', ' ') + ': ' + str(events[event][stat]))

        self.logger.info('\n'.join(summary))

        if self.historian is not None:
            self.historian.record(self.config['history']['benchmark_id'], events)

            # self.historian.clean(self.config['history']['benchmark_id'], 100)
            # print self.historian.get_statistics_list(self.config['history']['benchmark_id'], 'average_latency', 'RandomRW/read')

    def extract_frame_event_info(self, log):
        """
        Given a list a Logger object, extract information for each event type from the frames
        :param log: a Logger object
        :return: a dictionary of the following form:

        {'event_type': {
                            'total': [frame1, frame2, frame3, ...]
                            'failed': [frame1, frame2, frame3, ...]
                            'latency': [frame1, frame2, frame3, ...]
                            'throughput': [frame1, frame2, frame3, ...]
                        }
        'event_type': { ... }
        }
        """
        result = {}
        # get a set of all event types that were observed
        events = set()
        for frame in log.frames:
            for event in frame.events:
                events.add(event)
        # ensure that each event type has an entry in the result
        for event in events:
            result[event] = {'total': [],
                             'failed': [],
                             'latency': [],
                             'throughput': []
                             }
        for frame_number, frame in enumerate(log.frames):
            # set some default values (in case this frame doesn't have a particular event)
            for event in result:
                result[event]['total'].append(0)
                result[event]['failed'].append(0)
                result[event]['latency'].append(-1)
                result[event]['throughput'].append(0)
            for event in frame.events:
                result[event]['total'][frame_number] = frame.events[event].num
                result[event]['failed'][frame_number] = frame.events[event].failed
                result[event]['latency'][frame_number] = frame.events[event].latency
                result[event]['throughput'][frame_number] = frame.events[event].tput
        return result

    def write_frame_csv(self, data, framesize):
        """
        Generate a csv file of the data from the log frames
        :param filename: the file name of the csv file to create
        :param data: an object with the same format as returned by self.extract_frame_event_info()
        :param framesize: the size, in seconds, of each frame
        """

        columns = []

        filename = self.datadir + '/csv/frame_data.csv'

        for event_type in data:
            for stat in data[event_type]:
                column = []
                header = event_type + ': ' + stat
                column.append(header)
                column += data[event_type][stat]
                columns.append(column)

        # add a column with the frame time included (useful for graphing manually)
        column = ['time']
        assert len(columns) > 0 and len(columns[0]) > 0, 'No frame data received'
        for frame_number in xrange(len(columns[0])-1):
            column.append(significant_figures(frame_number * framesize, 4))
        columns = [column] + columns

        rows = []
        row_number = 0
        while row_number < len(columns[0]):
            rows.append([])
            for column in columns:
                rows[row_number].append(column[row_number])
            row_number += 1

        fObj = open(filename, 'w')
        csvw = csv.writer(fObj)
        csvw.writerows(rows)
        fObj.close()

    def write_latency_csvs(self, data, binsize):
        """
        Write several csvs with the latency bin information
        :param filename: the path to a directory where the csvs should be stored
        :param data: the object stored at Logger.latency_bins
        :param binsize: the size of a bin
        """

        #used for sorting a list of tuples
        def key(tup):
            return tup[0]

        for event in data:

            filename = self.datadir + '/csv/' + event.replace('/', '-') + '.csv'

            # construct a list of tuples
            bins = []
            for bin in data[event]:
                bins.append((significant_figures(bin * binsize, 4), data[event][bin]))
            bins = sorted(bins, key=key)

            bins = [('Latency', 'Number of events')] + bins

            fObj = open(filename, 'w')
            csvw = csv.writer(fObj)
            csvw.writerows(bins)
            fObj.close()

    def generate_frame_graphs(self, data, framesize):
        """
        Generate a small set of graphs
        :param data: a set of data in the same format as produced by extract_frame_event_info()
        """

        for event in data:
            for stat in data[event]:
                if stat == 'total':
                    continue

                graph_name = event + '_' + stat
                graph_name = graph_name.replace('/', '-')

                title = event + ': ' + stat

                yaxis = data[event][stat]

                xaxis = []
                for point in xrange(len(yaxis)):
                    xaxis.append(point * framesize)


                fig = plt.figure()
                fig.suptitle(title)
                ax = fig.add_subplot(111)
                plt.xlabel('Elapsed Time (seconds)')
                plt.ylabel(stat)
                ax.plot(xaxis, yaxis)
                ymax = max(yaxis) * 1.1
                if ymax == 0:
                    ymax = 1
                ax.set_ylim([0, ymax])
                ax.set_xlim([0, max(xaxis)])
                fig.savefig(self.datadir + '/graph/' + graph_name + '.png')
                plt.close('all')

    def generate_latency_graphs(self, data, binsize):
        """
        Generate graphs for latency bins
        :param data: the object stored at Logger.latency_bins
        :param binsize: the size of a bin
        """

        def key(tup):
            return tup[0]

        for event in data:

            filename = self.datadir + '/graph/' + event.replace('/', '-') + '_histogram.png'
            title = event + ' Latency Histogram'

            # construct a list of tuples
            bins = []
            for bin in data[event]:
                bins.append((significant_figures(bin * binsize, 4), data[event][bin]))
            bins = sorted(bins, key=key)

            # chop off the tail (on the right side)
            keep = .995
            total = 0
            for bin in bins:
                total += bin[1]
            included = 0
            for index, bin in enumerate(bins):
                included += bin[1]
                if float(included) / float(total) > keep:
                    bins = bins[:index]
                    break

            # reduce the number of bins to a reasonable number by merging bins
            optimal_number = 32
            merge_factor = int(len(bins) / optimal_number)
            if merge_factor > 1:
                new_binsize = binsize * merge_factor
                # populate the new set of bins with empty bins
                new_bins = []
                largest_bin = bins[-1][0]
                bin_number = 0
                while (bin_number-1) * new_binsize < largest_bin:
                    new_bins.append([bin_number * new_binsize, 0])
                    bin_number += 1
                # put the old bins into the new bins
                new_bin_index = 0
                for bin in bins:
                    while bin[0] > new_bins[new_bin_index][0]:
                        new_bin_index += 1
                    new_bins[new_bin_index-1][1] += bin[1]
                bins = new_bins

            # chop off the tail (on the left side)
            keep = 0.99
            included = 0
            for index, bin in enumerate(reversed(bins)):
                included += bin[1]
                if float(included) / float(total) > keep:
                    bins = bins[len(bins)-index:]
                    break

            xaxis_lables = []
            for bin, num in bins:
                xaxis_lables.append(bin)
            yaxis = []
            for bin, num in bins:
                yaxis.append(num)

            # normalize y axis
            for index, bin in enumerate(yaxis):
                yaxis[index] = float(bin) / float(total) * 100

            # create the x axis
            xaxis = []
            for index in xrange(len(yaxis)):
                xaxis.append(index)

            # convert lables from seconds to ms
            for index, value in enumerate(xaxis_lables):
                xaxis_lables[index] = value * 1000.0

            fig = plt.figure()
            fig.suptitle(title)
            ax = fig.add_subplot(111)
            if len(xaxis) > 0 and xaxis[-1] != 0:
                ax.set_xlim([0, xaxis[-1]])
            ax.bar(xaxis, yaxis)
            plt.xticks(xaxis, xaxis_lables, rotation='vertical')
            plt.xlabel('Latency (ms)')
            plt.ylabel('Percentage of operations')
            plt.subplots_adjust(bottom=0.15)
            fig.savefig(filename)

