#!/usr/bin/env bash

PYTHON_BIN=/usr/bin/python2.7

function die {
    echo "$1"
    exit 1
}

VENV_DIR=$(test "_$1" == "_" && echo "venv" || echo "$1")

echo -n "checking 'virtualenv': "
which virtualenv || die "no 'virtualenv' found, try 'sudo pip install virtualenv' (exiting)"

echo -n "checking '${VENV_DIR}': "
test -d ${VENV_DIR} && die "already there (exiting)"
echo "not existing (good)"

virtualenv -p  ${PYTHON_BIN} ${VENV_DIR} || die "failed to create environment (exiting)"
virtualenv --relocatable ${VENV_DIR}

source ${VENV_DIR}/bin/activate || die "failed to activate environment (exiting)"
pip install -r requirements.txt

echo "Done, activate venv with 'source ${VENV_DIR}/bin/activate'"
