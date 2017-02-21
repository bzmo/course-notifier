import requests
import smtplib
import filecmp, os
import datetime
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)

ADM_URL = 'http://www.adm.uwaterloo.ca/cgi-bin/cgiwrap/infocour/salook.pl'

# Email constants
FROM_ADDR = "bomouniversity@gmail.com"
PASSWORD = "Some Password"
TO_ADDR = "bzmo@uwaterloo.ca"

# Course Selection constants
CODE = "246"
SUBJECT = "CS"
LEVEL = "under" # under for undergraduate course

# File Name Constants
TMP_FILE = "tmp.log"
LOG_FILE = "email.log"

# Table Indices Constants
CLASS_NUM = 0
CLASS_ENROLL_CAP = 6
CLASS_ENROLL_TOT = 7
CLASS_SECTION = 1
CLASS_TIME = 10

# Lecture Object Keys
ENROLL_CAP = "enroll_cap"
ENROLL_TOT = "enroll_tot"
ENROLL_SECTION = "enroll_sec"
ENROLL_TIME = "enroll_time"


@app.route('/notify', methods=['POST'])
def show_post():
	CODE = request.form['code']
	SUBJECT = request.form['subject']
	LEVEL = request.form['level']
	TO_ADDR = request.form['address']

	main()

"""
@app.route('/test', methods=['GET'])
def test_route():
	f = open("submit.html")
	data = f.read()
	f.close()
	return data
"""



def send_email(body, info):
	print "Sending e-mail..."

	fromaddr = info["fromaddr"]
	toaddr = info["toaddr"]
	password = info["password"]
	msg = MIMEMultipart()
	msg['From'] = fromaddr
	msg['To'] = toaddr
	msg['Subject'] = "Classes update for " + SUBJECT + CODE

	msg.attach(MIMEText(body, 'plain'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(fromaddr, password)
	text = msg.as_string()
	server.sendmail(fromaddr, toaddr, text)
	server.quit()

	print "E-mail sent!"


def get_url(params):
	level = params['level']
	sess = params['sess']
	subject = params['subject']
	cournum = params['cournum']

	return ADM_URL + "?" + "level=" + level + "&sess=" + sess + "&subject=" + subject + "&cournum=" + cournum

def get_lectures(params):

	# GET Request to retrieve HTML doc
	url = get_url(params)
	req = requests.get(url)

	# Parse the HTML to retrieve the relevant table data
        soup = BeautifulSoup(req.content, 'html.parser')
	results =  soup.find_all('table')[0].find_all('table')[0].find_all('tr')
	del results[0] # 1st line contains irrelevant details

	lectures = [] # Keep track of lecture objects

	for result in results:
		result = result.findAll('td')
		class_type = result[CLASS_SECTION].get_text().split(' ')[0] # Ex. LEC 001 becomes splits into 'LEC' '001'

		# Exclude rows that are not "LEC" types
		if len(result) != 13 or class_type != "LEC":
			continue

		lecture = {}
		lecture[ENROLL_SECTION] = result[CLASS_SECTION].get_text().split(' ')[1]
		lecture[ENROLL_CAP] = int(result[CLASS_ENROLL_CAP].get_text())
		lecture[ENROLL_TOT] = int(result[CLASS_ENROLL_TOT].get_text())
		lecture[ENROLL_TIME] = result[CLASS_TIME].get_text()
		lectures.append(lecture)

	return lectures


def get_message(open_lectures):

	# msg that we are returning
	msg = SUBJECT + CODE + "\n\n"

	if open_lectures == []:
		msg += "No classes are currently open."
	else:
		msg = SUBJECT + CODE + "\n\n"

		for lecture in open_lectures:
			section = lecture[ENROLL_SECTION]
			cap = str(lecture[ENROLL_CAP])
			tot = str(lecture[ENROLL_TOT])
			time = lecture[ENROLL_TIME]
			msg += "Section %(s)s is open : %(t)s/%(c)s on %(m)s\n" % { "s" : section,
										 "t" : tot,
										 "c" : cap,
										 "m": time }

	return msg


def get_params():
	now = datetime.datetime.now()
	year = now.year % 100
	month = (now.month - 1) / 4 * 4 + 1 # Either Jan, May, Sep
	params = { 'sess' : "1" + str(year) + str(month),
          'subject' : SUBJECT,
          'cournum' : CODE,
          'level' : LEVEL
        }
	return params


def get_email_info():
	email_info = { "fromaddr" : FROM_ADDR,
        		"toaddr" : TO_ADDR,
			"password" : PASSWORD
	}

	return email_info

def main():

	params = get_params()
	email_info = get_email_info()
	lectures = get_lectures(params)
	open_lectures = [] # Keep track of open lectures

	f = open(TMP_FILE, 'w')

	# Scan through each lecture to check if any are open
	for lecture in lectures:
		section = lecture[ENROLL_SECTION]
		capacity = lecture[ENROLL_CAP]
		enrolled = lecture[ENROLL_TOT]

		if enrolled < capacity:
			open_lectures.append(lecture)
			f.write(section + '\n') # Write to temp log file

	f.close() # Close file stream to finish writing

	log_exists = os.path.isfile(LOG_FILE)

	# Only send an e-mail if the # of open classes has changed and is > 0
	if (open_lectures != [] and not log_exists or (log_exists and not filecmp.cmp(TMP_FILE, LOG_FILE, False))):
		msg = get_message(open_lectures)
		send_email(msg, email_info)

	os.rename(TMP_FILE, LOG_FILE)

if __name__ == "__main__":
	main()
