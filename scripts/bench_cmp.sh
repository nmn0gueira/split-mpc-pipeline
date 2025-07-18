#!/bin/bash
set -e

usage() {
    echo "Usage: $0 [-n <num_runs>] [-v] <command> [arguments...]"
}

num_runs=50
output_file="benchmark_results.txt"
total_time=0
valid_runs=0

verbose=false

> $output_file

while getopts "n:v" opt; do
    case $opt in
        n)  num_runs=$OPTARG;;
        v)  verbose=true ;;
        \?) echo "Invalid flag"; usage; exit 1 ;;
        :)  echo "Option -$OPTARG requires an argument"; usage; exit 1 ;;
    esac
done

shift $((OPTIND -1))

if [ $# -lt 1 ]; then
    usage
    exit 1
fi


echo "Number of runs: $num_runs"

for ((i=1; i<=num_runs; i++))
do
    output=$("$@" 2>&1)
    
    execution_time=$(echo "$output" | grep -oP 'time: \K[0-9.]+' | awk '{print $1 * 1000}') # Convert seconds to milliseconds as well
    
    if [ -n "$execution_time" ]; then
        total_time=$(echo "$total_time $execution_time" | awk '{print $1 + $2}')
        valid_runs=$((valid_runs + 1))
        run_msg="Run $i: $execution_time ms"
        
    else
        run_msg="Run $i: Error extracting time"
    fi

    if [ "$verbose" = true ]; then
        echo "$run_msg"
    fi
    echo "$run_msg" >> $output_file
done


if [ $valid_runs -gt 0 ]; then
    avg_time=$(echo "$total_time $valid_runs" | awk '{print $1 / $2}')
    avg_time_msg="Average compilation time: $avg_time ms"
    echo "$avg_time_msg"
    echo "$avg_time_msg" >> $output_file
else
    echo "No valid runs completed." >> $output_file
fi

echo "Benchmark completed. Results saved in $output_file."