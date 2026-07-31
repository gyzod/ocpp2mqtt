#!/bin/sh
set -eu

IMAGE="gyzod/ocpp2mqtt"
VERSION="$(python3 -c 'from version import __version__; print(__version__)')"

docker build -t "$IMAGE:$VERSION" -t "$IMAGE:beta" .
docker push "$IMAGE:$VERSION"
docker push "$IMAGE:beta"


