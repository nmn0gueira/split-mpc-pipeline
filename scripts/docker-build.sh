#!/bin/bash

set -e

IMAGE_NAME="mpspdz"
DOCKERFILE_PATH="Dockerfile"
BUILD_CONTEXT="."

TARGET="program"

declare -A BUILD_ARGS=(
    [arch]="native"
    [cxx]="clang++-11"
    [use_ntl]=1
    [prep_dir]="Player-Data"
    [ssl_dir]="Player-Data"
    [cryptoplayers]=3
    [machine]=""
    [gfp_mod_sz]=2
    [ring_size]=256
    [src]=""
    [compile_options]=""
)


usage() {
    cat <<EOF
Usage: $0 [--target <target>] [options]

Build Targets:
  --target buildenv              Build base environment
  --target machine               Build machine-specific image (requires --machine)
  --target program               Build complete program (default, requires --machine, --src)

Dockerfile Arguments:
  --arch <arch>                   Architecture (default: native)
  --cxx <compiler>                C++ compiler (default: clang++-11)
  --use_ntl <0|1>                 Use NTL (default: 1)
  --prep_dir <dir>                Prep directory (default: Player-Data)
  --ssl_dir <dir>                 SSL directory (default: Player-Data)
  --cryptoplayers <num>           Crypto players (default: 3)
  --machine <machine>             Target machine
  --gfp_mod_sz <size>             GF(p) mod size (default: 2)
  --ring_size <size>              Ring size (default: 256)
  --src <src>                     Source file name (excluding ".py")
  --compile_options <options>     Compilation options

Other Options:
  -h, --help                      Show this help and exit
EOF
    exit 1
}


parse_args() {
    while [[ $# -gt 0 ]]; do
        key="$1"
        case $key in
            --target)
                TARGET="$2"
                shift
                ;;
            --*)
                arg_name="${key#--}"
                if [[ ${BUILD_ARGS[$arg_name]+_} ]]; then
                    BUILD_ARGS[$arg_name]="$2"
                    shift
                else
                    echo "Unknown option: $key"
                    usage
                fi
                ;;
            -h|--help)
                usage
                ;;
            *)
                echo "Invalid argument: $1"
                usage
                ;;
        esac
        shift
    done
}


validate_args() {
    case "$TARGET" in
        buildenv)
            IMAGE_TAG="buildenv"
            ;;
        machine)
            if [[ -z "${BUILD_ARGS[machine]}" ]]; then
                echo "Error: --machine is required for building machine stage."
                usage
            fi
            IMAGE_TAG="${BUILD_ARGS[machine]}"
            BUILD_ARGS[machine]="${BUILD_ARGS[machine]}-party.x"
            ;;
        program)
            if [[ -z "${BUILD_ARGS[machine]}" || -z "${BUILD_ARGS[src]}" ]]; then
                echo "Error: --machine and --src are required for building program stage."
                usage
            fi
            IMAGE_TAG="${BUILD_ARGS[machine]}-${BUILD_ARGS[src]}"
            BUILD_ARGS[machine]="${BUILD_ARGS[machine]}-party.x"
            ;;
        *)
            echo "Error: Invalid target '$TARGET'"
            usage
            ;;
    esac
}


print_build_info() {
    echo "Building Docker image:"
    echo "  Target Stage: $TARGET"
    echo "  Image Name: $IMAGE_NAME"
    echo "  Image Tag: $IMAGE_TAG"
    echo "  Dockerfile Arguments:"
    
    for arg in "${!BUILD_ARGS[@]}"; do
        echo "  $arg: ${BUILD_ARGS[$arg]}"
    done
}

build_docker_image() {
    local docker_args=(
        "-f" "$DOCKERFILE_PATH"
        "-t" "$IMAGE_NAME:$IMAGE_TAG"
        "--target" "$TARGET"
    )

    for arg in "${!BUILD_ARGS[@]}"; do
        docker_args+=( "--build-arg" "$arg=${BUILD_ARGS[$arg]}" )
    done

    docker_args+=( "$BUILD_CONTEXT" )

    docker build "${docker_args[@]}"
}

main() {
    parse_args "$@"
    validate_args
    print_build_info
    build_docker_image
}

main "$@"