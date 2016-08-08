import os
import sys
import subprocess

class SSH:

    def __init__(self, address, username, password):

        self.username = username
        self.password = password
        self.address = address

        # check the validity of the connection
        command = ['sshpass', '-p' + self.password,
                   'ssh', '-o', 'StrictHostKeyChecking=no',
                   self.username + '@' + self.address, ':']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        print 'out', out, 'err', err
        sys.stdout.flush()

        bad_string = 'Connection refused'
        if bad_string in out or bad_string in err:
            raise Exception('Cannot connect to %s@%s using the given password' % (username, address))

    def send_command(self, command, block=True):
        full_command = ['sshpass', '-p' + self.password,
                        'ssh', '-o', 'StrictHostKeyChecking=no',
                        self.username + '@' + self.address, command]
        print ' '.join(full_command)
        p = subprocess.Popen(full_command)
        if block:
            p.communicate()


    def send_file(self, source, destination, block=True):
        """
        Send a file
        :param source: the file to be sent
        :param destination: the file path where the file should be saved.  Do not specify a directory, include
                                the full path including the name of the file
        """
        command = ['sshpass', '-p' + self.password,
                   'scp', '-o', 'StrictHostKeyChecking=no',
                   source, self.username + '@' + self.address + ':' + destination]
        print ' '.join(command)
        p = subprocess.Popen(command)
        if block:
            p.communicate()

    def send_directory(self, source, destination, block=True):
        """
        Recursively send a directory
        :param source: the directory to be sent
        :param destination: the file path where the directory should be saved.
        """
        command = ['sshpass', '-p' + self.password,
                   'scp', '-o', 'StrictHostKeyChecking=no', '-r',
                   source, self.username + '@' + self.address + ':' + destination]
        print ' '.join(command)
        p = subprocess.Popen(command)
        if block:
            p.communicate()
