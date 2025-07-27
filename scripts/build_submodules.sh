#!/bin/bash

set -euo pipefail

modules_to_build=()
clean_build=false
verbose=false

declare -A available_modules=(
    [kunlun]="An OpenSSL wrapper containing an implementation of Private-ID protocol in CZZ24"
    [volepsi]="A repository including PSI and Circuit-PSI protocol implementation of RR22"
    [privateid]="A collection of algorithms to match records between two or more parties. Among them are the original Private-ID protocol and PS3I protocol from BKM+20"
)

usage() {
    cat <<EOF
Usage: $0 [--modules <module1,module2,...>] [options]

Build Options:
  --modules <module1,...>        Comma-separated list of modules to build (default: all)
                                 Available modules: ${!available_modules[@]}
  --clean                        Clean build artifacts before building
  --verbose                      Enable verbose output

Other Options:
  --list-modules                 List available modules and exit
  -h, --help                     Show this help and exit
EOF
    exit 1
}

vlog() {
    if $verbose; then
        echo "[verbose] $@"
    fi
}

list_modules() {
    echo "Available modules:"
    for module in "${!available_modules[@]}"; do
        printf "  %-20s %s\n" "$module" "${available_modules[$module]}"
    done
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        key="$1"
        case $key in
            --modules)
                IFS=',' read -ra modules_to_build <<< "$2"
                shift 2
                ;;
            --list-modules)
                list_modules
                ;;
            --clean)
                clean_build=true
                shift
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --debug)
                set -x
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                echo "Invalid argument: $1"
                usage
                ;;
        esac
    done

    if [[ ${#modules_to_build[@]} -eq 0 ]]; then
        modules_to_build=("${!available_modules[@]}")
    fi
}

build_kunlun() (
    if [[ -z "$(find match/Kunlun -mindepth 1 -print -quit)" ]]; then
        vlog "Initializing Kunlun submodule..."
        git submodule update --init -- match/Kunlun
    fi
    vlog "Building Kunlun module"
    cd match/Kunlun
    vlog "Running OpenSSL installer"
    ./install_openssl.sh
    mkdir -p build
    cd build
    vlog "Running cmake"
    cmake ..
    vlog "Running make"
    make
)

build_volepsi() (
    if [[ -z "$(find match/volepsi -mindepth 1 -print -quit)" ]]; then
        vlog "Initializing volepsi submodule..."
        git submodule update --init -- match/volepsi
    fi
    vlog "Building volepsi module"
    cd match/volepsi
    python3 build.py -DVOLE_PSI_ENABLE_BOOST=ON #--par=1
)


build_privateid() (
    if [[ -z "$(find match/Private-ID -mindepth 1 -print -quit)" ]]; then
        vlog "Initializing Private-ID submodule..."
        git submodule update --init -- match/Private-ID
    fi
    vlog "Building Private-ID module"
    cd match/Private-ID
    cargo build --release
)


build_modules() {
    for module in "${modules_to_build[@]}"; do
        if [[ -n "${available_modules[$module]}" ]]; then
            echo "Building module: $module (${available_modules[$module]})"
            if [[ $(type -t "build_$module") == function ]]; then
                "build_$module"
            else
                echo "Warning: No build function for module '$module'"
            fi
        else
            echo "Warning: Unknown module '$module' - skipping"
        fi
    done
}

clean_modules() {
    for module in "${modules_to_build[@]}"; do
        echo "Cleaning module: $module"
        case $module in
            kunlun)
                rm -rf match/Kunlun/build
                ;;
            volepsi)
                rm -rf match/volepsi/build
                ;;
            private-id)
                cargo clean --manifest-path match/Private-ID/Cargo.toml
                ;;
        esac
    done
}

main() {
    parse_args "$@"
    echo "Modules to build: ${modules_to_build[@]}"
    
    if $clean_build; then
        clean_modules
    fi

    build_modules
    echo "Modules built successfully."
}

main "$@"