# Utilities for issuing alerts

class AlertIssuer(object):
    """Base class for issuing XMPP alerts"""
    serializer_class = None
    alert_types = None

    def __init__(self, obj, alert_type, *args, **kwargs):
        # Check alert type
        if alert_type not in self.alert_types:
            raise ValueError('alert_type should be in {0}'.format(
                self.alert_types))

        # Assign attributes
        self.obj = obj
        self.alert_type = alert_type

    def serialize_obj(self):
        return self.serializer_class(self.obj).data

    def issue_alerts(self):
        # Should be overridden in derived classes
        return NotImplemented


class AlertIssuerWithParentObject(AlertIssuer):
    """
    Base class for issuing XMPP alerts. Handles the case where
    we want to include both a serialized object (like a log, label, etc.),
    as well as a "parent" object to which the first object is attched, like
    an event or superevent.
    """
    parent_serializer_class = None

    def serialize_parent(self):
        return self.serializer_class(self.get_parent_obj())

    def get_parent_obj(self):
        if not hasattr(self, 'parent_obj'):
            self.parent_obj = self._get_parent_obj()
        return self.parent_obj

    def _get_parent_obj(self):
        return NotImplemented
