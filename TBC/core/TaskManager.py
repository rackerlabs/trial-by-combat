import inspect
import sys
import traceback
import Queue

from Task import *
from IProcMessage import IProcMessage

class TaskManager(object):
    """
    This class is responsible for running a task
    """

    def __init__(self, in_queue, out_queue, task_class, *args, **kwargs):
        """
        Start a new task manager
        :param out_queue: a queue for sending statistics back to the ProcessManager
        :param in_queue: a queue for receiving information from the ProcessManager
        :param task_class: a class type that inherits from Task
        """

        self.in_queue = in_queue
        self.out_queue = out_queue

        self.task = task_class(self, [])
        self.task._set_root(self)

        self.alive = True

    def start(self):
        try:
            self.task._run()
        except Exception as e:
            if self.out_queue is None:
                raise e
            else:
                m = IProcMessage('err', traceback.format_exc())
                self.out_queue.put(m)

    def _report(self, delta_t, failed, path):
        if self.out_queue is not None:
            m = IProcMessage('report', (path, delta_t, failed))
            self.out_queue.put(m)
        else:
            print (path, delta_t, failed)

    def handle_message(self, message):
        if message.type == "stop":
            self.close()
        else:
            m = IProcMessage('err', "TaskManager recieved unknown message type " + message.type)
            self.out_queue.put(m)

    def close(self):
        if self.alive:
            self.alive = False
            self.task._full_stop()

    def _check_in_queue(self):
        if not self.alive:
            return
        try:
            message = self.in_queue.get(block=False)
            self.handle_message(message)
        except Queue.Empty:
            pass

    def finish(self, depth):
        """
        Don't fail catastrophically, but warn the user that something strange happened.
        """
        sys.stderr.write('Warning: task attempted to tell it\'s task manager to finish. '
                         ' This happens if a task calls finish() with too large a depth.')

    def fail(self, depth):
        """
        Don't fail catastrophically, but warn the user that something strange happened.
        """
        sys.stderr.write('Warning: task attempted to tell it\'s task manager to fail. '
                         ' This happens if a task calls finish() with too large a depth.')
