#!/usr/bin/env bash

# Is it compilable?
python -m py_compile main.py || exit 1

# Python3 readiness
#pylint --generate-rcfile > pylintrc
#pylint doorpi.py || exit 0
