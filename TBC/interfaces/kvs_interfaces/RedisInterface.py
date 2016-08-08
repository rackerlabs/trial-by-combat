import redis

from TBC.interfaces.kvs_interfaces.KVSInterface import KVSInterface

class RedisInterface(KVSInterface):

    def __init__(self, url, port, database, password, client, debug=False):
        super(RedisInterface, self).__init__()

        if client == 'Redis':
            self.redis = redis.Redis(host=url, port=port, db=database, password=password)
        elif client == 'StrictRedis':
            self.redis = redis.StrictRedis(host=url, port=port, db=database, password=password)
        else:
            raise Exception('Unknown client ' + client)

        self.debug = debug

    def close(self):
        pass # fixme: does self.redis need to be closed?

    def exists(self, key):
        self.redis.exists(key)

    def set(self, key, value):
        self.redis.set(key, value)

    def get(self, key):
        return self.redis.get(key)

    def rename(self, src, dst):
        self.redis.rename(src, dst)

    def multi_get(self, keys):
        return self.redis.mget(keys)

    def multi_set(self, mapping):
        self.redis.mset(mapping)

    def delete_all(self):
        self.redis.flushdb()

    def bulk_load(self, kv_generator):
        pipeline = self.redis.pipeline(transaction=False)
        things_in_pipeline = 0
        max_things_in_pipeline = 1000
        for key, value in kv_generator():
            pipeline.set(key, value)
            things_in_pipeline += 1
            if things_in_pipeline >= max_things_in_pipeline:
                pipeline.execute()
                things_in_pipeline = 0
