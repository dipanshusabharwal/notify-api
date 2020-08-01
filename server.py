from flask import Flask, request
import datetime
from twilio.rest import Client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from flask_mysqldb import MySQL

app = Flask(__name__)

mysql = MySQL(app)

app.config["MYSQL_USER"] = ""
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = ""
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

twilio_account_sid = ''
twilio_auth_token = ''
twilio_email_auth_key = ""

twilio_sms_number = ""
twilio_whatsapp_number = ""
twilio_sender_email = ""


def data_integrity_check(data):
    missing_data = ""
    ts = data["timestamp"]
    e_id = data["enterprise_id"]

    for key, value in data.items():
        if value == "":
            missing_data += " " + key

    if len(missing_data) == 0:
        if timestamp_check(ts) == 0:
            return "Timestamp is invalid"
        else:
            if check_enterprise_id_exists(e_id):
                return ""
            else:
                return "Enterprise ID not found."

    return "Please enter " + missing_data


def timestamp_check(timestamp):
    timestamp = timestamp.split()
    date = map(int, timestamp[0].split("-"))
    time = map(int, timestamp[1].split(":"))
    year = date[0]
    month = date[1]
    day = date[2]
    hours = time[0]
    minutes = time[1]
    seconds = time[2]
    print("Timestamp destructured", year, month, day, hours, minutes, seconds)

    try:
        d = datetime.datetime(year, month, day, hours, minutes, seconds)
        print("Date is valid.")
        return 1
    except ValueError:
        print("Date is invalid.")
        return 0


