#!/bin/bash

set -e
/usr/sbin/sshd

# For debugging purposes
if [ "$#" = 0 ]; then
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "controller" ]; then
	/usr/sbin/rabbitmq-server &
	# TODO: Implicitly wait for broker to be up
	sleep 15
	splunk_eventgen service --role controller
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "server" ]; then
	splunk_eventgen service --role server
	tail -F -n0 /etc/hosts && wait
else
	"$@"
fi
