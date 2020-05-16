#!/home/ubuntu/env/bin python3
from func import *

app=Flask(__name__)

request_count = 0

print("\n\n\n\n Running users.py \n\n\n\n")

# Returns the request count
@app.route('/api/v1/_count', methods = ['GET'])
def count_req():
	global request_count
	return jsonify([request_count])

# Resets the request count
@app.route('/api/v1/_count', methods = ['DELETE'])
def del_req():
	global request_count
	request_count = 0
	return jsonify({})

# Add a user in the application
@app.route('/api/v1/users', methods = ['PUT'])
def add_user():
	global request_count
	request_count += 1
	
	try:
		user_name = request.get_json()['username']
		password = request.get_json()['password']

		# Verify password validtity
		check_password(password)
	except:
		abort(400)

	# Get the list of existing users
	res = requests.get('http://localhost/api/v1/users')
	
	# Check for content or no content
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)

	count = 0

	# Check if the username exists in the database
	if(res.status_code != 204):
		for i in res.json():
			if(i == user_name):
				count += 1
	# On existance return a 400 error
	if(count != 0):
		abort(400)

	# Send request to write the user details into the database
	json_send = {'username': user_name, 'password': password, 'table': 'user_details', 'type':'write'}
	res = requests.post('http://localhost/api/v1/db/write', json=json_send)
	try:
		res.json()
	except:
		abort(500)
	return res.json(), 201

# Fetches the list of users
@app.route('/api/v1/users', methods = ['GET'])
def list_users():
	global request_count
	request_count += 1

	# Fetch the username of the existing users
	json_send = {'table': 'user_details', 'columns': ["username"]}
	res = requests.post('http://localhost/api/v1/db/read', json=json_send)
	
	try:
		res.json()
	except:
		abort(400)
	
	count = 0
	for i in res.json():
		count += 1
	
	user_list = []
	
	# If any users exist, return the list of users
	if(count > 0):
		for i in res.json():
			user_list.append(i[0])
	
		return jsonify(user_list)
	else:
		return jsonify({}), 204


# Deletes a user from the database
@app.route('/api/v1/users/<name>', methods = ['DELETE'])
def remove_user(name):
	global request_count
	request_count += 1

	# Fetch the list of users
	res = requests.get('http://localhost/api/v1/users')
	
	try:
		if(res.status_code != 204):
			res.json()
	except:
		abort(400)
	
	# Check if user exists in the database
	count = 0
	if(res.status_code != 204):
		for i in res.json():
			if(i == name):
				count += 1
	else:
		count += 1

	# Send a delete request to the database server
	if(count > 0):
		json_send = {'username': name, 'table': 'user_details', 'type':'delete'}
		res = requests.post('http://localhost/api/v1/db/write', json=json_send)
		try:
			res.json()
		except:
			abort(500)			
		return jsonify({})
	
	abort(400)

if __name__ == '__main__':
	app.run(debug=True, port = '80', host = '0.0.0.0')

