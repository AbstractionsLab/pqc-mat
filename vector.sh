#!/usr/bin/env bash

set -euo pipefail

IMAGE_NAME="${VECTOR_IMAGE:-vector}"
CLI_CONTAINER_NAME="${VECTOR_CLI_CONTAINER_NAME:-vector-cli}"
GUI_CONTAINER_NAME="${VECTOR_GUI_CONTAINER_NAME:-vector-gui}"
GUI_PORT_DEFAULT="${VECTOR_PORT:-5992}"

SRC_MOUNT_POINT="/src"
OUTPUT_MOUNT_POINT="/output"
CBOM_MOUNT_POINT="/cbom-input"
GUI_HOST_MOUNT_POINT="/mnt/host-home"
DEMO_PROJECT_PATH="/home/vector/test-project/cryptography"
DEFAULT_OUTPUT_DIR="output"

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info() { printf '%s: %s\n' "$SCRIPT_NAME" "$1"; }
err()  { printf '%s: error: %s\n' "$SCRIPT_NAME" "$1" >&2; }

validate_identifier() {
  local value="$1" label="$2"
  if [[ ! "$value" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]]; then
    err "${label} ('${value}') is not a valid Docker name: it must start with a letter or digit and contain only letters, digits, '_', '.', or '-' — no spaces."
    return 1
  fi
  return 0
}
validate_identifier "$IMAGE_NAME" "VECTOR_IMAGE" || exit 1
validate_identifier "$CLI_CONTAINER_NAME" "VECTOR_CLI_CONTAINER_NAME" || exit 1
validate_identifier "$GUI_CONTAINER_NAME" "VECTOR_GUI_CONTAINER_NAME" || exit 1

usage() {
  cat <<EOF
Usage:
  ./${SCRIPT_NAME}
      Start VECTOR-GUI (same as "gui" below). Builds the image first only
      if it doesn't exist yet.

  ./${SCRIPT_NAME} gui [--port PORT] [--source-dir DIR]
      Start VECTOR-GUI and print the local address to open in a browser.
      --port        local port to publish (default: ${GUI_PORT_DEFAULT})
      --source-dir  host directory to make available inside the
                    container at ${GUI_HOST_MOUNT_POINT}, so it can be
                    entered as a source path in the web form
                    (default: the directory containing this script)

  ./${SCRIPT_NAME} cli
      Show the vector CLI help.

  ./${SCRIPT_NAME} cli <command> [args...]
      Run "vector <command> [args...]" inside the container.
      <command> is one of: code, network, score.
      For code and network, results go to --output DIR (must exist), or to
      ./${DEFAULT_OUTPUT_DIR} in the current directory (created if needed).
      Use "code demo" to analyze the demo project bundled in the image.

  ./${SCRIPT_NAME} build
      Build (or rebuild) the image unconditionally — run this after
      changing code.

  ./${SCRIPT_NAME} help | -h | --help
      Show help message.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} gui --port 8080 --source-dir ~/projects
  ./${SCRIPT_NAME} cli code demo
  ./${SCRIPT_NAME} cli code /path/to/project --name my-app --output ./results
  ./${SCRIPT_NAME} cli network --protocol tls --target example.com --port 443 --output ./results
  ./${SCRIPT_NAME} cli score ./results/cbom/crypto-combined-cbom.json
  ./${SCRIPT_NAME} build
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    err "Docker was not found on PATH. Install Docker Engine and try again."
    exit 1
  fi
}


do_build() {
  info "Building ${IMAGE_NAME} from Dockerfile..."
  if ! docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"; then
    err "Image build failed; not starting a container."
    exit 1
  fi
}

ensure_image() {
  require_docker
  if docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    return 0
  fi
  info "Image '${IMAGE_NAME}' not found locally."
  do_build
}

cmd_build() {
  require_docker
  do_build
}

tty_flags() {
  if [ -t 0 ] && [ -t 1 ]; then
    printf '%s\n' "-it"
  else
    printf '%s\n' "-i"
  fi
}

abspath() {
  if [ -d "$1" ]; then
    (cd "$1" && pwd)
  else
    (cd "$(dirname "$1")" && printf '%s/%s' "$(pwd)" "$(basename "$1")")
  fi
}

validate_dir() {
  local path="$1" label="$2"
  if [ ! -e "$path" ]; then
    err "${label} directory does not exist: ${path}"
    err "Create it first, e.g.: mkdir -p \"${path}\""
    return 1
  fi
  if [ ! -d "$path" ]; then
    err "${label} path exists but is not a directory: ${path}"
    return 1
  fi
  return 0
}

validate_file() {
  local path="$1" label="$2"
  if [ ! -e "$path" ]; then
    err "${label} file does not exist: ${path}"
    return 1
  fi
  if [ ! -f "$path" ]; then
    err "${label} path exists but is not a regular file: ${path}"
    return 1
  fi
  return 0
}

