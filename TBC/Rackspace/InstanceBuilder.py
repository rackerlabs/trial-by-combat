import yaml
import multiprocessing
import time
import json
import os
import sys
import argparse

from TBC.Rackspace.ApiReq import ApiReq
from TBC.utility.SSH import SSH
from TBC.utility.Merger import merge_dicts
from TBC.utility.yaml_loader import *


def parse_args():
    """
    Parses arguments
    :return: the object returned by argparser
    """

    parser = argparse.ArgumentParser(description='This script spins up machines to be used by trial-by-combat')

    parser.add_argument('config',
                        nargs='+',
                        help='One or more configuration yaml files')

    return parser.parse_args()


class InstaceBuilder(object):

    def __init__(self, config):
        self.config = config
        if type(self.config) is str:
            self.config = yaml.load(open(config, 'r'))

        self.api = load_class_from_data(ApiReq, self.config['api'])
        self.rate_limiter = 5

        self.node_outfile = 'nodes.yaml'

        self.build_vms()
        self.build_databases()
        self.finish_database_builds()
        self.finish_vm_builds()

    def build_databases(self):
        if 'database_build_data' not in self.config:
            return
        self.database_procs = []
        self.database_info = multiprocessing.Queue()
        for db in self.config['database_build_data']:
            proc = multiprocessing.Process(target=self.build_database, args=[db])
            self.database_procs.append(proc)
            proc.start()

    def build_database(self, db):

        info = None

        instantce_type = None

        if db['build_type'].lower() == 'mysql':
            info = run_function_from_data(self.api.build_mysql, db)
            instantce_type = 'instance'
        elif db['build_type'].lower() == 'redis':
            info = run_function_from_data(self.api.build_redis, db)
            instantce_type = 'instance'
        elif db['build_type'].lower() == 'ha_mysql':
            info = run_function_from_data(self.api.build_ha_mysql, db)
            instantce_type = 'ha_instance'
        elif db['build_type'].lower() == 'ha_redis':
            info = run_function_from_data(self.api.build_ha_redis, db)
            instantce_type = 'ha_instance'
        else:
            raise Exception('Unknown build type %s', db['build_type'])

        # print json.dumps(info, indent=4) # fixme: temporary

        instance_id = str(info[instantce_type]['id'])

        interface_yaml = {
            'interface': {
                'id': db['interface_id'],
                'instance_id': instance_id,
                'data': {
                    'database': db['database_name']
                }
            }
        }

        if 'user' in db:
            interface_yaml['interface']['data']['user'] = db['user']

        for field in db['auxilary_interface_data']:
            interface_yaml['interface']['data'][field] = db['auxilary_interface_data'][field]

        if db['build_type'].lower() == 'mysql':
            interface_yaml['interface']['data']['password'] = db['password']
            interface_yaml['interface']['data']['url'] = str(info[instantce_type]['hostname'])
        elif db['build_type'].lower() == 'redis':
            interface_yaml['interface']['data']['password'] = info[instantce_type]['password']
            interface_yaml['interface']['data']['url'] = str(info[instantce_type]['hostname'])
        elif db['build_type'].lower() in ('ha_mysql', 'ha_redis'):
            pass # get the password and url later

        while True:
            time.sleep(self.rate_limiter)

            info = None

            if db['build_type'].lower() in ('mysql', 'redis'):
                info = self.api.show_database(instance_id)
            elif db['build_type'].lower() in ('ha_mysql', 'ha_redis'):
                info = self.api.show_ha_database(instance_id)

            # print json.dumps(info, indent=4) # fixme: temporary
            try:
                status = None
                if db['build_type'].lower() in ('mysql', 'redis'):
                    status = info[instantce_type]['status']
                elif db['build_type'].lower() in ('ha_mysql', 'ha_redis'):
                    status = info[instantce_type]['state']
            except:
                print 'Invalid message'
                continue

            print 'database %s\'s state is %s' % (db['name'], status)

            if status == 'ACTIVE':
                if db['build_type'].lower() in ('ha_mysql', 'ha_redis'):
                    interface_yaml['interface']['data']['password'] = str(info[instantce_type]['master_password'])
                    interface_yaml['interface']['data']['url'] = str(info[instantce_type]['addresses'][1]['address'])
                    interface_yaml['interface']['ha'] = True
                if db['build_type'].lower() == 'ha_mysql':

                    # find the instance ID of the master
                    master_id = None
                    if 'replica_of' in info['ha_instance']['nodes'][0]:
                        master_id = info['ha_instance']['nodes'][0]['replica_of']['id']
                    else:
                        master_id = info['ha_instance']['nodes'][0]['id']

                    self.api.create_mysql_database(master_id, db['user'])
                    self.api.create_mysql_user(master_id, db['user'], db['password'], db['database_name'])
                    interface_yaml['interface']['data']['password'] = db['password']
                    self.api.attach_ha_mysql_configuration(instance_id, db['configuration'])
                break

        fname = 'interface_' + db['name'] + '.yaml'
        if 'outfile' in db:
            fname = db['outfile']
        fobj = open(fname, 'w')
        yaml.dump(interface_yaml, fobj, default_flow_style=False)
        fobj.close()

    def finish_database_builds(self):
        if 'database_build_data' not in self.config:
            return
        for proc in self.database_procs:
            proc.join()
        print 'All databases have finished building'

    def build_vms(self):
        """
        Non-blocking.  Start the build process for all vms
        :return:
        """
        if 'vm_build_data' not in self.config:
            return
        if 'outfile' in self.config['vm_build_data']:
            self.node_outfile = self.config['vm_build_data']['outfile']
        self.vm_procs = []
        self.vm_info = multiprocessing.Queue()  # [(vm_id, admin_password, ip_address), ...]
        for vm_num in range(self.config['vm_build_data']['how_many']):
            proc = multiprocessing.Process(target=self.build_vm, args=[vm_num])
            self.vm_procs.append(proc)
            proc.start()

    def finish_vm_builds(self):
        if 'vm_build_data' not in self.config:
            return
        for proc in self.vm_procs:
            proc.join()
        print 'All VMs have finished building'
        self.write_node_data()

        print 'This script needs root permission to modify local firewalls.'
        for node in self.nodes['nodes']:
            command = 'sudo iptables -A INPUT -s %s -j ACCEPT' % node['host']
            print command
            os.system(command)

    def build_vm(self, vm_num):
        """
        Call this function in a process thread.  Will run until the VM is setup.
        :param vm_num: Used to name the VM
        """

        self.config['vm_build_data']['config']['name'] = self.config['vm_build_data']['config']['base_name'] + \
                                                         str(vm_num)

        boot_info = run_function_from_data(self.api.boot, self.config['vm_build_data']['config'])
        try:
            vm_id = boot_info['server']['id']
        except:
            print 'unable to boot server'
            print boot_info
            return
        admin_password = boot_info['server']['adminPass']
        ip_address = None

        while True:
            time.sleep(self.rate_limiter)

            info = self.api.show_server(vm_id)
            try:
                status = info['server']['status']
            except:
                print 'Invalid message'
                continue

            print 'server %d\'s state is %s' % (vm_num, status)

            if status == 'ACTIVE':
                ip_address = info['server']['accessIPv4']
                #print 'server %d is active'
                #print json.dumps(info, indent=4)
                break

        self.vm_info.put((str(vm_id), str(admin_password), str(ip_address)))

        self.install(ip_address, admin_password)

    def install(self, ip, password):
        """
        This funcition is responsible for setting up trial-by-combat on each node
        """

        ssh = None
        while True:
            try:
                print 'Attempting to connect to server at %s' % ip
                ssh = SSH(ip, 'root', password)
                break
            except Exception as e:
                print e
                print '\tServer %s not accepting ssh connections yet' % ip
                time.sleep(self.rate_limiter)

        # copy files to target
        self.config['vm_build_data']['source_dir'] = os.path.expanduser(self.config['vm_build_data']['source_dir'])
        ssh.send_directory(os.path.expanduser(self.config['vm_build_data']['source_dir']), '/root/trial-by-combat')

        # run instalation script
        ssh.send_command('bash /root/trial-by-combat/install.sh /root/trial-by-combat')

        # open firewall
        ssh.send_command('iptables -A INPUT -s %s -j ACCEPT' % self.config['vm_build_data']['master_ip'])


    def write_node_data(self):
        """
        Write information to yaml file
        """

        self.nodes = {'nodes':[]}
        while not self.vm_info.empty():
            vm_id, vm_password, vm_ip = self.vm_info.get()
            self.nodes['nodes'].append({'id': vm_id,
                                  'password': vm_password,
                                  'host': vm_ip,
                                  'port': 9999,
                                  'user': 'root',
                                  'path': '/root/trial-by-combat'})
        fobj = open(self.node_outfile, 'w')
        yaml.dump(self.nodes, fobj, default_flow_style=False)
        fobj.close()


class _args(object):
    pass


def run(config, output_file='nodes.yaml'):
    args = _args()
    args.config = config
    args.o = output_file
    main(args)


def main(args):
    config = {}
    for conf in args.config:
        if type(conf) is str:
            conf = yaml.load(open(conf))
        merge_dicts(config, conf)
    args.config = config

    ib = InstaceBuilder(config)


if __name__=='__main__':
    args = parse_args()
    main(args)