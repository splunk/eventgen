#!/bin/sh

set -e

if [ "$#" -eq  "0" ]; then
	cd /root/
	gitbook serve
else
	"$@"
fi
