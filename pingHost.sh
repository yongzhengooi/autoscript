#!/bin/bash
target="targets.txt"
while read IP;do
	echo "Checking Host: $IP"
	ping -c 3 $IP
done<$target
