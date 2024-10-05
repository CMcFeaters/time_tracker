import concurrent.futures
import logging
import queue
import random
import threading
import time
import datetime as dt

'''
Queue: https://docs.python.org/3/library/queue.html



'''


class Shopper():
	def __init__(self,id):
		self.shopID=id
		self.enter=dt.datetime.now()
		self.serv=0
		self.exit=0
		self.trans=random.randint(0,2)
	

def producer(queue, event):
	"""Pretend we're getting a number from the network."""
	shid=0
	while shid<25 or not event.is_set():
		#message = random.randint(1, 101)
		#logging.info("Producer got message: %s", message)
		shid+=1
		shopper=Shopper(shid)
		logging.info("created shopper %s"%shid)
		queue.put(shopper)

	logging.info("Producer received event. Exiting")

def consumer(queue, event):
	"""Pretend we're saving a number in the database."""
	while not event.is_set() or not queue.empty():
		'''message = queue.get()
		logging.info(
			"Consumer storing message: %s (size=%d)", message, queue.qsize()
		)
		'''
		shopper=queue.get()
		shopper.serv=dt.datetime.now()
		logging.info("Servicing shopper %s, delay time: %s"%(shopper.shopID,shopper.trans))
		time.sleep(shopper.trans/10)
		shopper.exit=dt.datetime.now()
		logging.info("Done shopper %s"%(shopper.shopID))
		logging.info("Shopper %s, total wait time: %s"%(shopper.shopID,(shopper.exit-shopper.enter)))
		
	logging.info("Consumer received event. Exiting")

if __name__ == "__main__":
	#shopper=Shopper(1)
	#print("trans time: %s"%shopper.trans)
	format = "%(asctime)s: %(message)s"
	logging.basicConfig(format=format, level=logging.INFO,
						datefmt="%H:%M:%S")

	pipeline = queue.Queue(maxsize=100)
	event = threading.Event()
	with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
		executor.submit(producer, pipeline, event)
		executor.submit(consumer, pipeline, event)
		executor.submit(consumer, pipeline, event)
		

		#while not queue.empty():
		#	time.sleep(0.1)
		logging.info("Main: about to set event")
		event.set()
