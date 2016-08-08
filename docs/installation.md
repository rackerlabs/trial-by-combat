# Installation

[github]: https://github.com/rackerlabs/trial-by-combat
[install.sh]: https://github.com/rackerlabs/trial-by-combat/blob/master/install.sh

First, clone the repository. Trial by combat currently lives at [github].
An installation script ([install.sh]) has been included.  This script has been tested on Ubuntu 16.04.  This script creates and installs into a virtualenv called 'tbc'.

~~~~
install.sh path/to/trial-by-combat
~~~~

## Manual Installation

To install manually, first ensure that the following packages (or equivalent) are installed:

~~~~
libfreetype6-dev libxft-dev python-pip libmysqlclient-dev libssl-dev sshpass
~~~~

Next, run the following:

~~~~
pip --no-cache-dir install path/to/trial-by-combat --process-dependency-links
~~~~