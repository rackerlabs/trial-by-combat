# Python API

The python API for Trial By Combat is fully featured and can do everything the BASH CLI is able to do.  

~~~~
from TBC.trial_by_combat import run
run(master=True, config=['configuration1.yaml', 'configuration2.yaml], ...)
~~~~

Note: where as the bash CLI expects .yaml files, the Python API will accept both .yaml files and python objects (i.e. what you get when you run yaml.load() on a .yaml file).