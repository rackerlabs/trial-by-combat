import random
import inspect

from TBC.core.Tasklet import Tasklet

class Task(Tasklet):
    """
    An aggregate of one or more Tasklets
    """

    def __init__(self, parent, path):
        super(Task, self).__init__(parent, path)

        self._tasklets = self._gather_tasklets()
        self._next_tasklet = None
        self._total_weight = 0
        for tasklet in self._tasklets:
            self._total_weight += tasklet.weight

    def _gather_tasklets(self):
        """
        Uses introspection to fund all nested tasklets
        :return: a list of Tasklets instantiated from the nested tasklets
        """
        tasklets = []
        for key in self.__class__.__dict__:
            obj = self.__class__.__dict__[key]
            if inspect.isclass(obj) and issubclass(obj, Tasklet):
                tasklets.append(obj(self, self._path[:]))
        if len(tasklets) == 0:
            raise Exception('A task must have at least one tasklet')
        return tasklets

    def _find_tasklet(self, name):
        """
        Given a tasklet name, return the corresponding Tasklet object
        """
        for tasklet in self._tasklets:
            if tasklet.name == name:
                return tasklet
        raise IndexError('Task has no Tasklet named %s' % name)

    def _choose_tasklet(self):
        """
        Randomly select an operation to perform (unless one has already been chosen)
        :return: an Operation
        """
        if self._next_tasklet is not None:
            op = self._next_tasklet
            self._next_tasklet = None
            return op
        choice = random.uniform(0, self._total_weight)
        upto = 0.0
        for op in self._tasklets:
            if upto + op.weight >= choice:
                return op
            else:
                upto += op.weight

    def _full_stop(self):
        """
        Stop everything (still allows on_end to be called)
        """
        self._active = False
        for tasklet in self._tasklets:
            if issubclass(tasklet.__class__, Task):
                tasklet._full_stop()

    def _check_in_queue(self):
        """
        Only do work on leaf Tasklets
        """
        pass

    def _set_root(self, root):
        self._root = root
        for tasklet in self._tasklets:
            tasklet._set_root(root)

    def set_client(self, client):
        self.client = client
        for tasklet in self._tasklets:
            tasklet.set_client(client)

    def _set_next_task(self, path):
        """
        Specify which tasklet should be executed next
        :param path: a list of tasklet names.  Used to specify sub-tasks of tasklets
        """
        self._next_tasklet = self._find_tasklet(path[0])
        if len(path) > 1:
            self._next_tasklet._set_next_task(path[1:])

    def jump(self, path):
        if type(path) is str:
            path = path.split('/')

        if path[0] == '':
            if self is not self._root.task:
                self._active = False
            self._root.task.jump(path[1:])  # Note: _root is not actually a task, but _root.task is
        elif path[0] == '.':
            self.jump(path[1:])
        elif path[0] == '..':
            self._active = False
            self.parent.jump(path[1:])
        else:
            self._set_next_task(path)
            pass

    def operation(self):
        """
        Perform tasklets until finished (i.e. not self._active)
        """
        while self._active:
            op = self._choose_tasklet()
            op._run()
