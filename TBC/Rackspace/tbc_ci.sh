#!/usr/bin/env bash

set +x

path_to_tbc=$1 # the path to the trial-by-combat directory
conf=$1/conf # the location of the configuration files
db_interface=mysql_db.yaml # the name of the database interface file (generated)
nodes=nodes.yaml # the name of the nodes file (generated)
port=9999

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
workon tbc

# build all needed resources
python $path_to_tbc/TBC/Rackspace/InstanceBuilder.py $conf/api.yaml $conf/build_mysql.yaml $conf/build_nodes.yaml

# run the benchmark
python $path_to_tbc/TBC/trial_by_combat.py --master --port $port\
    --bootstrap --load --run --shutdown \
    --config $nodes $db_interface $conf/sysbench.yaml $conf/history.yaml \
    --log-config --csv --graph --path ~/tmp

# cleanup
python $path_to_tbc/TBC/Rackspace/Cleanup.py $conf/api.yaml $db_interface $nodes

# poll statistics
python $path_to_tbc/TBC/trial_by_combat.py \
    --config $conf/history.yaml \
    --history sysbench sysbench/Transaction average_throughput \
    --history-threshold -0.1 \
    --history-max-age 8640000 # 100 days
if [ $? -eq 0 ]; then
    echo 'Average throughput was acceptable.'
else
    echo 'Average throughput was too low.'
    exit 1
fi

python $path_to_tbc/TBC/trial_by_combat.py \
    --config $conf/history.yaml \
    --history sysbench sysbench/Transaction average_latency \
    --history-threshold 0.1 \
    --history-max-age 8640000 # 100 days
if [ $? -eq 0 ]; then
    echo 'Average latency was acceptable.'
else
    echo 'Average latency was too high.'
    exit 1
fi