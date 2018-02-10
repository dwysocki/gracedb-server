.. _phone_alerts:

========================
Phone alerts with Twilio
========================

*Last updated 1 December 2016*

Introduction
============
Phone and SMS alerts are currently implemented in GraceDB via `Twilio <https://www.twilio.com/>`__, a programmable communications provider used by both big and small organizations.
For our purposes, Twilio is used to make phone calls with synthesized voice messages, and to send SMS messages to phones (although many people can already get SMS messages using the existing GraceDB email alert feature, by using the email address that their service provider bridges to SMS).
Leo Singer is the local expert on Twilio, having used it with iPTF.

Similarly to e-mail alerts, the user can specify a variety of scenarios in which they would like to receive an alert: when a particular pipeline creates a new event, when a new label is applied, when an event with a given FAR is identified, and so on.
The GraceDB server sends the information to the Twilio server, which then contacts the recipient of the alert through a phone call and/or an SMS message.

Setting up Twilio for the LVC
=============================
*Notes here are from Peter Shawhan and Leo Singer on setting up a Twilio account.*

Peter Shawhan has some flexible funds which should be sufficient to pay for the LVC's usage of Twilio for at least the next couple of years, and possibly longer.
So, Peter created a new Twilio account, giving "LIGO Scientific Collaboration" for the company/organization name and ``peter.shawhan@ligo.org`` as the login email address.
When signing up at https://www.twilio.com, Peter indicated that our first product interest is "Voice" and our application is "Voice alerts" using Python, but that was probably just collecting information for marketing.

The Twilio console is reasonably intuitive.
With guidance from Leo, Peter did some of the "Getting started" steps as well as other configuration tasks:

- Ordered a Twilio phone number. All automated calls and SMS messages will originate from this number.  We got to select the phone number, and LVC members will appreciate the number's similarity to the name of our first detected event. :)
- Upgraded the account (clicked the "Upgrade" link which was near the upper right corner of the window) to make it a paid account rather than a trial account.
- Set up a payment method (Peter's credit card, $20 initial deposit, with auto-recharge).
- Added other users to the account (Home --> Account --> Manage Users): for now, Tanner Prestegard and Leo Singer, both with "Developer" permissions.
- Requested permission to make voice calls to several foreign countries where LVC members are located (Home --> Account --> Account Settings --> Geographic Permissions). These calls cost somewhat more, and our request has to be reviewed by a Twilio representative. We entered the LIGO Lab's Caltech address, website URL, and contact phone number (626-395-2129 - we're guessing that is answered by Julie Hiroto?) for this. SMS messages to all countries seem to be enabled by default.
- Set up two TwiML action templates ((...) --> Developer Center --> TwiML Bins) called "GraceDB create" and "GraceDB label" to queue the actual calls and SMS messages through http POST requests. The URLs generated for these actions have long hash codes and can be looked up in that part of the Twilio console.
- We have not attempted to change the default call execution rate, which is 1 call per second.  It is possible to submit a request to increase that rate (Programmable Voice --> Settings --> General --> Calls Per Second) but we won't do that, at least for now.

Twilio configuration for GraceDB
================================
As a GraceDB developer/maintainer, your first step is to get added as a developer to the LSC Twilio account (talk to Peter Shawhan or Leo Singer) - if you don't already have a Twilio account, you'll have to create one.
There are a few main things you'll need from the `Twilio Console <https://www.twilio.com/console>`__:

1. Account SID: visible at the top of the page, under "Account Summary".
2. Auth Token: below Account SID; you'll have to click on the eye icon to reveal it.

You'll also need the TwiML bin URLs, which you can get `here <https://www.twilio.com/console/dev-tools/twiml-bins>`__.
Currently, we have two TwiML bins:

- GraceDB create: used when an event is created.
- GraceDB label: used when an event is assigned a label.

If you click on one of the TwiML bins, you'll see an SID, a URL, and the configuration.
The SID will be needed for GraceDB to POST to this TwiML bin.
Also, the URL is defined by a base URL plus the SID: ``https://handler.twilio.com/twiml/SID``.

The "GraceDB create" TwiML bin configuration is shown here::

  <?xml version="1.0" encoding="UTF-8"?>
  <Response>
    <Say>
      A {{pipeline}} event with Grace DB ID {{graceid}} was created.
    </Say>
    <Sms>A {{pipeline}} event with GraceDB ID {{graceid}} was created.
      https://{{server}}.ligo.org/events/view/{{graceid}}
    </Sms>
  </Response>

The call and message components are easily apparent.
Currently, it's configured to do both by default, but this may change in the future.

The attributes are appended to the TwiML bin URL for the POST request.
Example: ``https://handler.twilio.com/twiml/SID?pipeline=gstlal&graceid=G123456&server=gracedb``. 

You'll need the Account SID, Auth Token, and TwiML bin SIDs for the next step.

Configuration on GraceDB server
===============================
Most of the relevant code is in ``events/alerts.py``, including the following functions:

- ``get_twilio_from``
- ``make_twilio_calls``
- ``issueAlertForLabel``
- ``issueEmailAlert``

There is also some relevant code in ``userprofile/models.py``, which defines a ``PhoneNumberField`` for the ``Contact`` model and validates the phone number when a user signs up for this service.

The TwiML bin SIDs are used in ``make_twilio_calls`` to generate the URLs and make the POST request.
These SIDs, along with the Account SID and Auth Token should **NOT** be saved in the git repository.
As a result, they are saved in ``settings/secret.py``, which is not part of the git repository, but is created by Puppet and encrypted in the GraceDB eyaml `file <https://git.ligo.org/cgca-computing-team/cgca-config/blob/production/production/hieradata/gracedb.cgca.uwm.edu.eyaml>`__ in the `cgca-config repository <https://git.ligo.org/cgca-computing-team/cgca-config>`__.
If you need to edit this, you'll have to follow the instructions `here <https://git.ligo.org/cgca-computing-team/cgca-config/blob/production/EncryptedYaml.md>`__ for working with eyaml files.

*Note: currently, the code for determining the phone call recipients is coupled with the code that determines e-mail recipients.
This may be the most efficient way of doing it, but we may want to consider separating it in the future for ease of understanding and modularity.*

Finally, phone calls are only made to LVC members at present.
