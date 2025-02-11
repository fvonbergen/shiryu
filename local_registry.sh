set -e

VERSION=0.0.1
# IS_TERMINAL=

source ./utils.sh

#
# script
#

readonly -a REQUIRED_SCRIPT_COMMANDS=(
  "cat"
  "docker"
  "getopt"
  "mkdir"
  "pwd"
)

check_external_commands "${REQUIRED_SCRIPT_COMMANDS[@]}"

usage() {
  local EXIT_CODE=$1
  local SCRIPT_NAME=$(get_script_name)

  cat <<-EOF
  Usage: ${SCRIPT_NAME} [-hvd]
    -h, --help    Print help message.
    -v, --version Print script version.
    -d, --debug   Enable debug.

    Positional options:
      
EOF
  exit "${EXIT_CODE}"
} 1>&2

options=$(getopt -n "${SCRIPT_NAME}" -l "help,version,debug,log:" -o "hvdl:" -- "$@" || usage 1)
eval set -- "${options}"
while true; do
  case "$1" in
  -h | --help)
    usage 0
    ;;
  -v | --version)
    get_stamp
    exit 0
    ;;
  -d | --debug)
    enable_debug
    ;;
  -l | --log)
    LOG_FILE=$2
    ;;
  --)
    shift
    break
    ;;
  esac
  shift
done

shift $((OPTIND - 1))

log INFO "$(get_stamp)"

PROJECT_NAME="shiryu"
CONTAINER_REGISTRY_DIRECTORY="${PROJECT_NAME}-registry"
log INFO "Create directory ${CONTAINER_REGISTRY_DIRECTORY}"
mkdir -p ${CONTAINER_REGISTRY_DIRECTORY}
CONTAINER_REGISTRY_LOCALHOST_NAME="${PROJECT_NAME}-registry-localhost"
log INFO "Stop and remove container with local registry in localhost network ${CONTAINER_REGISTRY_LOCALHOST_NAME}"
docker container stop ${CONTAINER_REGISTRY_LOCALHOST_NAME} || true
docker container rm ${CONTAINER_REGISTRY_LOCALHOST_NAME} || true
log INFO "Run container with local registry in localhost network ${CONTAINER_REGISTRY_LOCALHOST_NAME}"
docker run \
  --detach \
  --restart=always \
  --name="${CONTAINER_REGISTRY_LOCALHOST_NAME}" \
  --user="$(id --user ${USER})":"$(id --group ${USER})" \
  --volume=$(pwd)/${CONTAINER_REGISTRY_DIRECTORY}:/var/lib/registry \
  --publish=5000:5000 \
  registry:latest
DAGGER_PROJECT_IMAGE_NAME_TAG="localhost:5000/${PROJECT_NAME}/python:3.12-slim-git"
log INFO "Build container image ${DAGGER_PROJECT_IMAGE_NAME_TAG}"
docker build \
  --tag=${DAGGER_PROJECT_IMAGE_NAME_TAG} \
  --file=Dockerfile \
  .
log INFO "Push container image ${DAGGER_PROJECT_IMAGE_NAME_TAG}"
docker push ${DAGGER_PROJECT_IMAGE_NAME_TAG}
log INFO "Stop container with local registry in localhost network ${CONTAINER_REGISTRY_LOCALHOST_NAME}"
docker container stop ${CONTAINER_REGISTRY_LOCALHOST_NAME}
CONTAINER_DAGGER_ENGINE_NAME_PREFIX="dagger-engine-v"
CONTAINER_DAGGER_ENGINE_NAME="$(
  docker container ls \
    --filter=name=${CONTAINER_DAGGER_ENGINE_NAME_PREFIX}* \
    --format='{{.Names}}'
)"
# CONTAINER_DAGGER_ENGINE_VERSION=${CONTAINER_DAGGER_ENGINE_NAME#"${CONTAINER_DAGGER_ENGINE_NAME_PREFIX}"}
CONTAINER_REGISTRY_DAGGER_ENGINE_NAME="${PROJECT_NAME}-registry-${CONTAINER_DAGGER_ENGINE_NAME}"
log INFO "Stop and remove container with local registry in dagger engine network ${CONTAINER_REGISTRY_DAGGER_ENGINE_NAME}"
docker container stop ${CONTAINER_REGISTRY_DAGGER_ENGINE_NAME} || true
docker container rm ${CONTAINER_REGISTRY_DAGGER_ENGINE_NAME} || true
log INFO "Run container with local registry in dagger engine network ${CONTAINER_REGISTRY_DAGGER_ENGINE_NAME}"
docker run \
  --detach \
  --restart=always \
  --name="${CONTAINER_REGISTRY_DAGGER_ENGINE_NAME}" \
  --volume=$(pwd)/${CONTAINER_REGISTRY_DIRECTORY}:/var/lib/registry \
  --network=container:${CONTAINER_DAGGER_ENGINE_NAME} \
  registry:latest
