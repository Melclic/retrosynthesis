#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

supervisord -c /home/supervisor.conf &
python3 /home/services.py
