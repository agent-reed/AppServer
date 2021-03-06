from flask import Flask, jsonify, session, request, redirect, render_template

from user import User

import bcrypt
import db
import calcs
import push
import fetchdata

app = Flask(__name__)
app.debug = True

class Bug:

	def __init__(self, description, date, device):
		self.description = description
		self.date = date
		self.device = device    
		print("new bug found")

def isLoggedin():
	try:
		if session["loggedin"] == True:
			return True
		else:
			return False

	except:
		return False

# create the vars that we use for the sessions
def createSession(userID):
	session["loggedin"] = True
	session["userID"] = userID

def hashPassword(psswrd):
	return bcrypt.hashpw(psswrd.encode(), bcrypt.gensalt().encode())

def checkPassword(passwrd, hashedPass):
	print("Checking Password...")
	return hashedPass.encode() == bcrypt.hashpw(passwrd.encode(), hashedPass.encode())

@app.route('/create/', methods=['POST'])
def createUser():
	if request.method == 'POST':

		try:
			print("Recived a POST request under Create")
			firstName = request.form['firstName']
			lastName = request.form['lastName']
			email = request.form['email']
			distributor = request.form['distributor']
			salesperson = request.form['salesperson']
			admin = request.form['admin']
			interest = request.form['interest']
			print("#### Recieved Interest: %s"%interest)

			psswrd = request.form['psswrd']
			hashed = hashPassword(psswrd)

			db.addUserToDB(firstName,lastName,email,distributor,salesperson,admin,interest,hashed)

			return 'Created a User'

		except Exception as err:
			print(err)

			return 'Unable to create a new user'

	else:
		return "Method Not Allowed"

@app.route('/bug/', methods=['POST'])
def bugReport():
	if request.method == 'POST':
		description = request.form['description']
		date = request.form['date']
		device = request.form['device']
		newBug = Bug(description, date, device)
		db.addBugToDB(newBug)
	
		print "Added a Bug"
		return "Added bug"

	else:
		return "Method Not Allowed"

@app.route('/')
def index():
	return redirect('http://www.magswitch.com.au')

app.secret_key = '087c38712m]43jvdsp[ew'
@app.route('/login/', methods=['GET','POST'])
def checkLogin():
	if request.method == 'GET':
		
		if isLoggedin():
			userID = str(session["userID"])
			newUser = User(userID)
			newUser.incrementLoginCount()
			newUser.updateHistory()
			# return "Welcome!"
			return jsonify(firstname=newUser.firstName,lastname=newUser.lastName,email=newUser.email,distributor=newUser.distributor, salesperson=newUser.salesperson, admin=newUser.admin, userid=newUser.userid, logincount=newUser.logincount, interest=newUser.interest), 201

		else:
			return '''
					<form action = "" method = "post">
						<p>Email: <input type ="text" name ="email" /></p>
						<p>Password: <input type ="text" name ="psswrd_attempt" /></p>
						<p><input type ="submit" value = "Login" /></p>
					</form>
	
					'''

	if request.method == 'POST':
		try:
			email = request.form['email']
			psswrd_attempt = request.form['psswrd_attempt']
			token = request.form['tokenid']
			print("Email: " + email)

			con = db.createDBConnection()
			cur = con.cursor()
			cur.execute("SELECT psswrd, userid FROM users WHERE \"email\" = %s", (email,))
			results = cur.fetchone()
			print("Results Fetched")

			if results[0] and results [1] == None:
				return "No username in DB", 404

			if checkPassword(psswrd_attempt, results[0]):
				print("Password Checks Out")
				userID = results[1]
				createSession(userID)
				newUser = User(userID)
				newUser.incrementLoginCount()
				newUser.updateHistory()
				# return "Welcome!"

				cur.execute("UPDATE users SET tokenid = %s WHERE email = %s", (token, email))
				con.commit()
				return jsonify(firstname=newUser.firstName,lastname=newUser.lastName,email=newUser.email,distributor=newUser.distributor, salesperson=newUser.salesperson, admin=newUser.admin, userid=newUser.userid, logincount=newUser.logincount, interest=newUser.interest), 201
			else:
				print("Incorrect Combination")
				return "Unauthorized", 403

		except Exception as err:
			print(err)
			return "An error occured with logging in.", 400


@app.route("/logout/", methods=['GET'])
def removeSession():
	session["loggedin"] = False
	session.clear()
	return "Logged Out"


