#!/bin/bash
############ CONFIG
targetfile="targets.txt"
nmap_path="./nmap"

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
	echo "$ylw[...] Performing nmap TCP FULL scan for HOST: $blu $1 $wht"
	#########Perform nmap scan
	nmap -n -Pn -sS -p- -v -T4 --min-rate 500 --max-rate 700 $1 -oA "$2/TCP/$3" ##Change me
	nmap -n -sn -v -T3 $1 -oN "$2/ICMP/$3_icmp.txt"
	nmap -n -Pn -sU -v -T4 $1 --top-ports 1000 -oA "$2/UDP/$3" 
	echo
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
			if (nmap -sn -Pn $subnet | grep -q "Host is up");then  
				echo "$grn[+] Target is online $wht"
				echo $subnet >> alive.txt
				echo
				sub_filename=$(echo $subnet | tr "." "_" )
				## nmap part
				create_dir "$nmap_path/$filename"
				create_dir "$nmap_path/$filename/$sub_filename"
				create_dir "$nmap_path/$filename/$sub_filename/TCP"
				create_dir "$nmap_path/$filename/$sub_filename/ICMP"
				create_dir "$nmap_path/$filename/$sub_filename/UDP"
				nmap_normal $subnet "./$nmap_path/$filename/$sub_filename" $sub_filename
			else
				echo "$red[-] Target is down$wht"
			fi
		done<"./subnet.txt"
		rm "./subnet.txt"
	fi
}
## INIT dir
create_dir nmap
while read IP; do
	run $IP
done<$targetfile

###Clear empty dir
echo "$grn [+] Removing empty file and directory $wht"
find . -type f -empty -print -delete;
find . -type d -empty -print -delete;
