from distutils.core import setup

setup(
    name='trial-by-combat',
    version='0.1.0',
    packages=[
        'TBC',
        'TBC.core',
        'TBC.types',
        'TBC.utility',
        'TBC.benchmarks',
        'TBC.benchmarks.kvs',
        'TBC.benchmarks.kvs.RandomRW',
        'TBC.benchmarks.sql',
        'TBC.benchmarks.sql.RandomTransactions',
        'TBC.benchmarks.sql.sysbench',
        'TBC.interfaces',
        'TBC.interfaces.kvs_interfaces',
        'TBC.interfaces.sql_interfaces',
        'TBC.Rackspace'
    ],
    url='',
    license='http://www.apache.org/licenses/LICENSE-2.0',
    author='Cody Littley, Rackspace',
    author_email='',
    description='A database benchmarking utility.',
    install_requires=[
        'matplotlib',
        'MYSQL-python',
        'PyYAML',
        'redis',
        'requests',
        'network-cjl==0.0.0'
    ],
    dependency_links=[
        'https://github.com/littley/network_cjl/tarball/master#egg=network-cjl-0.0.0'
    ]
)
