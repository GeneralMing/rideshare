from flask import Flask, render_template, jsonify, request, abort
import requests
import sqlite3
import re
import json
import csv
import datetime

filename = "AreaNameEnum.csv"
fields = []
rows = []
cols1 = []
cols2 = []

with open(filename, 'r') as csvfile:
	csvreader = csv.reader(csvfile)
	fields = next(csvreader) 
	for row in csvreader:
		cols1.append(row[0])
		cols2.append(row[1])

def initialize():
	try:
		conn = sqlite3.connect('rideshare.db')
	except:
		abort(500)
	cur = conn.cursor()
	cur.execute("PRAGMA foreign_keys = ON;")
	cur.execute("CREATE TABLE IF NOT EXISTS user_details(username varchar(50) primary key, password varchar(41) not null);")
	cur.execute("CREATE TABLE IF NOT EXISTS rides(username varchar(50), source varchar(100) not null, destination varchar(100) not null, timess text not null, ride_id integer not null primary key autoincrement, foreign key (username) references user_details (username) on delete cascade);")
	cur.execute("CREATE TABLE IF NOT EXISTS ride_join(username varchar(50), ride_id integer, foreign key (username) references user_details (username) on delete cascade, foreign key (ride_id) references rides (ride_id) on delete cascade);")


def read(table, args, where = "1"):
	columns = ""
	for i in args:
		columns += i + ', '
	columns = columns[:-2]
	sql = list()
	sql.append("SELECT " + columns)
	sql.append(" FROM %s" % table)
	sql.append(" WHERE " + where)
	sql.append(";")
	return "".join(sql)


def upsert(table, **kwargs):
    keys = ["%s" % k for k in kwargs]
    values = ["'%s'" % v for v in kwargs.values()]
    sql = list()
    sql.append("INSERT OR REPLACE INTO %s (" % table)
    sql.append(", ".join(keys))
    sql.append(") VALUES (")
    sql.append(", ".join(values))
    sql.append(")")
    sql.append(";")
    return "".join(sql)


def delete(table, **kwargs):
    sql = list()
    sql.append("DELETE FROM %s " % table)
    sql.append("WHERE " + " AND ".join("%s = '%s'" % (k, v) for k, v in kwargs.items()))
    sql.append(";")
    return "".join(sql)

def engineer(time):
	arr = time.split(':')
	date = arr[0]
	date = date.split("-")
	time = arr[1]
	time = time.split('-')
	entry = date[2] + "-" + date[1] + '-' + date[0] + " " + time[2] + "-" + time[1] + "-" + time[0]
	return entry

def reverse_engineer(time):
	arr = time.split(" ")
	date = arr[0]
	date = date.split('-')
	date.reverse()
	time = arr[1]
	time = time.split('-')
	time.reverse()
	exit = ""
	for i in date:
		exit += i + "-"
	exit = exit[:-1]
	exit += ":"
	for i in time:
		exit += i + "-"
	exit = exit[:-1]
	return exit

def check_password(passwd):
	if(re.fullmatch('[0-9abcdef]{40}', passwd) == None):
		abort(400)

def check_date(date):
	date = date.split(':')
	if(re.fullmatch('^(0[1-9]|[1-2][0-9]|(3)[0-1])-(((0)[13578])|((1)[02]))-\d{4}$', date[0])):
		pass
	elif(re.fullmatch('^(0[1-9]|[1-2][0-9]|30)-(((0)[469])|((1)[1]))-\d{4}$', date[0])):
		pass
	elif(re.fullmatch('^(0[1-9]|2[0-8]|1[0-9])-(((0)[2]))-\d{4}$', date[0])):
		pass
	elif(re.fullmatch('^(0[1-9]|2[0-9]|1[0-9])-(((0)[2]))-\d{4}$', date[0])):
		string = date[0].split("-")
		if((int(string[2])%4 == 0) and (int(string[2])%100 != 0) or (int(string[2])%400 == 0)):
			pass
		else:
			abort(400)
	else:
		abort(400)


	if(None == re.fullmatch('^[0-5][0-9]-[0-5][0-9]-([0-1][0-9]|[2][0-3])', date[1])):
		abort(400)
def check_current_time(string):
	current_time = datetime.datetime.now()
	string = string.split(":")
	string[0] = string[0].split("-")
	string[1] = string[1].split("-")
	given_time = datetime.datetime(int(string[0][2]), int(string[0][1]), int(string[0][0]), int(string[1][2]), int(string[1][1]), int(string[1][0]), 000000)
	if(given_time >= current_time):
		return True
	else:
		return False