#!/bin/sh

if [ -e "$IPFS_PATH/config" ]; then
  echo "Found IPFS fs-repo $IPFS_PATH"
else
  ipfs init
fi

exec ipfs daemon --enable-gc
