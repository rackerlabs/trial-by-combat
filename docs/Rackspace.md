# Rackspace Specific Scripts

[TBC/Rackspace]: https://github.com/rackerlabs/trial-by-combat/tree/master/TBC/Rackspace
[InstanceBuilder.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/Rackspace/InstanceBuilder.py
[Cleanup.py]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/Rackspace/Cleanup.py

Trial By Combat was originally written for internal use in Rackspace.  Scripts in [TBC/Rackspace] can be used to create and destroy cloud servers and database instances in conjunction with Trial By Combat.  If you are not using Rackspace infrastructure then you may safely ignore [TBC/Rackspace].

## Creating and destroying instances quickly

### InstanceBuilder.py

[InstanceBuilder.py] expects one or more configuration files.  There are no other arguments for this script.

~~~~
python InstanceBuilder.py config1.yaml config2.yaml ... configN.yaml
~~~~

#### API configuration (.yaml)

This allows the script to spawn cloud servers and databases.  It is required by [InstanceBuilder.py].

~~~~
api:
    user: <insert user here>
    api_key: <insert API key here>
    identity_url: https://identity.api.rackspacecloud.com/v2.0
    datacenter: <insert datacenter here>
~~~~

#### Cloud server configuration (.yaml)

This configuration file may optionally be passed to [InstanceBuilder.py]. If included, it will allow the InstanceBuilder to spin up virtual machines.

~~~~
vm_build_data:
    config:
        image: <insert image identifier here>
        flavor: <insert flavor here>
        base_name: benchmark-                        # will create benchmark-0, benchmark-1, etc.
    how_many: 1                                      # the number of cloud servers to create
    source_dir: path/to/trial-by-combat              # this will be copied over to the nodes
    master_ip: <master IP address>                   # needed to open doorways in firewalls
    outfile: nodes.yaml                              # information about the nodes is dumped here
~~~~

#### Database Configuration (.yaml)

This configuration file may optionally be passed to [InstanceBuilder.py].  If included, it will allow the InstanceBuilder to spin up databases.  The example below shows will cause InstanceBuilder to spin up 4 databases: a redis instace, a ha-redis instance, a mysql instance, and a ha-mysql instance.

~~~~
database_build_data:
    - build_type: redis
      version: '3.0.7'
      flavor: '102'
      name: redis_benchmark_db
      database_name: benchmark
      interface_id: redis
      auxilary_interface_data:
          port: 6379
          client: StrictRedis
          database: 0
          debug: False
      outfile: redis_db.yaml
    - build_type: ha_redis
      version: '3.0.7'
      flavor: '102'
      nodes: 2
      name: redis_benchmark_db
      database_name: benchmark
      interface_id: redis
      auxilary_interface_data:
          port: 6379
          client: StrictRedis
          database: 0
          debug: False
      outfile: ha_redis_db.yaml
    - build_type: mysql
      version: '5.6'
      flavor: '1'
      size: 1
      name: mysql_benchmark_db
      database_name: benchmark
      user: benchmark
      password: guest
      configuration: <insert configuration id>       # this is an optional argument
      interface_id: MySQL
      auxilary_interface_data:
          port: 3306
          debug_queries: False
          debug_responses: False
      outfile: mysql_db.yaml
    - build_type: ha_mysql
      version: '5.6'
      flavor: '2'
      nodes: 2
      size: 1
      user: benchmark
      password: guest
      configuration: <insert configuration id>
      name: ha_mysql_benchmark_db
      database_name: benchmark
      interface_id: MySQL
      auxilary_interface_data:
          port: 3306
          debug_queries: False
          debug_responses: False
      outfile: ha_mysql_db.yaml
~~~~

### Cleanup.py

[Cleanup.py] expects one or more configuration files (described below).  There are no other arguments for this script.

#### API configuration (.yaml)

This file is required by [Cleanup.py].  This should be the same API configuration used by [InstanceBuilder.py]

~~~~
api:
    user: <insert user here>
    api_key: <insert API key here>
    identity_url: https://identity.api.rackspacecloud.com/v2.0
    datacenter: <insert datacenter here>
~~~~

#### VM and Database configuration (.yaml)

These files are optional.  [InstanceBuilder.py] generates several YAML files.  If any of these resulting YAML files are passed to [Cleanup.py] then the resources described within will be released.

