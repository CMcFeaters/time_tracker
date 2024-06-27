'''
This is a test program to act as server for basic requests
this will now add threads to handle multiple clients
server (this device):
Client: don't care


This device sits and waits to be contacted.  it then fires off a basic response which will
grow

protocol
{id:id#,comm:comm_type,param:parameter_name,val:new_value}
id (integer) the id number of teh unit
	0: supervisor
	1-10: players
comm (integer) is teh communication type
	0: request data
	1: write data
param (integer) is the parameter being changed in a write
	tbd
val (tbd) the value that is being updated
	tbd (this needs to be figured out when we develop the data model)

CONOPS:
Startup:  Get date, check for game, clear or join game, get current state in program memory
If receive a read: send current data
If receive a write: update DB, read DB, send current data

We'll use mariadb as our DBMS, need to build the data structure

'''

import socket
import threading
import time
import json

HOST=''
PORT=54321

def data_parse(data):
	''''
		this function parses the data recieved from a client and perfoms whatever
		actions are needed
	'''
	if data["comm"]==0:
		return ("{id} has requested information only".format(id=data["id"]))
	else:
		return ("null")

def handle_client(conn,addr,tnum):
	'''
		this function is what each thread executes when a client connection is made
	'''
	print(tnum," starting")
	
    # recv message
	message = conn.recv(1024)
	message = message.decode()
	data=json.loads(message)
	print("Handler thread {tnum} receving message from {addr}.  Message: {message}".format(tnum=tnum,addr=addr,message=message))
	# simulate longer work, this would be where we do an update or something
	time.sleep(5)
	response=data_parse(data)
	# send answer
	#message = "Got your message friend {thread}".format(thread=tnum)
	#message = message.encode()
	conn.send(response.encode())
	#print(tnum, " client:", addr, 'send:', message)
	
	#wrap up our connection
	conn.close()

	print(tnum, " ending")
	

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
			t=threading.Thread(target=handle_client,args=(conn,addr,len(all_threads)))
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

		