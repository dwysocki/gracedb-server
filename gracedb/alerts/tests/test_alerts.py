import itertools
try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import types

import pytest

from alerts.main import issue_alerts
from events.models import Event
from superevents.models import Superevent


###############################################################################
# FIXTURES ####################################################################
###############################################################################
# Mock recipient getter dict
@pytest.fixture
def mock_rg_dict():
    def _inner(alert_type='new', recips_exist=True):
        # Set up mock recipient getter stuff
        mock_recipients = mock.MagicMock()
        mock_recipients.exists.return_value = recips_exist
        mock_rg = mock.MagicMock()
        mock_rg.get_recipients.return_value = \
            (mock_recipients, mock_recipients)
        mock_rg_class = mock.MagicMock()
        mock_rg_class.return_value = mock_rg
        mock_rg_dict = {alert_type: mock_rg_class}
        return mock_rg_dict
    return _inner


###############################################################################
# TESTS #######################################################################
###############################################################################
@pytest.mark.parametrize(
    "xmpp,email,phone",
    list(itertools.product((True, False), repeat=3))
)
def test_alert_settings(settings, mock_rg_dict, xmpp, email, phone):
    # Set up settings
    settings.SEND_XMPP_ALERTS = xmpp
    settings.SEND_EMAIL_ALERTS = email
    settings.SEND_PHONE_ALERTS = phone

    # Set up mock superevent object
    superevent = mock.MagicMock()
    superevent.is_test.return_value = False
    superevent.is_mdc.return_value = False
    preferred_event = mock.MagicMock()
    type(preferred_event).offline = mock.PropertyMock(return_value=False)
    superevent.preferred_event = preferred_event

    # Call issue_alerts
    with mock.patch('alerts.main.issue_xmpp_alerts') as mock_xmpp, \
         mock.patch('alerts.main.issue_email_alerts') as mock_email, \
         mock.patch('alerts.main.issue_phone_alerts') as mock_phone, \
         mock.patch('alerts.main.is_event') as mock_is_event, \
         mock.patch.dict('alerts.main.ALERT_TYPE_RECIPIENT_GETTERS',
                         mock_rg_dict(), clear=True):

        mock_is_event.return_value = False
        issue_alerts(superevent, 'new', None)

    # Check results
    if xmpp:
        assert mock_xmpp.call_count == 1
    if phone:
        assert mock_phone.call_count == 1
    if email:
        assert mock_email.call_count == 1
    if not (phone or email):
        assert mock_is_event.call_count == 0 


@pytest.mark.parametrize(
    "is_event,is_mdc,is_test,is_offline",
    list(itertools.product((True, False), repeat=4))
)
def test_no_alerts_for_test_mdc_offline_events_and_superevents(
    settings, mock_rg_dict, is_event, is_mdc, is_test, is_offline
):
    # Set up settings
    settings.SEND_XMPP_ALERTS = False
    settings.SEND_EMAIL_ALERTS = True
    settings.SEND_PHONE_ALERTS = True

    # Set up mock event/superevent object
    # First, set up event
    event = mock.MagicMock()
    type(event).offline = mock.PropertyMock(return_value=is_offline)
    # If we're doing a superevent, then set the event as its preferred_event
    if not is_event:
        es = mock.MagicMock()
        es.preferred_event = event
    else:
        es = event
    # is_mdc and is_test are handled the same way for both events and
    # superevents, so we can set it up at this point
    es.is_mdc.return_value = is_mdc
    es.is_test.return_value = is_test

    # Instantiate mock_rg_dict
    mock_rg_dict = mock_rg_dict()

    # Call issue_alerts
    with mock.patch('alerts.main.issue_xmpp_alerts') as mock_xmpp, \
         mock.patch('alerts.main.issue_email_alerts') as mock_email, \
         mock.patch('alerts.main.issue_phone_alerts') as mock_phone, \
         mock.patch('alerts.main.is_event') as mock_is_event, \
         mock.patch.dict('alerts.main.ALERT_TYPE_RECIPIENT_GETTERS',
                         mock_rg_dict, clear=True):

        mock_is_event.return_value = is_event
        issue_alerts(es, 'new', None)

    # Check results
    assert es.is_mdc.call_count == 1
    assert es.is_test.call_count == int(not es.is_mdc())
    # Whether the recipient_getter class is called or not depends
    # finally on whether the event is offline or not
    if (not (es.is_mdc() or es.is_test())):
        assert mock_rg_dict['new'].call_count == int(not event.offline)
    else:
        assert mock_rg_dict['new'].call_count == 0
