#!/bin/sh

set -e

if [ "$#" -eq  "0" ]; then
	cd /root/
	gitbook build
	cd _book && python3 -m http.server 4000
else
	"$@"
fi
