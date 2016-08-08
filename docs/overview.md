# Overview

[system_diagram]: ./system_diagram.png

Trial By Combat is a benchmarking suit designed for stress testing 
databases.  It provides the following features:

* Multithreaded and multi-node architecture
* Simulates many users performing potentially random activity
* Captures very fine grained performance statistics (configurable)
* Produces graphs, csvs, and other reports automatically
* Benchmarks are written abstractly.  Any benchmark written for MySQL 
can be ported to postgres, for example, by writing a small postgres 
interface.
* An API for writing benchmarks very similar to the Locust framework
* Bash CLI and python interface; both are equally supported and featured

![system_diagram]

Note: although a single database instance is shown in this diagram, it is possible to use trial-by-combat to benchmark a cluster of databases as well (via an appropriate interface). 