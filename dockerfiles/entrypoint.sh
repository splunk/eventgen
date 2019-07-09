#!/bin/bash

set -e

if [ "$#" = 0 ]; then
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "controller" ]; then
	splunk_eventgen service --role controller &
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "server" ]; then
	splunk_eventgen service --role server &
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "standalone" ]; then
	splunk_eventgen service --role standalone &
	tail -F -n0 /etc/hosts && wait
else
	"$@"
fi