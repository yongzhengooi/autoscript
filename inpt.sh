#!/bin/bash
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

count=0
total=$(cat $targetfile | wc -l)
####################
create_dir(){
	if [ ! -d "$1" ];then
		mkdir "$1"
	fi
}
nmap_normal(){
	echo "$ylw[...] Performing nmap normal scan for HOST: $blu $1 $wht"
	#########Perform nmap scan
	nmap -sV -sC -Pn --min-rate 100 $1 -oA "$2" ##Change me
	echo
}
### param targetIP fileLocation outputLocation
check_ssh(){
	echo "$ylw[...] Checking if Port SSH open $wht"
	if (grep -rqi "22/tcp" "$2"); then
		echo "$grn[+] Port 22 detected $wht"
		if [ ! -d "./ssh" ];then
			mkdir ssh
		fi
		nmap -Pn -p 22 --script ssh2-enum-algos.nse $1 -oN "$3"
	fi
}

check_ssl(){
########## Chcking ssl port
	echo
	echo "$ylw[...] Checking is SSL service is enabled $wht"
	echo "Note: this only check for https services, might need to refer to ssl.txt for others undetected service"
	nmap -Pn $1 --script="ssl-enum*" -oN "$2"
	grep -i "https\|ssl/http" "$2" | awk -F "/" '{print $1}' > sslport.txt
	while read sslport;do
		echo "$grn[+] SSL port $sslport detected $wht"
		echo
		echo "$ylw[...]Testing with testSSL for HOST $blu $1 $ylw for port $blu $sslport $wht"
		testssl --csvfile "$3" --logfile "$3" --ip=one "$1:$sslport"
		echo
	done<"./sslport.txt"
	rm ./sslport.txt
}
###### MAIN FUNCTION
run(){
	echo
	echo "$ylw[...] Checking if host $1 is alive $wht"
	### If subnet IP
	if [[ $1 =~ .*"/".* ]]; then
		filename=$(echo $1 | tr "." "_" | sed s/"\/"/"_sub"/g)
		create_dir $nmap_path $filename
		nmap -sL -n $1 | awk '/Nmap scan report for/ {print $5}' > subnet.txt
		while read subnet;do
			echo "$ylw [..] Checking IP $subnet From $1"
			if (nmap -sn $subnet | grep -q "Host is up");then  
				echo "$grn[+] Target is online $wht"
				echo $subnet >> alive.txt
				echo
				sub_filename=$(echo $subnet | tr "." "_" )
				## nmap part
				create_dir "$nmap_path/$filename"
				create_dir "$nmap_path/$filename/$sub_filename"
				nmap_normal $subnet "./$nmap_path/$filename/$sub_filename/$sub_filename"
				
				### ssh part
				create_dir "$ssh_path/$filename"
				create_dir "$ssh_path/$filename/$sub_filename"
				check_ssh $subnet "$nmap_path/$filename/$sub_filename" "$ssh_path/$filename/$sub_filename/ssh.txt"
				
				#### ssl part 
				create_dir "$testssl_path/$filename"
				create_dir "$testssl_path/$filename/$sub_filename"
				check_ssl $subnet "$nmap_path/$filename/$sub_filename/ssl.txt" "$testssl_path/$filename/$sub_filename"
			else
				echo "$red[-] Target is down$wht"
			fi
		done<"./subnet.txt"
		rm "./subnet.txt"
	else
		filename=$(echo $1 | tr "." "_" )
		if (nmap -sn $1| grep -q "Host is up");then  
			echo $1 >> alive.txt
			echo "$grn[+] Target is online $wht"
			echo
			sub_filename=$(echo $1 | tr "." "_" )
			create_dir "$nmap_path/$filename"
			nmap_normal $1 "$nmap_path/$filename/$filename"
			create_dir "$ssh_path/$filename"
			check_ssh $1 "$nmap_path/$filename" "$ssh_path/$filename/ssh.txt"
			create_dir "$testssl_path/$filename"
			check_ssl $1 "$nmap_path/$filename/ssl.txt" "$testssl_path/$filename"
		else
			echo "$red[-] Target is down$wht"
		fi
	fi	
}

##########GET VULN FUCTION
scope_vuln_from_log(){
	echo "$ylw [...] Searching for $1 $wht"
	### Normal IP
	find . -type f -name "*.log" -exec grep -l $2 {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." | grep -v "sub" > "vuln/$3"
	### subnet
	find . -type f -name "*.log" -exec grep -l $2 {} \; 2>/dev/null | awk -F "/" '{print $4}' | tr "_" "." | grep -v "log" >> "vuln/$3"
	cp vuln/$3 ./tmp.txt
	cat ./tmp.txt | sort | uniq > vuln/$3
	rm ./tmp.txt
	echo "$grn [+] Discoved $(cat "vuln/$3" | wc -l) targets $wht"
	echo 	
}

scope_vuln_from_nmap(){
	echo "$ylw [...] Searching for $1 $wht"
	### Normal IP
	find . -type f -name "*.txt" -exec grep -l $2 {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." | grep -v "sub" > "vuln/$3"
	### subnet
	find . -type f -name "*.txt" -exec grep -l $2 {} \; 2>/dev/null | awk -F "/" '{print $4}' | tr "_" "." | grep -v "txt" >> "vuln/$3"
	cp vuln/$3 ./tmp.txt
	cat ./tmp.txt | sort | uniq > vuln/$3
	rm ./tmp.txt
	echo "$grn [+] Discoved $(cat "vuln/$3" | wc -l) targets $wht"
	echo 	
}


## INIT dir
create_dir nmap
create_dir ssh
create_dir testssl
create_dir vuln
#while read IP; do
	#run $IP
#done<$targetfile

######## Summarize vuln scope
## This few code is to suppress grep random matching when using 'offered (NOT ok)'
echo "$ylw [...] Searching for SSLv3 Protocol Detection $wht"
find . -type f -name "*.log" -exec grep -l 'offered (NOT ok)' {} \; 2>/dev/null | awk -F "/" '{print $3}' | tr "_" "." | grep -v "sub" > "vuln/sslv3.txt"
find . -type f -name "*.log" -exec grep -l 'offered (NOT ok)' {} \; 2>/dev/null | awk -F "/" '{print $4}' | tr "_" "." | grep -v "log" >> "vuln/sslv3.txt"
#cat $3 | sort | uniq >$3
echo "$grn [+] Discoved $(cat "vuln/sslv3.txt" | wc -l) targets $wht"
echo 	
## TESTSSL
scope_vuln_from_log "weak TLS supported" "(deprecated)" 'weak_tls.txt' #WEAK TLS
#scope_vuln_from_log "SSLv3 Protocol Detection" "offered (NOT ok)" 'ssl_V3_detection.txt' #SSLv3
scope_vuln_from_log "GZ or BR compression" '"gzip"\|"br"' 'gzip.txt'
scope_vuln_from_log "expired certificate" "expired" 'expired_cert.txt' #expired cert
scope_vuln_from_log "Secure Client-Initiated Renegotiation" "DoS threat" 'secure_client_init_renego.txt' #Secure Client-Initiated Renogotiation

###NMAP
scope_vuln_from_nmap "SSH Weak Cryto algo supported" "\-96\|\-cbc\|arcfour" 'weak_cryto_algo_supported.txt'
scope_vuln_from_nmap "SSH Weak key exchange supported" "\-group1\-\|\-group\-exchange\-sha1\|gss\-\|rsa1024" 'weak_key_exchange_supported.txt'
###Clear empty dir
echo "$grn [+] Removing empty file and directory $wht"
find . -type f -empty -print -delete;
find . -type d -empty -print -delete;
