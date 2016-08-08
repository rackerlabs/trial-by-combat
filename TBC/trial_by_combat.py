#!/usr/bin/env python

import argparse
import yaml
import os
import shutil
import logging
import subprocess
import signal
import traceback
import datetime
import sys
import time

from TBC.core.TBCSlave import TBCSlave
from TBC.core.TBCMaster import TBCMaster
from TBC.core.Historian import Historian
from TBC.interfaces.interface_locator import load_interface
from TBC.utility.Merger import merge_dicts
from TBC.utility.Numbers import significant_figures
from TBC.utility.SSH import SSH


def parse_args():
    """
    Parses arguments
    :return: the object returned by argparser
    """

    parser = argparse.ArgumentParser(description='A tool for benchmarking databases.')

    parser.add_argument('--master',
                        action='store_true',
                        default=False,
                        help='Use this flag if you want to set up a master node')

    parser.add_argument('--slave',
                        action='store_true',
                        default=False,
                        help='Use this flag if you want to set up a slave node')

    parser.add_argument('--port',
                        default=9999,
                        type=int,
                        help='Specify the port that this instance should listen to')

    parser.add_argument('--daemonize',
                        action='store_true',
                        default=False,
                        help='Run a slave node as a daemon.  Ignored for master nodes.')

    parser.add_argument('--bootstrap',
                        action='store_true',
                        default=False,
                        help='If this flag is included then start the trial-by-combat slave daemon on'
                             ' the slave nodes prior to running any benchmarks.')

    parser.add_argument('--load',
                        action='store_true',
                        default=False,
                        help='Include this flag when creating a master node in order to load a benchmark.'
                             '  Ignored if the created node is a slave node.')

    parser.add_argument('--run',
                        action='store_true',
                        default=False,
                        help='Include this flag when creating a master node in order to run a benchmark.'
                             '  Ignored if the created node is a slave node.  Can be used in combination'
                             ' with the --load flag.')

    parser.add_argument('--shutdown',
                        action='store_true',
                        default=False,
                        help='Including this flag when creating a master node will cause all slave nodes to '
                             'be terminated.  If included with --load or --run, slave nodes will terminate '
                             'after all operations have been completed.')

    parser.add_argument('--config',
                        nargs='+',
                        help='One or more configuration files. '
                             'Ignored if the created node is a slave node.')

    parser.add_argument('--csv',
                        action='store_true',
                        default=False,
                        help='If set then export the benchmark results to a .csv file')

    parser.add_argument('--graph',
                        action='store_true',
                        default=False,
                        help='If set then generate a series of graphs using matplotlib')

    parser.add_argument('--file-log-level',
                        default='info',
                        help='Set the log level for the logfile. Default is info. '
                             '(debug, info, warning, error, or critical)')

    parser.add_argument('--print-log-level',
                        default='info',
                        help='Set the log level for things that get printed to stdout. Default is info. '
                             '(debug, info, warning, error, or critical)')

    parser.add_argument('--purge-log',
                        action='store_true',
                        default=False,
                        help='If True then delete old log file if they have the same name as the new log files')

    parser.add_argument('--log-config',
                        action='store_true',
                        default=False,
                        help='If set then write benchmark configurations to disk')

    parser.add_argument('--path',
                        default='./',
                        help='Dump all files at this path')

    parser.add_argument('--log-name',
                        default=None,
                        help='The name of the trial (for record keeping purposes).'
                             '  If not provided a name will be generated.')

    parser.add_argument('--kill',
                        action='store_true',
                        default=False,
                        help='Using this flag will kill all trial-by-combat processes, including daemons. '
                             '(Note: this is a quick-and-dirty method, it simply searches for "trial-by-combat '
                             'and "trial_by_combat". If this string is not in the executable command then this '
                             'will not work.)')

    parser.add_argument('--setup-history',
                        action='store_true',
                        default=False,
                        help='If set and history information is included in the config then setup new history tables')

    parser.add_argument('--history',
                        nargs=3,
                        metavar=('BENCHMARK_ID', 'EVENT_ID', 'STATISTIC'),
                        help='Lookup the history for a benchmark and event.  Returns an error code of -1 if the'
                             ' most recent entry in the history is n%% worse than the average.')

    parser.add_argument('--history-threshold',
                        default=-0.1,
                        type=float,
                        help='The threshold at which the --history command will raise an error code.  Default is -0.1. '
                             'Negative numbers indicate a value lower than the average.')

    parser.add_argument('--history-max-age',
                        type=float,
                        help='The maximum age, in seconds, of benchmarks to consider with the --history command. '
                             'If not specified then all benchmarks are used.')

    parser.add_argument('--clean-history',
                        nargs=2,
                        metavar=('BENCHMARK_ID', 'MAX_AGE'),
                        help='Delete events in the history.  Age is specified in seconds.')

    return parser.parse_args()


