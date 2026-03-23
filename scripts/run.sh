#!/usr/bin/env bash

set -e

executable=$1
MP_SPDZ_PATH="MP-SPDZ"

usage() {
    echo "Script to run MP-SPDZ executables"
    echo "Example usages:"
    echo "Usage 1: $0 <protocol_script> <program_name> [<runtime_args>]"
    echo "Usage 2: $0 <protocol_binary> <party> <program_name> [<runtime_args>]"
}

while getopts ":h" opt; do
    case $opt in
        h)
            usage
            exit 1
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$executable" ]; then
    usage
    exit 1
fi

shift

cd $MP_SPDZ_PATH

if [[ "$executable" == *.sh ]]; then
    Scripts/"${executable}" "$@"

elif [[ "$executable" == *.x ]]; then
    ./"${executable}" "$@"
else
    echo "Unsupported executable format"
    usage
    exit 1
fi
