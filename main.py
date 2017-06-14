from flask import Flask
from flask import request
from spark.session import Session
from spark.messages import Message
from spark.rooms import Room
import requests
import json
import os
import sys
import base64

app = Flask(__name__)



# #Below needed for GMAIL
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart

version = '0.6'

token = os.environ['SPARK_BOT_TOKEN']
url = 'https://api.ciscospark.com'
session = Session(url, token)
auth = "Bearer %s" % token

domain = os.environ['MG_DOMAIN']

mg_key = os.environ['MG_KEY']
mg_url = 'https://api.mailgun.net/v3/{0}/messages'.format(domain)

email_from = os.environ['MG_EMAIL']


support_email = os.environ['SPARKMAIL_SUPPORT_EMAIL']
support_link = os.environ['SPARKMAIL_SUPPORT_LINK']




def whoAmI(auth, token):
    url = 'https://api.ciscospark.com/v1/people/me'
    headers = {'content-type':'applicaiton/json', 'authorization':auth}

    response = requests.request("GET", url, headers=headers)

    me = json.loads(response.content)

    name = me['displayName'].split()[0]
    print("I am {}".format(name))
    return name



def myID(auth, token):
    url = 'https://api.ciscospark.com/v1/people/me'
    headers = {'content-type':'applicaiton/json', 'authorization':auth}

    response = requests.request("GET", url, headers=headers)

    me = json.loads(response.content)

    myid = me['id']
    #print("I am {}".format(name))
    return myid


name = whoAmI(auth, token)
myid = myID(auth, token)

commands = {
    "/exclude": "Exclude an email domain. ex: {} /exclude(@cisco.com) Message".format(name),
}

def help():
    response = "Hello, I'm {0} Bot.  Just tag me with a message and I will send the content of the message via email to all members of the Spark Space.  \n\nE.G: @{1} Send this message via email!".format(name, name)
    for c in commands:
        response = response + "\n I also understand the command {0}: {1} ".format(c, commands[c])
    
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

def getRoomURL(roomId):
    basedecode = base64.b64decode(roomId)
    sys.stderr.write(basedecode.decode('utf-8'))
    roomurl = basedecode.decode('utf-8').split('/')[-1]
    fullurl = "https://web.ciscospark.com/rooms/{}/chat".format(roomurl)
    return fullurl


def getSubject(message_text, message):

    # mgs = message_text.split('-')
    # for i in mgs:
    #     if i.split()[0] == 'subject':
    #         print(i)
    #         begin = i.index('\'') + 1
    #         end = i.rfind('\'')
    #         subject = i[begin:end]
    #         break
    # if 'subject' not in locals():
    #     print(message.roomId)
    subject = "Message from Spark Space {}".format(getRoomName(message.roomId))

    return subject

def getContent(message_text):

    # mgs = message_text.split('-')
    # for i in mgs:
    #     if i.split()[0] == 'content':
    #         print(i)
    #         begin = i.index('\'') + 1
    #         end = i.rfind('\'')
    #         content = i[begin:end]
    #         break
    #     else:
    content = message_text

    return content

def getUsers(roomId):
    url = "https://api.ciscospark.com/v1/memberships"
    querystring = {"roomId": roomId, "max": "1000"}

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
            if user['personEmail'].split('@')[1] != "sparkbot.io":
                user_list.append(user['personEmail'])
    sys.stderr.write("User List\n----\n")
    for user in user_list:
        sys.stderr.write(user + "\n")
    return user_list

def getRecipients(message, excludelist):
    roomid = message.roomId
    users = getUsers(roomid)
    sys.stderr.write("Inside getRecipients: User List\n----\n")
    valid_users = []
    for user in users:
        sys.stderr.write(user + "\n")
    for useraddress in users:
        sys.stderr.write("\nLooking at {}'s address\n".format(useraddress))
        for domain in excludelist:
            sys.stderr.write("Looking for {0} in {1}'s address\n".format(domain, useraddress))
            if domain in useraddress:
                sys.stderr.write("Found {0} in {1}.  Removing it from list.\n".format(domain, useraddress))
                #users.remove(useraddress)
                #sys.stderr.write("Removed")
            else:
                sys.stderr.write("Did not find {0} in {1}. Adding it to valid list\n".format(domain, useraddress))
                valid_users.append(useraddress)
    return valid_users