_log_levels = {'debug': logging.DEBUG,
               'info': logging.INFO,
               'warning': logging.WARNING,
               'error': logging.ERROR,
               'critical': logging.CRITICAL}

_already_purged = False

def _setup_logging(file_log_level, print_log_level, log_name, logfile_name, purge=False):
    log_datadir = args.path + '/' + log_name
    log_datadir = os.path.expanduser(log_datadir.replace('//', '/'))
    if os.path.exists(log_datadir):
        global _already_purged
        if purge and not _already_purged:
            _already_purged = True
            shutil.rmtree(log_datadir)
            os.mkdir(log_datadir)
    else:
        os.mkdir(log_datadir)

    logger = logging.getLogger()
    logger.handlers = []
    logger.setLevel(logging.DEBUG)

    log_file_path = log_datadir + '/' + logfile_name

    fh = logging.FileHandler(log_file_path)
    fh.setLevel(_log_levels[file_log_level.lower()])
    fh.setFormatter(logging.Formatter('%(asctime)s (%(levelname)s): %(message)s'))
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setLevel(_log_levels[print_log_level.lower()])
    sh.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(sh)

    return logger


def run_master(args):
    master = None

    logger = _setup_logging(args.file_log_level,
                            args.print_log_level,
                            args.log_name,
                            'master_log.txt',
                            purge=args.purge_log)

    try:
        if args.config is None:
            raise Exception('You must include a configuration file.  Use the --config flag to do this.')

        master = TBCMaster(args.port,
                           args.config,
                           args.log_name,
                           log_config=args.log_config,
                           csv=args.csv,
                           graph=args.graph,
                           path=args.path,
                           setup_history=args.setup_history)

        for endpoint in args.config['nodes']:
            master.add_endpoint((endpoint['host'], int(endpoint['port'])))

        if not args.load and not args.run and not args.shutdown:
            print('Don\'t forget to specify --load, --run, --shutdown, or some '
                  'combination of these commands (or else this command doesn\'t do anything)')

        if args.load:
            master.load()
            logger.info('Loading data for benchmark %s', args.config['benchmark'])
            master.wait_for_load()
            logger.info('Loading finished')
        if args.run:
            logger.info('Running benchmark %s', args.config['benchmark'])
            master.run()
            logger.info('Gathering data')
            master.wait_for_run()
            logger.info('Benchmark finished')

    except:
        tb = traceback.format_exc()
        logger.critical(tb)

    finally:
        if master is not None:
            master.close(shutdown=args.shutdown)


def run_slave(args):
    if args.daemonize:
        if os.fork() != 0:
            os._exit(0)
        else:
            class NullDevice:
                def write(self, s):
                    pass

                def flush(self):
                    pass

            sys.stdin.close()
            sys.stdout = NullDevice()
            sys.stderr = NullDevice()

    logger = _setup_logging(args.file_log_level,
                            args.print_log_level,
                            args.log_name,
                            'slave_log.txt',
                            purge=args.purge_log)

    slave = None
    try:
        slave = TBCSlave(args.port)
        logger.info('Node online.  Waiting for commands from master.')
        slave.wait_until_finished()

    except:
        tb = traceback.format_exc()
        logger.critical(tb)

    finally:
        if slave is not None:
            slave.close()


