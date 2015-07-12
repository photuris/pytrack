#!/bin/bash

export PATH="/usr/local/bin:/opt/local/bin:$PATH"

# read yaml config file
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

. $DIR/parse_yaml.sh
eval $(parse_yaml $DIR/config.yml "config_")

# activate python environment
cd $config_paths_project
source venv/bin/activate

# run script
python track.py
