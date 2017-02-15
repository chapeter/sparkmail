# sparkmail
Sparkmail is a bot for Cisco Spark that sends an email to all members of a Spark Space when it is mentioned

## Use
sparkmail (bot) is currently running and active.  Invite sparkmail to a room and begin using it

## Requirements
sparkmail was written to work with Mailgun.  Create an account there if you don't want to alter any code.  I did some stubbing for GMAIL functionality as well.

* Register a new bot
* Create a webhook for with "messages" "create" for your bot pointing to /api/injest of your bot hosting server
* Set environment variables:
    * SPARK_BOT_TOKEN
    * MG_KEY
    * MG_DOMAIN
    * MG_EMAIL
* Install needed packages: ```pip install -r requirements.txt```
* ```python main.py```

