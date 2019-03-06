.. _notifications:

==============================================
Phone and email notifications (LVC users only)
==============================================

Phone and email alerts are issued under various circumstances to LVC users who have registered for them.
This page will provide some details on the alert sign-up process and the logic involved in issuing these alerts.


Alert signup
============
LVC users can find the main alerts page by clicking on the "Alerts" tab in the navigation bar.
Here, you will find two headings: contacts and notifications.


Creating a contact
------------------
Click on the "Create new contact" button on the main alerts page to begin the contact creation process.
Once you have reached the contact creation page, choose a phone or email contact by clicking on the corresponding tab.
For phone contacts, you can receive alerts via a text message, voice call, or both.
Fill in the form and submit it to finish the contact creation process.


Verifying a contact
-------------------
Once you have successfully created a contact, you will be returned to the main alerts page.
You should see your newly created contact displayed alongside some buttons.
Your contact is currently unverified, and you cannot receive alerts via this contact until it is verified.
Click on the yellow "Verify" button to the right of the contact to begin the verification process.

Once you have reached the verification page, you can click on the "Request a verification code" button to receive a verification code for your contact.
You will receive the verification code via the following mechanism:

- Email for email contacts
- Voice call for phone contacts who have specified "call"
- Text message for phone contacts who have specified "text" or "both"

Verification codes last for 60 minutes.
If your code expires or if you misplace it, you can request a new verification code.

Once you have your verification code, enter it in the form that is now displayed and hit submit.
If you have entered the code correctly, you will be returned to the main alerts page and your contact will now be marked as "Verified".


Modifying a contact
-------------------
You can edit a contact by clicking on the "Edit" button next to the contact information on the main alerts page.
You are not permitted to modify the contact information, as that would allow the verification process to be circumvented.
You may edit the description for either type of alert, or the phone contact method for phone alerts.

You may also delete a contact at any time, using the "Delete" button next to the contact information on the main alerts page.
If you create a new contact with the same information, it will need to be reverified.


Testing a contact
-----------------
Use the "Test" button next to the contact information on the main alerts page to send a test email, text message, and/or voice call to your contact.
Only verified contacts can be tested.


Creating a notification
-----------------------
A notification is a set of criteria which is linked to a contact or contacts.
It specifies under which conditions the corresponding contacts should receive an alert.

To begin, click on the "Create new notification" button on the main alerts page.
Once you have reached the notification creation page, decide whether you want to receive alerts about superevents or events (most users will likely want superevents) and click the corresponding tab.

First, you should enter a description of this notification and select a contact or contacts to receive alerts when this notification is triggered (you can select multiple contacts by holding CTRL and clicking).
The rest of the fields in either form correspond to criteria which must be met for the notification to be triggered.
More information about each field will be provided in the following section where the logic for triggering a notification is discussed.

A few notes here:

- The label query field allows a complex filter on the requirement for which labels are/are not applied to an event or superevent.  To construct a label query, combine label names with binary AND: ('&' or ',') or binary OR: '|'. They can also be negated with '~' or '-'. For N labels, there must be exactly N-1 binary operators. Parentheses are not allowed. It is suggested to specify at least one label that is not negated, or you may receive more notifications than you would like.
- You can specify either a set of labels or a label query, but not both.
- An event or superevent is considered a neutron star candidate if its source is thought to be a compact binary system where the secondary object has a mass less than 3 M\ :sub:`sun`\ . You can restrict your alerts to only events or superevents which are considered to be a neutron star candidate by checking the corresponding box in the form.


Alert logic
===========
Alerts will be issued in the following situations:

- Event or superevent creation
- Event or superevent update
- Label application to or label removal from an event or superevent

For each type of alert, there is a set of conditions that correspond to a state change which can trigger notifications.
For example: for an update alert, we don't trigger every notification whose FAR threshold is satisfied by the event's FAR, but only those where the event update changes the event's FAR from above threshold to below threshold.
All requirements on other parameters (NS candidate status, label status, etc.) must still be satisfied.

**Alerts are not sent for:**

- **Test or MDC events or superevents**
- **Offline events or for superevents whose preferred events are marked as offline**

Creation alerts
---------------
When an event or superevent is created, all notifications whose criteria on FAR, NS candidate status, and group, pipeline, and search requirements (events only) are satisfied will be triggered.
Labels are not applied to events or superevents at creation time, so any notifications which have a label requirement will not be triggered.


Update alerts
-------------
When an event or superevent is updated, all notifications will be triggered whose criteria on FAR, NS candidate status, group, pipeline, and search requirements (events only), and label status are met, **AND**:

- The update changes the event or superevent's FAR from above the notification's FAR threshold to below it, **OR**
- The update changes the event or superevent's NS candidate status from False to True, and the notification requires an NS candidate.


Label added alerts
------------------
When a label is applied to event or superevent, all notifications will be triggered whose criteria on FAR, NS candidate status, group, pipeline, and search requirements (events only), and label status, **AND**:

- The label that was just added matches one of the labels required by the notification (i.e., the addition of this label is the final requirement to satisfy the notification's label or label query requirements).


Label removed alerts
--------------------
Same as "label added" alerts, except that the label that was just removed must be the final requirement to satisfy the notification's label query requirements.
