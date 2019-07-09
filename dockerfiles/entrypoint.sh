#!/bin/bash

set -e

if [ "$#" = 0 ]; then
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "controller" ]; then
	splunk_eventgen service --role controller
elif [ "$1" = "server" ]; then
	splunk_eventgen service --role server
elif [ "$1" = "standalone" ]; then
	splunk_eventgen service --role standalone
else
	"$@"
fi