#!/home/ubuntu/env/bin python3
from func import *

app=Flask(__name__)

request_count = 0

print("\n\n\n\n Running users.py \n\n\n\n")

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
			string = delete('user_details')[:-1] + "1;"
			cur.execute(string)
			return jsonify({})
		except:
			abort(500)
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

@app.route('/api/v1/users', methods = ['PUT'])
def add_user():
	global request_count
	request_count += 1
	try:
		user_name = request.get_json()['username']
		password = request.get_json()['password']
		check_password(password)
	except:
		abort(400)
	res = requests.get('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/users')
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)
	count = 0
	if(res.status_code != 204):
		print(res.json())
		for i in res.json():
			if(i == user_name):
				count += 1
	if(count != 0):
		abort(400)
	json_send = {'username': user_name, 'password': password, 'table': 'user_details', 'type':'write'}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
	try:
		res.json()
	except:
		abort(500)
	return res.json(), 201


@app.route('/api/v1/users', methods = ['GET'])
def list_users():
	global request_count
	request_count += 1
	json_send = {'table': 'user_details', 'columns': ["username"]}
	res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/read', json=json_send)
	try:
		res.json()
	except:
		abort(400)
	count = 0
	for i in res.json():
		count += 1
	user_list = []
	if(count > 0):
		for i in res.json():
			user_list.append(i[0])
		return jsonify(user_list)
	else:
		return jsonify({}), 204



@app.route('/api/v1/users/<name>', methods = ['DELETE'])
def remove_user(name):
	global request_count
	request_count += 1
	res = requests.get('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/users')
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)
	count = 0
	if(res.status_code != 204):
		print(res.json())
		for i in res.json():
			if(i == name):
				count += 1
	else:
		count += 1
	if(count > 0):
		json_send = {'username': name, 'table': 'user_details', 'type':'delete'}
		res = requests.post('http://test-855239080.us-east-1.elb.amazonaws.com/api/v1/db/write', json=json_send)
		try:
			res.json()
		except:
			abort(500)			
		return jsonify({})
	abort(400)

if __name__ == '__main__':
	app.run(debug=True, port = '80', host = '0.0.0.0')

