#!/bin/bash

set -e

protocol=$1
MP_SPDZ_PATH="MP-SPDZ"

usage() {
    echo "Usage 1: $0 <protocol_script> <program_name> [<runtime_args>]"
    echo "Usage 2: $0 <protocol_binary> <party> <program_name> [<runtime_args>]"
}

if [ -z "$protocol" ]; then
    usage
    exit 1
fi

shift

cd $MP_SPDZ_PATH

if [[ "$protocol" == *.sh ]]; then   # If a protocol script is specified we execute it as such (which in turn executes it in localhost)
    if [ -z "$1" ]; then
        usage
        exit 1
    fi
    Scripts/${protocol} "$@"
else
    if [ -z "$1" ] || [ -z "$2" ]; then
        usage
        exit 1
    fi
    ./$protocol "$@"
fi