def run_kill(args):
    my_pid = os.getpid()
    p = subprocess.Popen(['ps', '-ax'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    for line in out.splitlines():
        if line.find('trial-by-combat') != -1 or line.find('trial_by_combat') != -1:
            pid = int(line.split(None, 1)[0])
            if pid != my_pid:
                print 'killing %s' % line
                os.kill(pid, signal.SIGKILL)


def run_historian_clean(args):
    if args.config is None:
        raise Exception('You must include a configuration file.  Use the --config flag to do this.')

    historian = Historian(load_interface(args.config['history']['interface_id'],
                                         args.config['history']['interface_data']))

    historian.clean(args.clean_history[0], float(args.clean_history[1]))


def run_historian(args):
    logger = _setup_logging(args.file_log_level,
                            args.print_log_level,
                            args.log_name,
                            'historian_log.txt',
                            purge=args.purge_log)

    if args.config is None:
        raise Exception('You must include a configuration file.  Use the --config flag to do this.')

    benchmark_id = args.history[0]
    event = args.history[1]
    stat = args.history[2]

    historian = Historian(load_interface(args.config['history']['interface_id'],
                                         args.config['history']['interface_data']))

    max_age = None
    if args.history_max_age is not None:
        max_age = float(args.history_max_age)
    stats = historian.get_statistics_list(benchmark_id, event, stat, max_age=max_age)

    if len(stats) <= 1:
        logger.error('No historical data for this benchmark and stat')
        return
    most_recent = stats[-1]
    stats = stats[:-1]

    total = 0
    for value in stats:
        total += value
    average = float(total) / len(stats)

    logger.info('There were %d matching benchmarks. The average value of %s for %s (%s) is %s.' %
                (len(stats), stat, event, benchmark_id, str(average)))

    logger.info('The most recent value is %s' % str(most_recent))

    difference = most_recent - average
    fraction = difference / float(average)

    logger.info('Deviation from average: %s%%', str(significant_figures(fraction, 3) * 100))

    if fraction > 0 and args.history_threshold > 0 and fraction > args.history_threshold:
        logger.error('Deviation exceeds threshold')
        sys.exit(-1)
    elif fraction < 0 and args.history_threshold < 0 and fraction < args.history_threshold:
        logger.error('Deviation exceeds threshold')
        sys.exit(-1)


def bootstrap(args):

    logger = _setup_logging('critical', 'info', args.log_name, 'bootstrap.log')

    for node in args.config['nodes']:

        ssh = SSH(node['host'], node['user'], node['password'])
        # cmd = 'python /root/asdf.py'
        cmd = 'source /usr/share/virtualenvwrapper/virtualenvwrapper.sh; ' \
              'workon tbc; ' \
              'python ' + node['path'] + '/TBC/trial_by_combat.py --slave --daemon --port ' + str(node['port'])
        logger.info('Bootstrapping %s@%s' % (node['user'], node['host']))
        logger.info(cmd)
        ssh.send_command(cmd, block=False)


def main(args):
    if args.master and args.slave:
        raise Exception('--master and --slave cannot be used at the same time')

    if args.log_name is None:
        args.log_name = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-')

    if args.config is not None:
        config = {}
        for conf in args.config:
            if type(conf) is str:
                conf = yaml.load(open(conf))
            merge_dicts(config, conf)
        args.config = config

    # handle kill
    if args.kill:
        run_kill(args)

    # handle bootstrap
    if args.bootstrap:
        bootstrap(args)

    # handle master
    if args.master and not args.slave:
        run_master(args)

    # handle slave
    elif args.slave and not args.master:
        run_slave(args)

    # handle clean-history
    if args.clean_history is not None:
        run_historian_clean(args)

    # handle history
    if args.history is not None:
        run_historian(args)



class _args(object):
    pass


def run(master=False,
        slave=False,
        port=9999,
        daemonize=False,
        load=False,
        run=False,
        shutdown=False,
        config=None,
        csv=False,
        graph=False,
        file_log_level='info',
        print_log_level='info',
        purge_log=False,
        log_config=False,
        setup_history=False,
        path='./',
        log_name=None,
        kill=False,
        history=None,
        history_threshold=-0.1,
        history_max_age=None,
        clean_history=None):
    """
    A python interface with the same functionality as the command line interface.
    Execute 'trial_by_combat.py --help' for documentation.
    """
    args = _args()
    args.master = master
    args.slave = slave
    args.port = port
    args.daemonize = daemonize
    args.load = load
    args.run = run
    args.shutdown = shutdown
    args.config = config
    args.csv = csv
    args.graph = graph
    args.file_log_level = file_log_level
    args.print_log_level = print_log_level
    args.purge_log = purge_log
    args.log_config = log_config
    args.setup_history = setup_history
    args.path = path
    args.log_name = log_name
    args.kill = kill
    args.history = history,
    args.history_threshold = history_threshold,
    args.history_max_age = history_max_age,
    args.clean_history = clean_history
    main(args)


if __name__ == '__main__':
    args = parse_args()
    main(args)
