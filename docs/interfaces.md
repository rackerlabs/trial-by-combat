[interface_locator]: https://github.com/rackerlabs/trial-by-combat/blob/master/TBC/interfaces/interface_locator.py

# Interfaces

Benchmarks should be written abstractly.  Instead of using the API for a specific database, instead use an abstract interface.  That way, anybody who wishes to use that benchmark for another database can simply implement the interface and use your benchmark without modification.

## Writing a new interface

Creating a new interface is simple.  Create a class that inherits the interface of your choice (look in trial-by-combat/TBC/interfaces) and implement all of its methods.

Don't forget to register your interface in trial-by-combat/TBC/interfaces/interface_locator.py