def check_enterprise_id_exists(enterprise_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT * FROM customers WHERE enterprise_id = %s""", (enterprise_id,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    if results is None:
        return 0
    else:
        return 1


def check_for_subscription(enterprise_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT is_subscribed FROM customers WHERE enterprise_id = %s""", (enterprise_id,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    return results["is_subscribed"]


def check_for_channels_gateways(enterprise_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT channel_id, gateway_id FROM subscriptions WHERE enterprise_id = %s""", (enterprise_id,))

    results = cursor.fetchall()

    mysql.connection.commit()
    cursor.close()

    items = []
    for item in results:
        items.append(item)

    return items


def fetch_customer_details(enterprise_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT phone, email FROM customers WHERE enterprise_id = %s""", (enterprise_id,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    return results


def send_notifications(lst, json_data, customer_details):
    notification_arr = []

    for results in lst:
        print(results)
        channel_id = results["channel_id"]
        gateway_id = results["gateway_id"]

        cursor = mysql.connection.cursor()
        cursor.execute(
            """SELECT gateway_name, channel_name FROM gateways INNER JOIN channels ON channels.channel_id = gateways.channel_id WHERE channels.channel_id = %s AND gateways.gateway_id = %s""",
            (
                channel_id, gateway_id,))

        res = cursor.fetchall()

        mysql.connection.commit()
        cursor.close()

        for item in res:
            print(item["channel_name"], item["gateway_name"])

            notif_status = portal(item["channel_name"], item["gateway_name"], channel_id, gateway_id, json_data,
                                  customer_details)

            if notif_status is not None:
                notification_arr.append(notif_status)

    return (notification_arr)


def portal(channel_name, gateway_name, channel_id, gateway_id, json_data, customer_details):
    # add notification channels here
    if channel_name == "SMS":
        if gateway_name == "Twilio":
            return (twilio_sms(json_data, channel_id, gateway_id, customer_details))
    elif channel_name == "Whatsapp":
        if gateway_name == "Twilio Whatsapp":
            return (twilio_whatsapp(json_data, channel_id, gateway_id, customer_details))
    elif channel_name == "Email":
        if gateway_name == "SendGrid":
            return (sendgrid_email(json_data, channel_id, gateway_id, customer_details))


def twilio_sms(json_data, channel_id, gateway_id, customer_details):
    print("Twilio SMS invoked")

    try:
        client = Client(twilio_account_sid, twilio_auth_token)

        message = client.messages.create(
            body="Shipment ID " + json_data["shipment_id"] + " is " + json_data["status"] + ". Updated on " + json_data[
                "timestamp"],
            from_=twilio_sms_number,
            to=customer_details["phone"]
        )

        print(message.sid)
        return (log_notification(json_data, channel_id, gateway_id))

    except Exception as e:
        print("Exception occurred in sending SMS", e)
        log_notification_failure(json_data, channel_id, gateway_id, "Error in sending SMS from Twilio")
        return {"status": 400, "channel": "SMS", "gateway": "Twilio",
                "message": "Notification not sent. Error Occurred."}


def twilio_whatsapp(json_data, channel_id, gateway_id, customer_details):
    print("Twilio Whatsapp invoked")

    client = Client(twilio_account_sid, twilio_auth_token)

    try:
        message = client.messages.create(
            body="Shipment ID " + json_data["shipment_id"] + " is " + json_data["status"] + ". Updated on " + json_data[
                "timestamp"],
            from_='whatsapp:' + twilio_whatsapp_number,
            to='whatsapp:' + customer_details["phone"]
        )

        print(message.sid)
        return (log_notification(json_data, channel_id, gateway_id))

    except Exception as e:
        print("Exception occurred in sending whatsapp", e)
        log_notification_failure(json_data, channel_id, gateway_id, "Error in sending Whatsapp from Twilio Whatsapp")
        return {"status": 400, "channel": "Whatsapp", "gateway": "Twilio Whatsapp",
                "message": "Notification not sent. Error Occurred."}


def sendgrid_email(json_data, channel_id, gateway_id, customer_details):
    print("Send Grid for Email invoked")
    email_message = "Shipment ID " + json_data["shipment_id"] + " is " + json_data["status"] + ". Updated on " + \
                    json_data[
                        "timestamp"]
    print(email_message)

    message = Mail(
        from_email=twilio_sender_email,
        to_emails=str(customer_details["email"]),
        subject='Order Status Update',
        html_content=str(email_message))
    try:
        sg = SendGridAPIClient(twilio_email_auth_key)
        response = sg.send(message)
        return (log_notification(json_data, channel_id, gateway_id))

    except Exception as e:
        print("Exception occurred in sending email from Sendgrid", e)
        log_notification_failure(json_data, channel_id, gateway_id, "Error in sending Email from SendGrid")
        return {"status": 400, "channel": "Email", "gateway": "Sendgrid",
                "message": "Notification not sent. Error Occurred."}


def log_notification(json_data, channel, gateway):
    print("Logging successful notification details")

    now_time = datetime.datetime.now()
    now_time = now_time.strftime("%Y-%m-%d %H:%M:%S")

    cursor = mysql.connection.cursor()
    cursor.execute(
        """INSERT INTO logs (shipment_id, status, enterprise_id, timestamp, channel, gateway, notify_time) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (json_data["shipment_id"], json_data["status"], json_data["enterprise_id"], json_data["timestamp"], channel,
         gateway, now_time))

    mysql.connection.commit()
    cursor.close()

    return {"status": 200, "message": "Notification Sent and Logged."}


def log_notification_failure(json_data, channel, gateway, message):
    print("Logging notification failure details")

    now_time = datetime.datetime.now()
    now_time = now_time.strftime("%Y-%m-%d %H:%M:%S")

    cursor = mysql.connection.cursor()

    cursor.execute(
        """INSERT INTO logs_failure (shipment_id, status, enterprise_id, timestamp, channel, gateway, notify_time, message) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (json_data["shipment_id"], json_data["status"], json_data["enterprise_id"], json_data["timestamp"], channel,
         gateway, now_time, message))

    mysql.connection.commit()
    cursor.close()


def channel_exists(channel):
    print("Checking if channel exists")

    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT channel_name FROM channels WHERE channel_name = %s""", (channel,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    if results is None:
        return 0
    else:
        return 1


def gateway_exists(gateway):
    print("Checking if gateway exists")

    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT gateway_name FROM gateways WHERE gateway_name = %s""", (gateway,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    if results is None:
        return 0
    else:
        return 1


def create_channel(channel):
    print("Creating new channel")

    cursor = mysql.connection.cursor()
    cursor.execute(
        """INSERT INTO channels (channel_name) VALUES (%s)""", (channel,))

    mysql.connection.commit()
    cursor.close()


def fetch_channel_id(channel):
    print("Fetching channel id")

    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT channel_id FROM channels WHERE channel_name = %s""", (channel,))

    results = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    return results["channel_id"]


def create_gateway(gateway, chnl_id):
    print("Creating new gateway")

    cursor = mysql.connection.cursor()
    cursor.execute(
        """INSERT INTO gateways (gateway_name, channel_id) VALUES (%s, %s)""", (gateway, chnl_id,))

    mysql.connection.commit()
    cursor.close()


@app.route('/', methods=["GET", "POST"])
def welcome():
    if request.json is None:
        return {"status": 400, "message": "Please send order status data"}

    if request.method == "GET":
        return {"status": 400, "message": "Welcome to Notify API. Please put a post request with shipment data."}
    else:
        print(request.json)
        integrity_check_message = data_integrity_check(request.json)
        if integrity_check_message != "":
            return integrity_check_message
        else:
            enterprise_id = request.json["enterprise_id"]
            if check_for_subscription(enterprise_id):
                customer_details = fetch_customer_details(enterprise_id)
                list_of_channels_gateways = check_for_channels_gateways(enterprise_id)
                if len(list_of_channels_gateways) == 0:
                    log_notification_failure(request.json, 0, 0,
                                             "Customer is subscribed for notifications but missing channels and gateways.")
                    return {"status": 401,
                            "message": "Customer is subscribed for notifications but missing channels and gateways."}
                print(list_of_channels_gateways)
                return {"message": send_notifications(list_of_channels_gateways, request.json, customer_details)}
            else:
                log_notification_failure(request.json, 0, 0, "Customer not subscribed to notifications")
                return {"status": 401,
                        "message": "Customer not subscribed to notifications. Logged in notification failures."}


@app.route("/add-channel", methods=["POST"])
def add_channel():
    if request.json is None:
        return {"status": 400, "message": "Please send channel and gateway data."}

    chnl_name = request.json["channel_name"]
    gtwy_name = request.json["gateway_name"]

    if chnl_name == "" or gtwy_name == "":
        return {"status": 400, "message": "Channel or Gateway name is missing."}

    if channel_exists(chnl_name) and gateway_exists(gtwy_name):
        return {"status": 401, "message": "Channel and Gateway already exists."}

    if channel_exists(chnl_name) == 0:
        create_channel(chnl_name)

    chnl_id = fetch_channel_id(chnl_name)
    create_gateway(gtwy_name, chnl_id)

    return {"status": 200, "message": "Channel and Gateway created."}


@app.route("/fetch-channels-gateways", methods=["GET"])
def send_channels_gateways():
    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT channel_name, gateway_name FROM gateways INNER JOIN channels ON channels.channel_id = gateways.channel_id WHERE channels.channel_id = gateways.channel_id""")

    res = cursor.fetchall()

    mysql.connection.commit()
    cursor.close()
    return ({"status": 200, "message": res})


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return {"status": 400,
            "message": "Welcome to Notify API. Please put a post request with shipment data at the index route."}
