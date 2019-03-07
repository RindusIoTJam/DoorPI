#!/usr/bin/env bash

# Is it compilable?
python -m py_compile doorpi.py || exit 1
#RC=$?; [[ $RC -ne 0 ]] && exit 1

# Python3 readiness
pylint --generate-rcfile > pylintrc
pylint doorpi.py || exit 0
