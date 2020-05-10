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


connection = pika.BlockingConnection(pika.ConnectionParameters('10.0.2.2'))
channel = connection.channel()


channel.exchange_declare(exchange = 'independent', exchange_type = 'direct')
channel.exchange_declare(exchange = 'sync', exchange_type = 'direct')



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


class read_client(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(host='10.0.2.2'))

		self.channel = self.connection.channel()

		self.callback_queue = "responseQ"

		self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)

	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	def call(self, n):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		self.channel.basic_publish(exchange='independent', routing_key='readQ', properties=pika.BasicProperties(reply_to=self.callback_queue, correlation_id=self.corr_id, content_type = "application/json"),body=str(n))
		while self.response is None:
			self.connection.process_data_events()
		self.connection.close()
		return self.response

class write_client(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(host='10.0.2.2'))

		self.channel = self.connection.channel()

		self.callback_queue = "responseQ"

		self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.on_response, auto_ack=True)

	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	def call(self, n):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		self.channel.basic_publish(exchange='sync', routing_key='writeQ', properties=pika.BasicProperties(reply_to=self.callback_queue, correlation_id=self.corr_id, content_type = "application/json"),body=str(n))
		while self.response is None:
			self.connection.process_data_events()
		self.connection.close()
		return self.response

logging.basicConfig()

client = docker.from_env()

not_called_by_scale = True
deleted_master = False

zk = KazooClient(hosts='10.0.2.3:2181')
zk.start()
active_containers = {}

if(zk.exists("/producer")):
	zk.delete("/producer", recursive = True)

zk.ensure_path("/producer")

temp1 = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
time.sleep(10)
temp = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
time.sleep(10)
prev_children = zk.get_children("/producer")

active_containers["master"] = temp1.top()['Processes'][0][2]
for i in prev_children:
	if(i != "master"):
		active_containers[i] = temp.top()['Processes'][0][2]

#print(prev_children)
#print(active_containers)

@zk.ChildrenWatch("/producer")
def watch_children(children):
	global not_called_by_scale
	global deleted_master
	if(not_called_by_scale):
		global prev_children
		global active_containers
		deleted_child = list(set(prev_children) - set(children))
		#print(deleted_child)
		#print(prev_children)
		if(deleted_child != []):
			for i in deleted_child:
				#print(i)
				#print(active_containers)
				try:
					del active_containers[i]
				except:
					pass
				temp = client.containers.run("worker", auto_remove = True, detach = True, network = "cry_cloud")
				time.sleep(8)
				all_children = zk.get_children("/producer")
				new_child = list(set(all_children) - set(children))
				for i in new_child:
					if(deleted_master):
						active_containers["master"] = temp.top()['Processes'][0][2]
						deleted_master = False
					else:
						active_containers[i] = temp.top()['Processes'][0][2]
			#print(active_containers)
	else:
		not_called_by_scale = True
	prev_children = zk.get_children("/producer")

counter = 0

def reset():
	global counter
	if counter!= 0:
		counter = 0

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

@app.route('/api/v1/db/read', methods = ['POST'])
def read_db():
	req = request.get_json()
	global counter
	counter += 1
	new_obj = read_client()
	result = new_obj.call(str(req))
	#print(result)
	if(str(result) == "400"):
		abort(400)
	if(str(result) == "500"):
		abort(500)
	result = ast.literal_eval(result.decode())
	del new_obj
	return jsonify(result)

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
		prev_children = zk.get_children("/producer")
		return jsonify([str(pid)])
	except:
		return jsonify({}), 500

@app.route('/api/v1/crash/slave', methods = ['POST'])
def kill_slave():
	global active_containers
	global prev_children
	client = docker.from_env()
	req = request.get_json()
	pid_list = []
	print(active_containers)
	for i in active_containers:
		if(i != "master"):
			pid_list.append(int(active_containers[i]))
	try:
		print(pid_list)
		pid = sorted(pid_list)[-1]
	except:
		return jsonify({}), 500
	#	print("hi")
	try:
		print(active_containers)
		for i in client.containers.list():
			if(str(pid) == i.top()['Processes'][0][2]):
				i.kill()
				for k,v in active_containers.items():
					if(v == str(pid)):
						key = k
				del active_containers[key]
		prev_children = zk.get_children("/producer")
		return jsonify([str(pid)])
	except:
		return jsonify({}), 500

@app.route('/api/v1/worker/list', methods = ['GET'])
def list_workers():
	global active_containers
	req = request.get_json()
	pid_list = []
	for i in active_containers:
		pid_list.append(int(active_containers[i]))
	return jsonify(sorted(pid_list))

@app.route('/api/v1/scale-check', methods = ['GET'])
def scale_check():
	global counter
	global prev_children
	global active_containers
	global not_called_by_scale
	#print("The number of incoming HTTP request at the moment: ", counter)
	
	count = counter//20
	#lower_range = count*20+1
	#upper_range = lower_range+19
	client = docker.from_env()
	no_of_containers = len(client.containers.list()) - 4
	if(count >= no_of_containers):
		while count >= no_of_containers:
			prev_children = zk.get_children("/producer")
			prev_child = prev_children
			#print(prev_children)
			temp = client.containers.run("worker", detach = True, auto_remove = True, network = "cry_cloud")
			time.sleep(8)
			all_children = zk.get_children("/producer")
			#print(all_children)
			new_child = list(set(all_children) - set(prev_child))
			#print("new child: ", new_child)
			for i in new_child:
				#print(active_containers)
				active_containers[i] = temp.top()['Processes'][0][2]
				#print(active_containers)
			count -= 1
	else:
		if(len(client.containers.list()) > 5):
			not_called_by_scale = False
			requests.post("http://10.0.2.4/api/v1/crash/slave", json = {})


	prev_children = zk.get_children("/producer")
	#reset_counter()
	return jsonify({})

threading.Thread(target=executioner).start()

if __name__ == '__main__':
	app.run(debug=True, port = '80', host = '0.0.0.0', use_reloader=False)