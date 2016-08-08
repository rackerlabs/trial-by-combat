# Configuration Files

[interaction_diagram]: ./interaction_diagram.png

Although Trial By Combat accepts many arguments via the command line, the core configuration for benchmarks is specified via .yaml configuration files.  A few notes on these configuration files:

* File names do not matter
* You may provide more than one .yaml file to any interface that is expecting a .yaml file.  These files will be merged before being consumed.
* It is ok if multiple config files overwrite the same value.  If multiple config files are included, the later files in the list overwrite duplicate values of files earlier in the list.
* The python API will accept either a YAML file or a python object (i.e. what you get when you do yaml.dump('my_config.yaml')).

![interaction_diagram]