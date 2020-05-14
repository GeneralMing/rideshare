#!/home/ubuntu/env/bin python3
from func import *
app=Flask(__name__)

request_count = 0


print("\n\n\n\n Running rides.py \n\n\n\n")
"""
@app.route('/api/v1/db/write', methods = ['POST'])
def write_db():
	req = request.get_json()
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
			return jsonify({})
		except:
			abort(500)

@app.route('/api/v1/db/read', methods = ['POST'])
def read_db():
	req = request.get_json()

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
			abort(400)
		data = cur.fetchall()
		return json.dumps(data)


@app.route('/api/v1/db/clear', methods = ['POST'])
def clear_db():
	with sqlite3.connect("rideshare.db") as con:
		cur = con.cursor()
		cur.execute("PRAGMA foreign_keys = ON;")
		try:
			string = delete('ride_join')[:-1] + "1;"
			cur.execute(string)
			string = delete('rides')[:-1] + "1;"
			cur.execute(string)
		except:
			abort(500)
	res = requests.post("http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/clear", json = {})
	if(res.status_code == 200):
		return  jsonify({})
	else:
		abort(405)



@app.route('/api/v1/db/clear', methods = ['POST'])
def clear_db():
	with sqlite3.connect("rideshare.db") as con:
		cur = con.cursor()
		cur.execute("PRAGMA foreign_keys = ON;")
		try:
			string = delete('ride_join')[:-1] + "1;"
			cur.execute(string)
			string = delete('rides')[:-1] + "1;"
			cur.execute(string)
		except:
			abort(500)
	res = requests.post("http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/clear", json = {})
	if(res.status_code == 200):
		return  jsonify({})
	else:
		abort(405)

"""

@app.route('/api/v1/_count', methods = ['GET'])
def count_req():
	global request_count
	return jsonify([request_count])

@app.route('/api/v1/_count', methods = ['DELETE'])
def del_req():
	global request_count
	request_count = 0
	return jsonify({})

@app.route('/api/v1/db/clear', methods = ['POST'])
def clear_db():
	global request_count
	request_count += 1
	res = requests.post("http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/clear", json = {})
	if(res.status_code == 200):
		return  jsonify({})
	else:
		abort(500)


@app.route('/api/v1/rides', methods = ['POST'])
def new_ride():
	global request_count
	request_count += 1
	user_name = request.get_json('created_by')
	timestamp = request.get_json('timestamp')
	source = request.get_json('source')
	destination = request.get_json('destination')
	if(str(source['source']) not in cols1):
		abort(400)
	if(str(destination['destination']) not in cols1):
		abort(400)

	time = timestamp["timestamp"]
	check_date(time)
	entry = engineer(time)
	if(cols2[int(source['source']) - 1] == cols2[int(destination['destination']) - 1]):
		return jsonify({}), 400
	res = requests.get('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/users')
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)
	count = 0
	if(res.status_code != 204):
		for i in res.json():
			if(i == user_name['created_by']):
				count += 1
	if(count > 0):
		json_send = {'username': user_name['created_by'], 'source': cols2[int(source['source']) - 1], 'destination': cols2[int(destination['destination']) - 1], 'timess': entry, 'table': 'rides', 'type':'write'}
		res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
		try:
			res.json()
		except:
			abort(400)
		return jsonify({}), 201
	abort(400)

@app.route('/api/v1/rides', methods = ['GET'])
def get_ride():
	global request_count
	request_count += 1
	source = request.args.get('source')
	destination = request.args.get('destination')
	if(str(source) not in cols1):
		abort(400)
	if(str(destination) not in cols1):
		abort(400)
	ride_holder = []
	json_send = {'table': 'rides', 'columns': ["*"], "where": "source = '" + cols2[int(source) - 1] + "' and destination = '" + cols2[int(destination) - 1] + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	for i in res.json():
		ride_holder.append({'rideId': i[4], 'username': i[0], 'timestamp': reverse_engineer(i[3])})
	if(ride_holder == []):
		return jsonify(ride_holder), 204
	refine = []
	for i in ride_holder:
		if(check_current_time(i['timestamp'])):
			refine.append(i)
	return jsonify(refine)


@app.route('/api/v1/rides/<ride_id>', methods = ['GET'])
def list_ride(ride_id):
	ride_holder = []
	users = []

	global request_count
	request_count += 1

	json_send = {'table': 'rides', 'columns': ["*"], "where": "ride_id = '" + str(ride_id) + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	count = 0
	for i in res.json():
		count += 1
	if(count == 0):
		return jsonify({}), 204
	json_send = {'table': 'ride_join', 'columns': ["*"], "where": "ride_id = '" + str(ride_id) + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	for i in res.json():
		users.append(i[0])
	json_send = {'table': 'rides', 'columns': ["*"], "where": "ride_id = '" + str(ride_id) + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	for i in res.json():
		ride_holder.append({'rideId': i[4], 'created_by': i[0], 'timestamp': reverse_engineer(i[3]),'users': list(set(users)), 'source': i[1], 'destination': i[2]})
	return jsonify(ride_holder[0])

@app.route('/api/v1/rides/<ride_id>', methods = ['POST'])
def join_ride(ride_id):
	global request_count
	request_count += 1
	json_send = {'table': 'rides', 'columns': ["*"], "where": "ride_id = '" + str(ride_id) + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	count = 0
	for i in res.json():
		count += 1
	if(count == 0):
		return jsonify({}), 204
	username = request.get_json('username')['username']
	res = requests.get('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/users')
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)
	count = 0
	if(res.status_code != 204):
		for i in res.json():
			if(i == username):
				count += 1
	if(count > 0):
		json_send = {'username': username, 'ride_id': str(ride_id), 'table': 'ride_join', 'type':'write'}
		res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
		try:
			res.json()
		except:
			abort(400)
		return jsonify({})

@app.route('/api/v1/rides/<ride_id>', methods = ['DELETE'])
def delete_ride(ride_id):

	global request_count
	request_count += 1

	json_send = {'table': 'rides', 'columns': ["*"], "where": "ride_id = '" + str(ride_id) + "'"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	count = 0
	for i in res.json():
		count += 1
	if(count == 0):
		return jsonify({}), 204
	json_send = {'ride_id': str(ride_id), 'table': 'ride_join', 'type':'delete'}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	json_send = {'ride_id': str(ride_id), 'table': 'rides', 'type':'delete'}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
	try:
		res.json()
	except:
		abort(500)
	return jsonify({})

@app.route('/api/v1/rides/count', methods = ['GET'])
def num_rides():
	global request_count
	request_count += 1

	json_send = {'table': 'rides', 'columns': ["*"], "where": "1"}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	count = 0
	for i in res.json():
		count += 1
	return jsonify([count])


if __name__ == '__main__':
	app.run(debug=False, port = '80', host = '0.0.0.0')
