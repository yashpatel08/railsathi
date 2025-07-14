#!/bin/sh

HOST=$1
PORT=$2
TIMEOUT=${3:-15}

echo "Waiting for $HOST:$PORT to become available..."

i=0
while [ "$i" -lt "$TIMEOUT" ]; do
  nc -z "$HOST" "$PORT" && echo "$HOST:$PORT is available!" && break
  sleep 1
  i=$((i+1))
done

if ! nc -z "$HOST" "$PORT"; then
  echo "Timeout after $TIMEOUT seconds waiting for $HOST:$PORT"
  exit 1
fi

# Run the command if provided
shift 3
if [ $# -gt 0 ]; then
  exec "$@"
fi
