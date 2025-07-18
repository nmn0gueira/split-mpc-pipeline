#!/bin/bash

usage() {
    echo "Usage: $0 [-n <num_runs>] [-f] [-v] <command> [arguments...]"
}

num_runs=50
output_file="benchmark_results.txt"
total_time=0
valid_runs=0

force=false
verbose=false

> $output_file

while getopts "n:vf" opt; do
    case $opt in
        n)  num_runs=$OPTARG;;
        v)  verbose=true ;;
        f)  force=true ;;
        \?) echo "Invalid flag"; usage; exit 1 ;;
        :)  echo "Option -$opt requires an argument"; usage; exit 1 ;;
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
    
    execution_time=$(echo "$output" | grep -oP 'Time = \K[0-9.]+' | awk '{print $1 * 1000}') # Convert seconds to milliseconds as well
    
    if [ -n "$execution_time" ]; then
        total_time=$(echo "$total_time $execution_time" | awk '{print $1 + $2}')
        valid_runs=$((valid_runs + 1))
        last_successful_output="$output"
        run_msg="Run $i: $execution_time ms"
        
    else
        run_msg="Run $i: Error extracting time"
        if [ "$force" = true ]; then
            i=$((i - 1)) # Decrement i to repeat this run
        fi
    fi

    if [ "$verbose" = true ]; then
        echo "$run_msg"
    fi
    echo "$run_msg" >> $output_file
done


if [ $valid_runs -gt 0 ]; then
    avg_time=$(echo "$total_time $valid_runs" | awk '{print $1 / $2}')
    avg_time_msg="Average execution time: $avg_time ms"
    communication_msg=$(echo "$output" | grep 'sent =')
    echo "$avg_time_msg"
    echo "$communication_msg"
    echo "$avg_time_msg" >> $output_file
    echo "$communication_msg" >> $output_file
else
    echo "No valid runs completed." >> $output_file
fi

echo "Benchmark completed. Results saved in $output_file."