def getExcludelist(message_text):
    excludelist = []
    sys.stderr.write("Running in getExcludelist")
    sys.stderr.write(message_text)
    if "/exclude" in message_text:
        raw_list = message_text.split("/exclude")[1].split(")")[0].split("(")[1].split("@")
        for item in raw_list:
            sys.stderr.write("\n" + item + "\n")
            if "." in item:
                sys.stderr.write("\nFound {} in exclude command\n".format(item))
                excludelist.append(item)
    
    return excludelist


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

    print("Mailgun response " + response.text)
    return response.status_code

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
def getSender(personId):
    url = "https://api.ciscospark.com/v1/people/{}".format(personId)

    headers = {
        'authorization': auth,
        'content-type': 'application/json'
    }
    response = requests.request("GET", url, headers=headers)
    user = json.loads(response.content)

    return user['displayName']

def buildEmail(message, message_text, senderId, roomId, excludelist=[]):
    sender = getSender(senderId)
    subject = getSubject(message_text, message)
    roomurl = getRoomURL(roomId)
    footer = "\n\nContinue the conversation on spark {}".format(roomurl)
    content = "Message from {}:\n\n".format(sender) + getContent(message_text) + footer
    #I'm thinking of adding exclude list here
    recipients = getRecipients(message, excludelist)


    if content != None:
        print("Content Found - Sending email")
        sendmail_status = sendEmail(subject, content, recipients)
        if sendmail_status >= 200 < 300:
            response = 'Email sent:\n' \
                       'to:{2}\n' \
                       'subject "{0}"\n' \
                       'content "{1}"'.format(subject, content, recipients)
        else:
            response = "Failed to send email.  Please contact the following for support:\n" \
                       "{0}\n" \
                       "or {1}\n".format(support_email, support_link)
    else:
        print("Error - User - empty content")
        response = 'You must specify content\n\n' + help()
    return response

def received():
    response = "Received message. Standby."
    return response

def removeCMD(msg, option):
    
    return msg.split(")",1)[1].strip()

@app.route("/api/injest", methods=['POST'])
def injest():
    data = request.get_json()
    message_id = data['data']['id']

    message = Message.get(session, message_id)
    sender = message.attributes['personId']
    print(message.attributes)
    print(sender)
    if sender != myid:
        room = Room(attributes={'id':message.roomId})
        
        #room.send_message(session, "Received message. Standby.")

        #Check to see if there are more than 50 members in a room.  If so do not send the message
        member_count = len(getUsers(message.roomId))

        if member_count <= 500:

            message_text = message.attributes['text']

            msg = message_text.split(name)
            sys.stderr.write("\nremoving {} from message\n".format(name))
            msg = msg[1].strip()
            sys.stderr.write("\nMessage is - {}\n".format(msg))

            if len(msg) < 1:
                sys.stderr.write("\nMessage is empty\n")
                spark_msg = "Please tag me and type a message to be sent via email"
            else:
                if msg.split()[0] == '-version':
                    response = version
                    spark_msg = version
                elif msg.split()[0] == '-email':
                    room.send_message(session, received())
                    response = buildEmail(message, msg, sender)
                    spark_msg = response + "\nYou no longer need to tag messages with -email, just speak to me"
                elif msg.split()[0] == 'help':
                    response = help()
                    spark_msg = response
                elif '/exclude' in msg.split()[0]:
                    excludelist = getExcludelist(msg)
                    msg = removeCMD(msg, '/exclude')
                    room.send_message(session, received())
                    response = buildEmail(message, msg, sender, message.roomId, excludelist=excludelist)
                    spark_msg = "Email Sent"                    
                else:
                    room.send_message(session, received())
                    response = buildEmail(message, msg, sender, message.roomId)
                    spark_msg = "Email Sent"

            room.send_message(session, spark_msg)

        else:
            room_too_large_message = "I cannot create an email for you.  To help prevent SPAM I am limited to " \
                                     "only sending Emails with rooms that have no more than 500 users.  If you" \
                                     "would like to see this increased please file an issue at {} or reach out" \
                                     "to {}".format(support_link, support_email)
            room.send_message(session, room_too_large_message)
            response = "Room too large"

    else:
        response = "Ignore message, sent from myself"

    return(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
