from flask import Flask, render_template, jsonify, request, abort
from func import *
import requests
import json
import pika
import uuid
import time
import ast
import logging
import docker
import os
import signal
import schedule
import threading
from kazoo.client import KazooClient
from kazoo.client import KazooState


# Enable this to see the outputs after starting the server
logging.basicConfig()


#  Open a new connection with the RabbitMQ server
connection = pika.BlockingConnection(pika.ConnectionParameters('10.0.2.2'))
channel = connection.channel()

# Create two different exchanges, one to handle read requests and the other to handle write and sync requests
channel.exchange_declare(exchange = 'independent', exchange_type = 'direct')
channel.exchange_declare(exchange = 'sync', exchange_type = 'direct')


# Creation of the four queues
result = channel.queue_declare(queue='readQ')
queue_name = result.method.queue
channel.queue_bind(exchange='independent', queue=queue_name, routing_key = "readQ")

result = channel.queue_declare(queue='writeQ')
queue_name = result.method.queue
channel.queue_bind(exchange='sync', queue=queue_name, routing_key = "writeQ")

result = channel.queue_declare(queue='syncQ', durable = True)
queue_name = result.method.queue
channel.queue_bind(exchange='sync', queue=queue_name, routing_key = "syncQ")

result = channel.queue_declare(queue='responseQ')
queue_name = result.method.queue
channel.queue_bind(exchange='independent', queue=queue_name, routing_key = "responseQ")



# This class defines the method or the RPC pattern to be applied when a read request comes in
class read_client(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(host='10.0.2.2'))

		self.channel = self.connection.channel()

		# Setting the reply queue to responseQ
		self.callback_queue = "responseQ"

		# Set the on_response function to run once a reply comes to be validated
		self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)

	# Verification of the reply
	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	# Send a request and get the reply after verification 
	def call(self, n):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		
		self.channel.basic_publish(exchange='independent', routing_key='readQ', properties=pika.BasicProperties(reply_to=self.callback_queue, correlation_id=self.corr_id, content_type = "application/json"),body=str(n))
		
		while self.response is None:
			self.connection.process_data_events()
		self.connection.close()
		
		return self.response

# This class defines the method or the RPC pattern to be applied when a write request comes in
class write_client(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(host='10.0.2.2'))

		self.channel = self.connection.channel()

		# Setting the reply queue to responseQ
		self.callback_queue = "responseQ"

		# Set the on_response function to run once a reply comes to be validated
		self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)

	# Verification of the reply
	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body
	# Send a request and get the reply after verification 
	def call(self, n):
		self.response = None
		self.corr_id = str(uuid.uuid4())

		self.channel.basic_publish(exchange='sync', routing_key='writeQ', properties=pika.BasicProperties(reply_to=self.callback_queue, correlation_id=self.corr_id, content_type = "application/json"),body=str(n))
		
		while self.response is None:
			self.connection.process_data_events()
		self.connection.close()
		
		return self.response

# Importing the docker variables from the host
client = docker.from_env()

# A set of global variables to handle entering various sections of the code
not_called_by_scale = True
deleted_master = False
# Setting the initial active containers pid and uuid and the counting the number or requests
active_containers = {}
counter = 0

# Establish a connection with the Zookeeper
zk = KazooClient(hosts='10.0.2.3:2181')
zk.start()

# Create a parent node for the child container if one doesn't exist
if(zk.exists("/producer")):
	zk.delete("/producer", recursive = True)

zk.ensure_path("/producer")

# Run the initial two workers of master and slave on the cry_cloud network
# The time.sleep argument is for the docker service to have enough time to create a new container 
temp1 = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
time.sleep(10)
temp = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
time.sleep(10)

# Set the children in case of a change in children nodes in the zookeeper i.e a container is created or destroyed
prev_children = zk.get_children("/producer")

# Holds the key value pairs of uuids of containers and their PIDS in the host OS
active_containers["master"] = temp1.top()['Processes'][0][2]
for i in prev_children:
	if(i != "master"):
		active_containers[i] = temp.top()['Processes'][0][2]

@zk.ChildrenWatch("/producer")
def watch_children(children):
	global not_called_by_scale
	global deleted_master
	"""
	This section is configured such that a when a container dies or is created, based on which api calls it,
	it behaves differently. The not_called_by_scale variable handles the scalability api where-as the rest is
	meant actually in case of a node failure or a crash call.
	"""
	if(not_called_by_scale):
		global prev_children
		global active_containers
		
		# Get the list of deleted children uuid if any
		deleted_child = list(set(prev_children) - set(children))
		if(deleted_child != []):
			for i in deleted_child:	
				# Try block here is mentioned in the case that the crash api has already updated the active container dictionary
				try:
					del active_containers[i]
				except:
					pass
				
				# Creation of a new worker
				temp = client.containers.run("worker", auto_remove = True, detach = True, network = "cry_cloud")
				time.sleep(8)
				
				# This section is meant to get all the details of the new node spawned 
				all_children = zk.get_children("/producer")
				new_child = list(set(all_children) - set(children))

				# Update new child details in the dictionary and handle master crash call
				for i in new_child:
					if(deleted_master):
						active_containers["master"] = temp.top()['Processes'][0][2]
						deleted_master = False
					else:
						active_containers[i] = temp.top()['Processes'][0][2]
	else:
		# Do no container respawn in case of failure
		not_called_by_scale = True
	prev_children = zk.get_children("/producer")

