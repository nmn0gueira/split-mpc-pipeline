#!/bin/bash


usage() {
    echo "Usage: $0 [-n <num_runs>] [-f] [-v] [-r <regex>] <command> [arguments...]"
    echo
    echo "  -n <num_runs>   Number of times to run the command (default: 50)"
    echo "  -f              Force re-run on error"
    echo "  -v              Verbose output"
    echo "  -r <regex>      Regex with named groups (?P<time>) and optionally (?P<unit>)"
    echo
    echo "If -r is not provided, total wall-clock time is measured externally."
}

convert_to_ms() {
    local value=$1
    local unit=$2
    case "$unit" in
        ms|msec|milliseconds|"") echo "$value" ;;
        s|sec|seconds) echo "$value" | awk '{print $1 * 1000}' ;;
        us|µs|microseconds) echo "$value" | awk '{print $1 / 1000}' ;;
        ns|microseconds) echo "$value" | awk '{print $1 / 1000000}' ;;
        *) echo "" ;;
    esac
}

num_runs=50
output_file="benchmark_results.txt"
total_time=0
valid_runs=0
force=false
verbose=false
time_regex=""

> $output_file

while getopts "n:vfr:" opt; do
    case $opt in
        n)  num_runs=$OPTARG;;
        v)  verbose=true ;;
        f)  force=true ;;
        r)  time_regex=$OPTARG ;;
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
if [ -n "$time_regex" ]; then
    echo "Using custom regex for time extraction"
fi

for ((i=1; i<=num_runs; i++)); do
    if [ -n "$time_regex" ]; then
        output=$("$@" 2>&1)
        time_and_unit=$(echo "$output" | perl -n -e "if (/$time_regex/) { print qq|\$+{time} \$+{unit}| }")
        time_value=$(echo "$time_and_unit" | awk '{print $1}')
        unit=$(echo "$time_and_unit" | awk '{print $2}')
        execution_time=$(convert_to_ms "$time_value" "$unit")
    else
        start=$(date +%s.%N)
        output=$("$@" 2>&1)
        end=$(date +%s.%N)
        execution_time=$(echo "$end - $start" | awk '{print $1 * 1000}')
    fi
    
    if [ -n "$execution_time" ]; then
        total_time=$(echo "$total_time $execution_time" | awk '{print $1 + $2}')
        valid_runs=$((valid_runs + 1))
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
    echo "$avg_time_msg"
    echo "$avg_time_msg" >> $output_file
    if [ "$verbose" = true ]; then
        echo "$output"
        echo "$output" >> $output_file
    fi
else
    echo "No valid runs completed." >> $output_file
fi

echo "Benchmark completed. Results saved in $output_file."