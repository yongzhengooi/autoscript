#!/bin/bash
######### COLOR
red=$(tput setaf 1) # Red
grn=$(tput setaf 2) # Green
ylw=$(tput setaf 3) # Yellow
blu=$(tput setaf 4) # Blue
pur=$(tput setaf 5) # Purple
cyn=$(tput setaf 6) # Cyan
wht=$(tput sgr 0) # White

find . -type f -name "*.txt" 2>/dev/null | awk -F "/" '{print $2}' | uniq > "folder.tmp"
while read path;do
	echo "$ylw [...] Checking for $blu $path $wht"
	echo "$grn [+] Showing reachable host by ping $wht"
	find "./$path" -type f -name "*.txt" -exec grep -rli "Host is up" {} \; 2>/dev/null | sort
	echo ""
	echo "$grn [+] Showing path possible open for TCP$wht"
	find "./$path" -type f -name "*.nmap" -exec grep -rlE '[0-9]+/tcp +open' {} \; 2>/dev/null | sort
	echo "$grn [+] showiing path possible open for UDP $wht"
	find "./$path" -type f -name "*.nmap" -exec grep -rlE '[0-9]+/udp +open' {} \; 2>/dev/null | sort
	echo ""
	echo ""
done<"folder.tmp"

rm folder.tmp
