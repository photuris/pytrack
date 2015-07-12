#!/bin/bash

export PATH="/usr/local/bin:/opt/local/bin:$PATH"

# read yaml config file
. parse_yaml.sh
eval $(parse_yaml config.yml "config_")

# activate python environment
cd $config_paths_project
source venv/bin/activate

# run script
python track.py