# Resets the request counter
def reset():
	global counter
	if counter!= 0:
		counter = 0
# Schedules the functions to be called every 2 minutes for scalability
def reset_counter():
	a = requests.get
	schedule.every(2).minutes.do(a,"http://10.0.2.4/api/v1/scale-check")
	schedule.every(2).minutes.do(reset)

def executioner():
	while True:
		schedule.run_pending()
reset_counter()


app=Flask(__name__)
print("Running orchestrator now!")


# Clears the database on success, else returns a 500 error
@app.route('/api/v1/db/clear', methods = ['POST'])
def clear_db():
	table_list = ["user_details", "rides", "ride_join"]
	for i in table_list:
		req = { "'1'": "1", 'table': i, 'type':'delete'}
		new_obj = write_client()
		result = new_obj.call(str(req))
		if(str(result) == "500"):
			return jsonify({}), 500
		result = ast.literal_eval(result.decode())
		del new_obj
	return result

# Reads the contents of the database on success and returns it, returns an error on failure
@app.route('/api/v1/db/read', methods = ['POST'])
def read_db():
	req = request.get_json()
	global counter
	counter += 1
	new_obj = read_client()
	result = new_obj.call(str(req))
	if(str(result) == "400"):
		abort(400)
	if(str(result) == "500"):
		abort(500)
	result = ast.literal_eval(result.decode())
	del new_obj
	return jsonify(result)

# Writes into a database. Returns 500 on error
@app.route('/api/v1/db/write', methods = ['POST'])
def write_db():
	req = request.get_json()
	new_obj = write_client()
	result = new_obj.call(str(req))
	if(str(result) == "500"):
		return jsonify({}), 500
	result = ast.literal_eval(result.decode())
	del new_obj
	return result

# Meant to kill master node
@app.route('/api/v1/crash/master', methods = ['POST'])
def kill_master():
	global active_containers
	global prev_children
	global deleted_master
	client = docker.from_env()
	req = request.get_json()
	pid = active_containers["master"]
	try:
		for i in client.containers.list():
			if(str(pid) == i.top()['Processes'][0][2]):
				deleted_master = True
				i.kill()
				for k,v in active_containers.items():
					if(v == str(pid)):
						key = k
				del active_containers[key]
		return jsonify([str(pid)])
	except:
		return jsonify({}), 500

# Kills the slave worker running and spawns a new slave
@app.route('/api/v1/crash/slave', methods = ['POST'])
def kill_slave():
	global active_containers
	global prev_children
	global not_called_by_scale

	client = docker.from_env()
	req = request.get_json()
	pid_list = []
	
	# Creates a list of slave PIDS
	for i in active_containers:
		if(i != "master"):
			pid_list.append(int(active_containers[i]))
	try:
		pid = sorted(pid_list)[-1]
	except:
		return jsonify({}), 500
	
	# Kills the highest slave PID and deletes its record in active containers
	try:
		for i in client.containers.list():
			if(str(pid) == i.top()['Processes'][0][2]):
				i.kill()
				for k,v in active_containers.items():
					if(v == str(pid)):
						key = k
				del active_containers[key]
		
		# Updates the children only in the case it was called by scaling function	
		if(not not_called_by_scale):
			prev_children = zk.get_children("/producer")
		
		return jsonify([str(pid)])
	except:
		return jsonify({}), 500


# Lists the PIDS of all the workers
@app.route('/api/v1/worker/list', methods = ['GET'])
def list_workers():
	global active_containers
	
	req = request.get_json()
	pid_list = []

	for i in active_containers:
		pid_list.append(int(active_containers[i]))
	
	return jsonify(sorted(pid_list))


# The API responsible for handling auto-scaling of workers based on requests
@app.route('/api/v1/scale-check', methods = ['GET'])
def scale_check():
	global counter
	global prev_children
	global active_containers
	global not_called_by_scale

	# Gets the number of expected and present
	count = counter//20
	client = docker.from_env()
	no_of_containers = len(client.containers.list()) - 4
	
	# If requested count of slaves is higher than current
	if(count >= no_of_containers):
		while count >= no_of_containers:
			# Updates the children list
			prev_children = zk.get_children("/producer")
			prev_child = prev_children
			
			# Starts a new slave
			temp = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
			time.sleep(8)
			
			# Gets a list of new slave workers spawned and updates its properties in active_containers
			all_children = zk.get_children("/producer")
			new_child = list(set(all_children) - set(prev_child))
			
			for i in new_child:
				active_containers[i] = temp.top()['Processes'][0][2]
			
			count -= 1
	else:
		# Called to downscale if requested count of slaves is lower than current
		if(len(client.containers.list()) > 5):
			not_called_by_scale = False
			requests.post("http://10.0.2.4/api/v1/crash/slave", json = {})

	prev_children = zk.get_children("/producer")
	return jsonify({})

# Starts the scheduler
threading.Thread(target=executioner).start()

if __name__ == '__main__':
	app.run(debug=True, port = '80', host = '0.0.0.0', use_reloader=False)