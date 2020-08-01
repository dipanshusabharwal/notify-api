<b><u><h1>notify-api</h1></b></u>

A small API for handling order status updates and sending notifications through selected channels.

<b><u><h2>Features implemented:</h2></b></u>

1. Push notifications through subscribed channels.

2. Logging updates for both success and failure.

3. Maintaining channel and gateway info for each enterprise.

4. Add new channels and gateways.

5. List all channels and gateways.

6. Basic data hygience checks - input data missing, input data validation.

<b><u><h2>Stack:</h2></b></u>

1. Python.

2. Flask.

3. MySQL.

<b><u><h2>Notification Services Used:</h2></b></u>

1. [Twilio for SMS](https://www.twilio.com/messaging)

2. [SendGrid for Email](https://www.twilio.com/sendgrid/email-api)

3. [Twilio for Whatsapp](https://www.twilio.com/whatsapp)

<b><u><h2>Routes:</h2></b></u>

1. <b>/</b> - default route with POST method and json input for updating order status.

![/ route](./routes/send_notification.png "/ route")

2. <b>/</b> - default route with GET method for handling error route.

![/ route](./routes/error.png "/ route")

3. <b>/add-channel-gateway</b> with POST method and json input for creating new channel and gateway.

![/add-channel-gateway route](./routes/add_channel_gateway.png "/add-channel-gateway route")

4. <b>/fetch-channels-gateways</b> with GET method for fetching all channels and gateways.

![/fetch-channels-gateways route](./routes/fetch_channels_gateways.png "/fetch-channels-gateways route")

<b><u><h2>Tables:</h2></b></u>

1. <b>customers</b> : information about enterprise - id, is subscribed for notifications, phone and email.

![customers table](./schema/customers.png "customers table")

2. <b>channels</b> : information about channels - id, name.

![channels table](./schema/channels.png "channels table")

3. <b>gateways</b> : information about gateways - id, name and channel it is associated with.

![gateways table](./schema/gateways.png "gateways table")

4. <b>subscriptions</b> : information about channels and gateways an enterprise is subscribed to. There can be none and there can be many. Contains - enterprise id, channel id and gateway id.

![subscriptions table](./schema/subscriptions.png "subscriptions table")

5. <b>logs</b> : information about successful notification through selected channels to enterprises. Contains - all order status, enterprise id, channel id, gateway id and logging time.

![logs table](./schema/logs.png "logs table")

6. <b>Logs_failure</b> : information about all notifications that were not sent due to service API failures, customer not subscribed to any notification service, customer subscription data missing. Contains - all order status, enterprise id, channel id, gateway id, logging time and reason for failure.

![logs_failure table](./schema/logs_failure.png "logs_failure table")

<b><u><h2>For a successful run, you need:</h2></b></u>

1. All Twilio configurations for successful notifications (Auth Key and relevant phone numbers).
2. Enterprise, channel, gateway and enterprise subscription table entries already created.

<b><u><h2>Notification received:</h2></b></u>

1. SMS
   ![sms notification](./notifications/sms.jpeg "sms notification")
2. Email
   ![email notification](./notifications/email.jpeg "email notification")
3. Whatsapp
   ![whatsapp notification](./notifications/whatsapp.jpeg "whatsapp notification")
