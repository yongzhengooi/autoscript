#!/bin/bash
############ CONFIG
targetfile="targets.txt"
nmap_path="./nmap"
testssl_path="./testssl"
ssh_path="./ssh"

######### COLOR
red=$(tput setaf 1) # Red
grn=$(tput setaf 2) # Green
ylw=$(tput setaf 3) # Yellow
blu=$(tput setaf 4) # Blue
pur=$(tput setaf 5) # Purple
cyn=$(tput setaf 6) # Cyan
wht=$(tput sgr 0) # White

if [ ! -d "./nmap" ];then
	mkdir nmap
fi

if [ ! -d "./testssl" ];then
	mkdir testssl
fi

count=0
total=$(cat $targetfile | wc -l)
####### MAIN
while read IP;do
	echo
	echo "$ylw[...] Checking if host $IP is alive $wht"
	filename=$(echo $IP | tr "." "_")
	if (nmap -sn $IP | grep -q "Host is up");then
		echo $IP >> alive.txt
		######Create dir if not exist
		echo "$grn[+] Target is online $wht"
		echo
		if [ ! -d "$nmap_path/$filename" ];then
			mkdir "$nmap_path/$filename"
		fi
		echo "$ylw[...] Performing nmap normal scan for HOST: $blu $IP $wht"
		#########Perform nmap scan
		nmap -sV -sC -Pn --min-rate 100 $IP -oA "$nmap_path/$filename/$filename" ##Change me
		echo
		echo "$ylw[...] Checking if Port SSH open $wht"
		if (grep -rqi "22/tcp" "./$nmap_path/$filenmae"); then
			echo "$grn[+] Port 22 detected $wht"
			if [ ! -d "./ssh" ];then
				mkdir ssh
			fi
			#### SSH script chcek
			mkdir "$ssh_path/$filename"
			nmap -Pn -p 22 --script ssh2-enum-algos.nse $IP -oN "$ssh_path/$filename/ssh.txt"
		fi
		
		########## Chcking ssl port
		echo
		echo "$ylw[...] Checking is SSL service is enabled $wht"
		echo "Note: this only check for https services, might need to refer to ssl.txt for others undetected service"
		nmap -Pn $IP --script="ssl-enum*" -oN "$nmap_path/$filename/ssl.txt"
		grep -i "https\|ssl/http" "./$nmap_path/$filename/ssl.txt" | awk -F "/" '{print $1}' > sslport.txt
		while read sslport;do
			echo "$grn[+] SSL port $sslport detected $wht"
			echo
			echo "$ylw[...]Testing with testSSL for HOST $blu $IP $ylw for port $blu $sslport $wht"
			if [ ! -d "$testssl_path/$filename" ]; then
				mkdir "$testssl_path/$filename"
			fi
			testssl --csvfile "$testssl_path/$filename" --logfile "$testssl_path/$filename" --ip=one "$IP:$sslport"
			echo 
		done<"./sslport.txt"
		
		### Just counting usage can ignore this 
		count=$(($count+1))
		echo
		echo
		echo "$pur $count/$total host completed $wht"
		
	else
		echo "$red[-] Target is down$wht"
	fi
	
done<$targetfile

###Searching for SSL vuln
##  WEAK TLS
echo "$ylw [...] Searching for weak TLS supported $wht"
find . -type f -name "*.log" -exec grep -lF "(deprecated)" {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." > vuln_weakTLS.txt
echo "$grn [+] Discoved $(cat vuln_weakTLS.txt | wc -l) targets $wht"
echo 

### GZIP / BR
echo "$ylw [...] Search for gzip / br vuln $wht"
find . -type f -name "*.log" -exec grep -lF "potentially NOT ok, " {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." > vuln_gzip.txt
echo "$grn [+] Discoved $(cat vuln_gzip.txt | wc -l) targets $wht" 
echo

### Certificate cannot trust
echo "$ylw [...] Search for expired, cannot trust or self signed cert $wht"
find . -type f -name "*.log" -exec grep -l "expired\|self signed" {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." > vuln_cannotTrust.txt
echo "$grn [+] Discoved $(cat vuln_cannotTrust.txt | wc -l) targets $wht"
echo

### Secure Client Initiated Renegotiation 
echo "$ylw [...] Search for Secure Client-Initiated Renegotiation $wht"
find . -type f -name "*.log" -exec grep -lF "DoS threat" {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." > vuln_renegotiation.txt
echo "$grn [+] Discoved $(cat vuln_renegotiation.txt | wc -l) targets $wht"
echo
echo
echo "$grn The vulnerable targets host have been output $wht"


