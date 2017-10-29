#!/bin/bash

apt-get install -y python2.7 python-pip python-setuptools python-matplotlib python-tk
pip install --upgrade pip
pip install pushbullet.py
chmod a+x ./gcode_gui.sh
