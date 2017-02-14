from flask import Flask
from flask import request

app = Flask(__name__)

from spark.session import Session
from spark.messages import Message
from spark.rooms import Room
import requests
import json
import os

# #Below needed for GMAIL
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

token = os.environ['SPARK_BOT_TOKEN']
url = 'https://api.ciscospark.com'
session = Session(url, token)
auth = "Bearer %s" % token

domain = os.environ['MG_DOMAIN']

mg_key = os.environ['MG_KEY']
mg_url = 'https://api.mailgun.net/v3/{0}/messages'.format(domain)

email_from = os.environ['MG_EMAIL']

def whoAmI(auth, token):
    url = 'https://api.ciscospark.com/v1/people/me'
    headers = {'content-type':'applicaiton/json', 'authorization':auth}

    response = requests.request("GET", url, headers=headers)

    me = json.loads(response.content)

    name = me['displayName'].split()[0]
    print("I am {}".format(name))
    return name

name = whoAmI(auth, token)


def help():
    response = "Here is what I can do:\n" \
               "-email - send email to everyone in the room\n" \
               "-subject - set subject\n" \
               "-content - set content of email\n" \
               "\n" \
               "Example:\n" \
               "-email -subject 'example' -content 'content'"
    return response

def getRoomName(roomId):
    url = "https://api.ciscospark.com/v1/rooms/{}".format(roomId)

    headers = {
        'authorization': auth,
        'cache-control': "no-cache",
        'content-type': 'application/json'
    }
    response = requests.request("GET", url, headers=headers)
    room = json.loads(response.content)
    return room['title']


def getSubject(message_text, message):

    mgs = message_text.split('-')
    for i in mgs:
        if i.split()[0] == 'subject':
            print(i)
            begin = i.index('\'') + 1
            end = i.rfind('\'')
            subject = i[begin:end]
            break
    if 'subject' not in locals():
        print(message.roomId)
        subject = "From Spark Room {}".format(getRoomName(message.roomId))

    return subject

def getContent(message_text):

    mgs = message_text.split('-')
    for i in mgs:
        if i.split()[0] == 'content':
            print(i)
            begin = i.index('\'') + 1
            end = i.rfind('\'')
            content = i[begin:end]
            break
        else:
            content = None

    return content

def getUsers(roomId):
    url = "https://api.ciscospark.com/v1/memberships"
    querystring = {"roomId": roomId}

    headers = {
        'authorization': auth,
        'cache-control': "no-cache",
        'content-type': 'application/json'
    }
    response = requests.request("GET", url, headers=headers, params=querystring)
    users = json.loads(response.content)
    users = users[u'items']
    user_list = []
    for user in users:
        ##Ignore monitor bots
        if user[u'isMonitor'] == False:
            # user_list.append(str(user['personId']))
            if user['personEmail'].split('@')[1] != "sparkbot.io":
                user_list.append(user['personEmail'])
    return user_list

def getRecipients(message):
    roomid = message.roomId
    users = getUsers(roomid)
    return users

def sendEmail(subject, content, recipients):

    response = requests.post(
        mg_url,
        auth=('api', mg_key),
        data={
        'from': email_from,
        'to': recipients,
        'subject': subject,
        'text': content
    })

    print(response)
    return

# def sendGmail(subject, content, recipients):
#     sender = gmail_sender
#     password = gmail_password
#
#     msg = MIMEMultipart('alternitive')
#     msg['Subject'] = subject
#     msg['From'] = sender
#     msg['To'] = ", ".join(recipients)
#
#     print(msg['To'])
#
#     body = MIMEText(content)
#     msg.attach(body)
#
#     server = smtplib.SMTP()
#     server.connect('smtp.gmail.com',587)
#     server.ehlo()
#     server.starttls()
#     server.login(gmail_sender, gmail_password)
#     server.sendmail(msg['From'], msg['To'].split(","), msg.as_string())
#
#     print("sent via gmail")
#     return

def buildEmail(message, message_text):
    subject = getSubject(message_text, message)
    content = getContent(message_text)
    recipients = getRecipients(message)

    response = 'Email sent:\n' \
               'to:{2}\n' \
               'subject "{0}"\n' \
               'content "{1}"'.format(subject, content, recipients)

    if content != None:
        print("Content Found - Sending email")
        sendEmail(subject, content, recipients)
    else:
        print("Error - User - empty content")
        response = 'You must specify content\n\n' + help()
    return response

@app.route("/api/injest", methods=['POST'])
def injest():
    data = request.get_json()
    message_id = data['data']['id']

    message = Message.get(session, message_id)
    message_text = message.attributes['text']

    msg = message_text.split(name)
    msg = msg[1].strip()

    print(msg)


    if msg.split()[0] == '-email':
        response = buildEmail(message, message_text)
        spark_msg = response
    else:
        response = help()
        spark_msg = response


    room = Room(attributes={'id':message.roomId})
    room.send_message(session, spark_msg)


    return(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)