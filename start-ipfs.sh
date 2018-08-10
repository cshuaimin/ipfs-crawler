#!/bin/sh

if [ -e "/root/.ipfs/config" ]; then
  echo "Found IPFS fs-repo"
else
  ipfs init
fi

exec ipfs daemon