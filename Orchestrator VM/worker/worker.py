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

a = str(uuid.uuid4())

logging.basicConfig()
master = True


var = a
pid = "/producer/" + var
error = False

initialize()

zk = KazooClient(hosts='10.0.2.3:2181')
zk.start()
if(zk.exists(pid)):
    zk.delete(pid, recursive=True)
if(zk.exists("/producer/master")):
    master = False
    zk.create(pid, var.encode(), ephemeral = True)
else:
    zk.create("/producer/master", "master".encode(), ephemeral = True)
#print("My id is: ", var)


connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.0.2.2'))

channel = connection.channel()

def read_from_database(req):
    table_name = req['table']
    try:
        where = req['where']
    except:
        where = "1"
    columns = req['columns']

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

def write_to_database(req):
    #print("in writer")
    req_type = req['type']
    table_name = req['table']
    del req['table']
    del req['type']
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

def caller():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='10.0.2.2'))
    channel = connection.channel()
    message_count = channel.queue_declare(queue='syncQ', durable = True).method.message_count
    channel.basic_qos(prefetch_count=1)
    #print("incaller")
    if(message_count == 0):
        connection.close()
        return None
    for method_frame, properties, body in channel.consume('syncQ'):
        sync_table(body)
        print(body)
        channel.basic_ack(method_frame.delivery_tag)
        channel.basic_publish(exchange='sync', routing_key='syncQ', properties=pika.BasicProperties(delivery_mode = 2), body=str(body.decode()))
        if(method_frame.delivery_tag == message_count):
            break
    #print("finished consuming")
    connection.close()



def sync_table(body):
    global error
    with sqlite3.connect("rideshare.db") as con:
        cur = con.cursor()
        try:
            #print("in table")
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(str(body.decode()))
            #print(body.decode())
            #print("hi")
        except:
            #print("hi2")
            error = True

def on_request(ch, method, props, body):
    global error
    req = ast.literal_eval(body.decode())
    try:
        req['type']
        ret = write_to_database(req)
        if(ret != 500):
            ch.basic_publish(exchange='sync', routing_key='syncQ', properties=pika.BasicProperties(delivery_mode = 2), body=str(ret))
            print("Published: ",str(ret))
            ret = json.dumps({})
    except:
        caller()
        #print("finished")
        ret = read_from_database(req)
        #print("in worker 1 with ", ret)
        if(error):
            ret = 400

    #print(str(req))
    #time.sleep(10)
    ch.basic_publish(exchange='independent',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id = props.correlation_id, content_type = "application/json"),body=str(ret))
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_qos(prefetch_count=1)
if(master):
    channel.basic_consume(queue='writeQ', on_message_callback=on_request)
channel.basic_consume(queue='readQ', on_message_callback=on_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()