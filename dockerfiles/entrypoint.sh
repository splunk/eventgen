#!/bin/bash

set -e
/usr/sbin/sshd

# For debugging purposes
if [ "$#" = 0 ]; then
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "master" ]; then
	/usr/sbin/rabbitmq-server &
	tail -F -n0 /etc/hosts && wait
elif [ "$1" = "slave" ]; then
	tail -F -n0 /etc/hosts && wait
else
	"$@"
fi