@app.route("/product/", methods=['POST'])
def tagProduct():

	if request.method == 'POST':

		productid = request.form["productid"]
		name = request.form["name"]

		if isLoggedin():
			print("Somebody is logged in")
			userID = int(session["userID"])
			con = db.createDBConnection()
			cur = con.cursor()

			cur.execute("SELECT EXISTS(SELECT 1 FROM products WHERE productid=%s)", (productid,))
			result = cur.fetchone()
			if result[0] == False:
				cur.execute("INSERT INTO products VALUES(%s, %s, %s, %s, %s)", (productid, name, 1, 1, [userID,0]))
				con.commit()

			else:
				cur.execute("SELECT totalviews, users FROM products WHERE productid=%s", (productid,))
				result = cur.fetchone()
				total = result[0]
				users = result[1]
				print(users)
				print(userID)
				cur.execute("UPDATE products SET totalviews=%s WHERE productid=%s", (total+1, productid))

				if userID in users:
					print("User already in list")
				else:
					cur.execute("UPDATE products SET users = array_append(users,%s)", (userID,))

				con.commit()

			# cur.execute("UPDATE products SET totalviews=%s WHERE productid=%s", (23,productid))
			# cur.execute("INSERT INTO products (productid, name, totalviews) SELECT %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM products WHERE productid=%s)", (productid, name, 24, productid))

			return "Okay"

		else:
			return "Not logged in"

@app.route("/favorite/", methods=['GET', 'POST'])
def favorite():

	if request.method == 'GET':
		if isLoggedin():
			print("Somebody is logged in")
			userID = str(session["userID"])
			con = db.createDBConnection()
			cur = con.cursor()
			print("About to execute")
			cur.execute("SELECT favorites FROM users WHERE \"userid\" = %s", (userID,))
			print("executed")
			results = cur.fetchone()
			print("fetched")
			print(results[0])

			return str(results[0])
		else:
			return redirect('/login/')

	if request.method == 'POST':

		productid = request.form["productid"]

		if isLoggedin():
			userID = str(session["userID"])
			con = db.createDBConnection()
			cur = con.cursor()
			print("About to execute")
			cur.execute("UPDATE users SET favorites = array_append(favorites,%s) WHERE userid = %s", (productid,userID))
			con.commit()
			
			return "Added to favorites!"

		else:
			return redirect('/login/')

@app.route("/deleteFavorite/", methods=['POST'])
def deleteFavorite():

	if request.method == 'POST':

		productid = request.form["productid"]

		if isLoggedin():
			userID = str(session["userID"])
			con = db.createDBConnection()
			cur = con.cursor()
			print("About to execute")
			cur.execute("UPDATE users SET favorites = array_remove(favorites,%s) WHERE userid = %s", (productid,userID))
			con.commit()
			
			return "Removed from favorites"

		else:
			redirect('/login/')

@app.route("/interest/", methods=['POST'])
def updateInterests():

	print "Request Recieved"
	userid = request.form['userid']
	interest = request.form['interest']

	con = db.createDBConnection()
	cur = con.cursor()
	cur.execute("UPDATE users SET interest = %s WHERE userid = %s", (interest, userid))

	con.commit()

	print "Interest Changed"

	return "Successfully Updated Interests"

@app.route("/push/", methods=['GET','POST'])
def sendNotifications():

	error = None
	if request.method == 'GET':

		creator = render_template('notificationCreator.html', error = error)
		return creator

	if request.method == 'POST':
		message = request.form["message"]
		tokenString = request.form.getlist('tokens')
		username = request.form['username']
		password = request.form['password']
		link = request.form['link']

		error = None
		if username != 'magswitch' or password != 'pikachu':
			error = "Bad Credentials. Please try again."
			return render_template('notificationCreator.html', error=error)
		else:
			msg = push.pushNotificationByGroups(tokenString, message, link)
	
		return render_template('notificationCompletion.html', msg=msg)


@app.route("/calculate/", methods=['GET','POST'])
def calculateHoldingForce():

	print("Visted Calculate")
	error = None
	result = None
	if request.method == 'GET':
		print("recieved GET request")
		calcCreator = render_template('ForceCalculatorCenter.html', error = error, result = result)
		return calcCreator

	if request.method == 'POST':

		material = request.form["material"]
		print("recieved following request:")
		print("* Material: %s" %material)
		thickness = request.form["thickness"]
		print("* Thickness: %s" %thickness)
		width = request.form["width"]
		print("* Width: %s" %width)
		length = request.form["length"]
		print("* Length: %s" %length)
		condition = request.form["condition"]
		print("* Condition: %s" %condition)
		orientation = request.form["orientation"]
		print("* Orientation: %s" %orientation)
		mobile = request.form["mobile"]
		print("* Mobile: %s" %mobile)

		if mobile == "True":
			calcData = fetchdata.getDerekData(thickness,width,length,material,condition,orientation)
			print(calcData)
			return jsonify(calcData)

		if thickness < 0:
			error = "Negative thickness given - Cannot Calculate"
			return render_template('ForceCalculatorCenter.html', error = error, result = result)

		print("not mobile - showing page")

		result = calcs.holdingCalc(unit, material, thickness)
		calcCreator = render_template('ForceCalculatorCenter.html', error = error, result = result)
		return calcCreator


if __name__ == '__main__':
	app.run()

