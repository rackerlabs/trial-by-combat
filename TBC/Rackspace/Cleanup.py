import yaml
import sys
import os
import argparse

from TBC.Rackspace.ApiReq import ApiReq
from TBC.utility.Merger import merge_dicts
from TBC.utility.yaml_loader import *


def parse_args():
    """
    Parses arguments
    :return: the object returned by argparser
    """

    parser = argparse.ArgumentParser(description='This cleans up machines that were used by trial-by-combat')

    parser.add_argument('config',
                        nargs='+',
                        help='One or more configuration yaml files')

    return parser.parse_args()

class Cleanup(object):

    def __init__(self, config):
        self.config = config
        if type(self.config) is str:
            self.config = yaml.load(open(config, 'r'))

        self.api = load_class_from_data(ApiReq, self.config['api'])

        self.shutdown_nodes()
        self.shutdown_databases()
        self.close_firewall()


    def shutdown_nodes(self):
        if 'nodes' in self.config:
            for node in self.config['nodes']:
                self.api.delete_server(node['id'])
        print 'all nodes have been destroyed'

    def shutdown_databases(self):

        if 'interface' in self.config:
            self.shutdown_database(self.config['interface'])

        if 'interfaces' in self.config:
            for interface in self.config['interfaces']:
                self.shutdown_database(interface)

        print 'all databases have been destroyed'

    def shutdown_database(self, db):
        if 'ha' in db and db['ha']:
            self.api.delete_ha_database(db['instance_id'])
        else:
            self.api.delete_database(db['instance_id'])

    def close_firewall(self):
        if 'nodes' in self.config:
            print 'This script needs root permission to modify local firewalls.'
            for node in self.config['nodes']:
                command = 'sudo iptables -A INPUT -s %s -j DROP' % node['host']
                print command
                os.system(command)
        print 'firewall exceptions closed'


class _args(object):
    pass


def run(config):
    args = _args()
    args.config = config
    main(args)


def main(args):
    config = {}
    for conf in args.config:
        if type(conf) is str:
            conf = yaml.load(open(conf))
        merge_dicts(config, conf)
    args.config = config

    ib = Cleanup(config)


if __name__=='__main__':
    args = parse_args()
    main(args)