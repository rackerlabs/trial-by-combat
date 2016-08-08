#!/usr/bin/env bash

# This script will set up trial-by-combat on a clean ubuntu 16.04 installation

echo about to start installing!

set -x

sudo apt-get update
sudo apt-get -y install git libfreetype6-dev libxft-dev python-pip libmysqlclient-dev libssl-dev virtualenv virtualenvwrapper sshpass

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
mkvirtualenv tbc

pip --no-cache-dir install $1 --process-dependency-links

set +x

echo finished installing