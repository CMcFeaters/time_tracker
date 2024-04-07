'''
This is a test program to act as server for basic requests

server (this device):
Client: don't care


This device sits and waits to be contacted.  it then fires off a basic response which will
grow

'''

import socket

HOST='localhost'
PORT=54321

def main():
	print('calling server')
	print(request_state())
	print('exiting')

def request_state():
	"""
	request_pic:
	1) initiates a socket connection with the pi_cam host
	2) waits and recieves RGB array data back from host
	3) converts to jpg formt
	4) writes to a date/time stamped file
	5) returns the file name
	
	returns: (string) filename 
	"""
	
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		
		#ask for a picture from the server
		print("Initiating connection")
		s.connect((HOST,PORT))
		s.sendall(b'Please Send me the state')
		
		#once we connect, recieve the response until connection is closed
		data=0
		data=s.recv(1024)	#our buffer is 1024 bytes
		i=0
		print ('Receiving state')
		while 1:
			#print('Receiving %d'%i)
			tdata=s.recv(1024)
			if not tdata: break	#if there's nothing here, break out
			data+=tdata
			i+=1
		print("State %d received"%i)
		
		
		
		s.close()	#close the socket
	
	#return the file name
	return data
	
if __name__=="__main__":
	main()