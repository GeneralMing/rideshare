import pika
from func import *
import json
import ast
import time
import logging
import os 
from kazoo.client import KazooClient
from kazoo.client import KazooState
import sys
import uuid

logging.basicConfig()


# Creating unique ids for each worker and creating child path
a = str(uuid.uuid4())
master = True
var = a
pid = "/producer/" + var
error = False

# Create database schema
initialize()

# Open a connection with zookeeper
zk = KazooClient(hosts='10.0.2.3:2181')
zk.start()
if(zk.exists(pid)):
    zk.delete(pid, recursive=True)

# Check if a master worker already exists else create one with the uid as data
if(zk.exists("/producer/master")):
    master = False
    zk.create(pid, var.encode(), ephemeral = True)
else:
    zk.create("/producer/master", "master".encode(), ephemeral = True)



connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.0.2.2'))

channel = connection.channel()

# Database read function implementation
def read_from_database(req):
    table_name = req['table']

    # Check for where clauses
    try:
        where = req['where']
    except:
        where = "1"
    # Fetch list of columns
    columns = req['columns']

    # Build and execute the query. On error, return 400
    with sqlite3.connect("rideshare.db") as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        
        string = read(table_name, columns, where)
        
        try:
            cur.execute(string);
        except:
            return 400
        
        data = cur.fetchall()
        return json.dumps(data)

# Database write function implementation
def write_to_database(req):
    req_type = req['type']
    table_name = req['table']
    
    del req['table']
    del req['type']
    
    # Build and execute the query based on the type of query i.e insert or delete
    # Return 500 on error
    with sqlite3.connect("rideshare.db") as con:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        if(req_type == "delete"):
            string = delete(table_name, **req)
        elif(req_type == "write"):
            string = upsert(table_name, **req)
        try:
            cur.execute(string);
            return string
        except:
            return 500

# Sync function
def caller():
    # Open a new temporary connection with syncQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.0.2.2'))
    channel = connection.channel()

    # Get number of messages in the queue
    message_count = channel.queue_declare(queue='syncQ', durable = True).method.message_count
    
    # Max unack messages set to 1
    channel.basic_qos(prefetch_count=1)


    if(message_count == 0):
        connection.close()
        return None
    # Receive each message from the queue and sync the table based on it
    for method_frame, properties, body in channel.consume('syncQ'):
        
        sync_table(body)

        # Send ack for messages and requeue them
        channel.basic_ack(method_frame.delivery_tag)
        channel.basic_publish(exchange='sync', routing_key='syncQ', properties=pika.BasicProperties(delivery_mode = 2), body=str(body.decode()))
        if(method_frame.delivery_tag == message_count):
            break

    connection.close()


# Executes the syncQ messages
def sync_table(body):
    global error
    with sqlite3.connect("rideshare.db") as con:
        cur = con.cursor()
        try:
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(str(body.decode()))
        except:
            error = True

# Called on write and read queues
def on_request(ch, method, props, body):
    global error

    # Convert the message from string to a datatype based on string structure
    req = ast.literal_eval(body.decode())
    
    # Try block has all the writing code in case of a successful write
    # Except block has all the reading code and sync before reading
    # Delivery mode is set to two because of persistent messages
    try:
        req['type']
        ret = write_to_database(req)

        if(ret != 500):
            ch.basic_publish(exchange='sync', routing_key='syncQ', properties=pika.BasicProperties(delivery_mode = 2), body=str(ret))
            ret = json.dumps({})
    except:
        caller()
        ret = read_from_database(req)
        if(error):
            ret = 400

    # Sends a ack along with a response into the responseQ
    ch.basic_publish(exchange='independent',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id = props.correlation_id, content_type = "application/json"),body=str(ret))
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Set max unack messages to 1
channel.basic_qos(prefetch_count=1)

if(master):
    channel.basic_consume(queue='writeQ', on_message_callback=on_request)
channel.basic_consume(queue='readQ', on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()