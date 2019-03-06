#!/usr/bin/env bash

# Is it compilable?
python -m py_compile doorpi.py

# Python3 readiness
pylint --generate-rcfile > pylintrc
pylint --py3k doorpi.py || true
