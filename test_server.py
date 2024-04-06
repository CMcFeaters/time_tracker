'''
This is a test program to act as server for basic requests

server (this device):
Client: don't care


This device sits and waits to be contacted.  it then fires off a basic response which will
grow

'''

import socket

HOST=''
PORT=54321

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:	#AF_INET = AddressFamily Internet (IPV4), SOCK_STREAM = TCP
	s.bind((HOST,PORT))
	s.listen()	#bind and listen on the port we initiated
	
	while True:
		#Wait for a connection
		print("waiting")
		conn,add = s.accept()	#accept our connection and address of what we accepted, the program blocks on this line to a connection is received
		print("accepting from ",add)
		print("received: ",conn.recv(1024))
		
		#once a request has occured,
		#we take the picture
		data="HELLO FRIEND"
		
		with conn:
			#we respond back over the socket with the data
			print("replying with data")
			print(conn.sendall(data))
			print("Data sent")

		