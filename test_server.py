'''
This is a test program to act as server for basic requests
this will now add threads to handle multiple clients
server (this device):
Client: don't care


This device sits and waits to be contacted.  it then fires off a basic response which will
grow

'''

import socket
import threading
import time

HOST=''
PORT=54321

def handle_client(conn,addr):
	'''
		this function is what each thread executes when a client connection is made
	'''
	print("[thread] starting")
	
    # recv message
	message = conn.recv(1024)
	message = message.decode()
	print("[thread] client:", addr, 'recv:', message)
	
	# simulate longer work, this would be where we do an update or something
	time.sleep(5)

	# send answer
	message = "Got your message friend!"
	message = message.encode()
	conn.send(message)
	print("[thread] client:", addr, 'send:', message)
	
	#wrap up our connection
	conn.close()

	print("[thread] ending")
	

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:	#AF_INET = AddressFamily Internet (IPV4), SOCK_STREAM = TCP
	s.bind((HOST,PORT))
	s.listen(9)	#bind and listen on the port we initiated, will listen for 9 connections
	all_threads=[]	#this will hold all of our threads for record keeping
	try:
		while True:
			#Wait for a connection
			print("waiting")
			conn,addr = s.accept()	#accept our connection and address of what we accepted, the program blocks on this line to a connection is received
			print("accepting from ",addr)

			#begin the threading to get it rolling		
			t=threading.Thread(target=handle_client,args=(conn,addr))
			t.start()
			
			#adding a thread
			all_threads.append(t)
			
	except KeyboardInterrupt:
		print("Stopped by Ctrl+C")
	finally:
		#do our cleanup
		if s:
			s.close()
		for t in all_threads:
			t.join()

		