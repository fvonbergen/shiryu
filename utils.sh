set -e

# The utils.sh script is intended to be sourced: source ./utils.sh.
# If it isn't sourced the variable SCRIPT will have an incorrect value.

#
# commands
#

readonly -a REQUIRED_CORE_COMMANDS=(
  "awk"
  "basename"
  "date"
  "md5sum"
  "realpath"
)
check_external_commands() {
  local missing_commands=()

  for cmd in "$@"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      missing_commands+=("${cmd}")
    fi
  done

  if [ ${#missing_commands[@]} -ne 0 ]; then
    printf "[-] [-] [ERROR]" "Missing required commands: ${missing_commands[*]}"
    exit 1
  fi
}

check_external_commands "${REQUIRED_CORE_COMMANDS[@]}"

#
# functions
#

# get_stamp

if ! [[ -v VERSION ]]; then
  printf "VERSION variable is not set."
  exit 1
fi
SCRIPT=$(realpath "$0")
get_stamp() {
  local DIGEST

  DIGEST=$(md5sum "${SCRIPT}" | awk '{print $1}')
  printf "{'script': ['${SCRIPT}', '${DIGEST}', '${VERSION}']}"
}

# get_script_name

get_script_name() {
  printf $(basename "${SCRIPT}")
}

# log

IS_TERMINAL=${IS_TERMINAL:-false}
if [ -t 1 ] || [ "${IS_TERMINAL}" = true ]; then
  IS_TERMINAL=true
fi

color() {
  local type=$1

  if ${IS_TERMINAL}; then
    case ${type} in
    DEBUG) str="\033[95m" ;;
    INFO) str="\033[92m" ;;
    WARNING) str="\033[93m" ;;
    WAIT) str="\033[94m" ;;
    ERROR) str="\033[91m" ;;
    esac
    printf "${str}${type}\033[0m"
  else
    printf "${type}"
  fi
}

timestamp() {
  date +'%Y-%m-%dT%T.%6N'
}

LOG_FILE=""
LAST_TYPE=""
log() {
  {
    local TYPE=$1
    local SCRIPT_NAME=$(get_script_name)
    shift
    local begin=""
    local end="\n"
    local now

    now=$(timestamp)
    if ${IS_TERMINAL}; then
      if [ "${TYPE}" == "WAIT" ]; then
        begin="\r"
        end=""
      else
        if [ "${LAST_TYPE}" == "WAIT" ]; then
          begin="\n"
        fi
      fi
    fi
    printf "${begin}[${now}] [${SCRIPT_NAME}] [$(color "${TYPE}")] %s${end}" "$*"
    if [ -n "${LOG_FILE}" ]; then
      printf "[${now}] [${SCRIPT_NAME}] [${TYPE}] %s\n" "$*" >>"${LOG_FILE}"
    fi
    LAST_TYPE="${TYPE}"
  } 2>/dev/null
}

# enable_debug

enable_debug() {
  log WARNING "Enable debug"
  _l='               '
  export PS4='${_l:0:${#FUNCNAME[@]}}[$(timestamp)] [${SCRIPT_NAME}] [$(color DEBUG)] [${LINENO}] [${FUNCNAME[0]}] '
  set -x
}
