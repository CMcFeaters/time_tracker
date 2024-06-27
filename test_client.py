'''
This is a test program to act as server for basic requests

server LOCAL HOST
Client: (this device)


This device contacts the server.  It does this periodically and ad-hoc (user input)
It can contact to provide the server some information or it can contact to just receice info
'''

import socket
import threading
import json

HOST='localhost'
PORT=54321



def request_state(id):
	"""
	just requests the server provide the current game state
	"""
	data={"id":id,"comm":0}
	print("Data to send: {data}".format(data=repr(data)))
	
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		
		#ask for a picture from the server
		print("Initiating connection")
		s.connect((HOST,PORT))
		print(json.dumps(data))
		s.sendall(bytearray(json.dumps(data),'utf-8'))
		#bytearray(repr(data),'utf-8')
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
		#print("State %d received"%i)
		print("Date recived: ", data.decode())
		
		
		
		s.close()	#close the socket
	
	#return the file name
	return data
	

def main():
	all_threads=[]
	id=10
	try:
		for i in range(1,2):
			print ("request: ",i)
			t=threading.Thread(target=request_state, args=([id]))
			print ("starting")
			t.start()
			all_threads.append(t)
			id+=1
			print('exiting')
	except KeyboardInterrupt:
		print("CTRL+C")
	finally:
		print("Close it out")
		for t in all_threads:
			t.join()
		
if __name__=="__main__":
	main()