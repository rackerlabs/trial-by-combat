import time

class Tasklet(object):
    """
    The base unit of work
    """

    name = None
    weight = 1.0
    report_stats = True

    def __init__(self, parent, path):
        self.parent = parent
        self._root = None
        if self.name is None:
            self.name = self.__class__.__name__
        self._path = path
        self._path.append(self.name)

        self.client = None

        self._active = False
        self._failed = False

    def operation(self):
        """
        This function gets executed when it is time to execute the Tasklet
        :return:
        """
        raise Exception('Tasklet \'' + self.name + '\' has no operation function defined')

    def on_start(self):
        """
        This function is called right before the execution of this Tasklet
        """
        pass

    def on_end(self):
        """
        This function is called right after the execution of this Tasklet
        """
        pass

    def _report(self, time, failed):
        """
        This funciton is used to pass statistics about an operation up to the manager
        :param time: the time that it took to perform this operation
        :param path: the 'path' of the operation, uniquely identifies the operation
        """
        self._root._report(time, failed, self._path)

    def _check_in_queue(self):
        """
        This should be called after EVERY tasklet... it briefly yields control so that message queues can be monitored
        """
        self._root._check_in_queue()

    def finish(self, depth=1):
        """
        This function should be called to end the execution of a particular Tasklet.
        :param depth: A depth of 1 will also end the execution of the parent task, 2 will end the grandparent, etc.
        """
        self._active = False
        depth -= 1
        if depth >= 0:
            self.parent.finish(depth)

    def fail(self, depth=0):
        """
        Call this function to signal that a Tasklet has failed.  Tasklets that do not call fail are assumed to
        have succeeded.  Calling fail will also cause the Tasklet to be finished
        :param depth: use depth to cause a parent tasklet to also fail.  Depth=1 causes parent to fail, depth=2
                        causes grandparent to fail, etc.
        """
        self._active = False
        self._failed = True
        depth -= 1
        if depth >= 0:
            self.parent.fail(depth)

    def jump(self, path):
        """
        Call this function to schedule the execution of another tasklet.  The specified tasklet will be executed
        once the current tasklet ends.
        :param path: a string equal to the name of the tasklet that should be executed next.  Can specify paths.
                        Uses a syntax for paths similar to file paths.  Each Task is a directory, each tasklet is a
                        file.  For example, '../taskB' specifies a subtask of the task in a level above.
                        '/taskX/taskY' specifies a tasklet relative to the root task.

        """
        self.parent.jump(path)  # If this is called on a generic Tasklet then pass it to the parent Task

    def set_client(self, client):
        """
        Sets the client
        :param client:
        :return:
        """
        self.client = client

    def _set_root(self, root):
        """
        Specify the object (probably a TaskManager) that has the root _report and _check_in_queue functions
        This is to save several function calls each time a leaf Tasklet calls one of these functions
        :param root: the root object
        """
        self._root = root

    def _run(self):
        self._active = True
        self._failed = False
        start_time = time.time()
        self.on_start()
        if not self._failed:
            self.operation()
        if not self._failed:
            self.on_end()
        end_time = time.time()
        delta_time = end_time - start_time
        if self.report_stats:
            self._report(delta_time, self._failed)
        else:
            self.operation()
        self._check_in_queue()