is_github_url() {
  [[ "$1" =~ ^https://github\.com/ ]] || [[ "$1" =~ ^git@github\.com: ]]
}

cmd_gui() {
  local port="$GUI_PORT_DEFAULT"
  local source_dir="$SCRIPT_DIR"

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --port)
        shift
        [ "$#" -gt 0 ] || { err "--port requires a value."; return 1; }
        port="$1"; shift ;;
      --source-dir)
        shift
        [ "$#" -gt 0 ] || { err "--source-dir requires a value."; return 1; }
        source_dir="$1"; shift ;;
      -h|--help)
        usage; return 0 ;;
      *)
        err "Unrecognized gui option: $1"
        usage
        return 1 ;;
    esac
  done

  local -a mounts=()
  if [ -n "$source_dir" ]; then
    validate_dir "$source_dir" "Source" || return 1
    mounts+=(-v "$(abspath "$source_dir"):${GUI_HOST_MOUNT_POINT}")
    info "Host directory available inside the container at ${GUI_HOST_MOUNT_POINT}"
  fi

  info "Starting VECTOR-GUI — open http://localhost:${port} once it reports running (Ctrl+C to stop)"
  docker run --rm $(tty_flags) --name "$GUI_CONTAINER_NAME" \
    -p "${port}:${port}" \
    -e "VECTOR_PORT=${port}" \
    ${mounts[@]+"${mounts[@]}"} \
    "$IMAGE_NAME" gui --port "${port}"
}


cmd_cli() {
  if [ "$#" -eq 0 ]; then

    docker run --rm $(tty_flags) --name "$CLI_CONTAINER_NAME" "$IMAGE_NAME"
    return $?
  fi

  local subcommand="$1"; shift
  local -a passthrough=("$subcommand")
  local -a mounts=()
  local output_given=0
  local runs_scan=0


  local help_requested=0
  local a
  for a in "$@"; do
    if [ "$a" = "-h" ] || [ "$a" = "--help" ]; then
      help_requested=1
      break
    fi
  done
  if [ "$subcommand" = "-h" ] || [ "$subcommand" = "--help" ] || [ "$subcommand" = "help" ]; then
    help_requested=1
  fi

  case "$subcommand" in
    code)
      if [ "$#" -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        passthrough+=("$@")
      else
        runs_scan=1
        local src="$1"; shift
        if [ "$src" = "demo" ]; then
          passthrough+=("${DEMO_PROJECT_PATH}")
        elif is_github_url "$src"; then
          passthrough+=("$src")
        else
          validate_dir "$src" "Source" || return 1
          mounts+=(-v "$(abspath "$src"):${SRC_MOUNT_POINT}")
          passthrough+=("${SRC_MOUNT_POINT}")
        fi

        while [ "$#" -gt 0 ]; do
          case "$1" in
            --output)
              shift
              [ "$#" -gt 0 ] || { err "--output requires a value."; return 1; }
              validate_dir "$1" "Output" || return 1
              mounts+=(-v "$(abspath "$1"):${OUTPUT_MOUNT_POINT}")
              passthrough+=(--output "${OUTPUT_MOUNT_POINT}")
              output_given=1
              shift ;;
            *) passthrough+=("$1"); shift ;;
          esac
        done
      fi
      ;;

    network)
      [ "$#" -gt 0 ] && runs_scan=1
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --output)
            shift
            [ "$#" -gt 0 ] || { err "--output requires a value."; return 1; }
            validate_dir "$1" "Output" || return 1
            mounts+=(-v "$(abspath "$1"):${OUTPUT_MOUNT_POINT}")
            passthrough+=(--output "${OUTPUT_MOUNT_POINT}")
            output_given=1
            shift ;;
          *) passthrough+=("$1"); shift ;;
        esac
      done
      ;;

    score)
      if [ "$#" -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        passthrough+=("$@")
      else
        local cbom="$1"; shift
        validate_file "$cbom" "CBOM" || return 1
        mounts+=(-v "$(dirname "$(abspath "$cbom")"):${CBOM_MOUNT_POINT}")
        passthrough+=("${CBOM_MOUNT_POINT}/$(basename "$cbom")")
        passthrough+=("$@")
      fi
      ;;

    -h|--help|help)
      : 
      ;;

    *)
      passthrough+=("$@")
      ;;
  esac

  # Without --output, vector would write to its working directory inside the image,
  # which the host user cannot write to: default to ./output on the host instead
  if [ "$output_given" -eq 0 ] && [ "$runs_scan" -eq 1 ] && [ "$help_requested" -eq 0 ]; then
    mkdir -p "$DEFAULT_OUTPUT_DIR" || { err "Could not create the default output directory ./${DEFAULT_OUTPUT_DIR}"; return 1; }
    validate_dir "$DEFAULT_OUTPUT_DIR" "Output" || return 1
    mounts+=(-v "$(abspath "$DEFAULT_OUTPUT_DIR"):${OUTPUT_MOUNT_POINT}")
    passthrough+=(--output "${OUTPUT_MOUNT_POINT}")
    info "No --output given: writing results to ./${DEFAULT_OUTPUT_DIR}"
  fi

  docker run --rm $(tty_flags) --name "$CLI_CONTAINER_NAME" \
    --user "$(id -u):$(id -g)" \
    ${mounts[@]+"${mounts[@]}"} \
    "$IMAGE_NAME" "${passthrough[@]}"
}

main() {
  if [ "$#" -eq 0 ]; then
    ensure_image
    cmd_gui
    return $?
  fi

  local action="$1"; shift
  case "$action" in
    build)
      cmd_build "$@" ;;
    gui)
      ensure_image
      cmd_gui "$@" ;;
    cli)
      ensure_image
      cmd_cli "$@" ;;
    help|-h|--help)
      usage ;;
    *)
      err "Unrecognized command: ${action}"
      usage
      exit 1 ;;
  esac
}

main "$@"