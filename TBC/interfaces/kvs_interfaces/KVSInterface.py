from TBC.interfaces.Interface import Interface

class KVSInterface(Interface):
    """
    A generic key-value store interface
    """

    def __init__(self):
        super(KVSInterface, self).__init__()

    def close(self):
        pass

    def exists(self, key):
        """
        This function returns True if the key exists, otherwise False
        """
        raise Exception('create_table is not implemented')

    def set(self, key, value):
        """
        Set the value for a particluar key
        """
        raise Exception('create_table is not implemented')

    def get(self, key):
        """
        Get the value stored at a key
        """
        raise Exception('create_table is not implemented')

    def rename(self, src, dst):
        """
        Rename a key
        :param src: the old name
        :param dst: the new name
        """
        raise Exception('create_table is not implemented')

    def multi_get(self, keys):
        """
        Get the values from multiple keys
        :param keys: a list of keys
        :return: a list of values (in the same order as the provided keys
        """
        result = []
        for key in keys:
            result.append(self.get(key))
        return result

    def multi_set(self, mapping):
        """
        Set multiple values
        :param mapping: a dictionary of keys and the values that they should be set to
        """
        for key, value in mapping:
            self.set(key, value)

    def delete_all(self):
        """
        Delete all keys in the database
        """
        raise Exception('delete_all is not implemented')

    def bulk_load(self, kv_generator):
        """
        A method that is used when a lot of things are being loaded into the database
        :param kv_generator: a generator that returns (key, value) tuples that need to be inserted
        """
        for key, value in kv_generator():
            self.set(key, value)