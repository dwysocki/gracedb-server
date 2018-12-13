from api.v1.superevents.serializers import SupereventSerializer, \
    SupereventLogSerializer, SupereventLabelSerializer, \
    SupereventVOEventSerializer, SupereventEMObservationSerializer, \
    SupereventSignoffSerializer, SupereventGroupObjectPermissionSerializer
from ..main import issue_alerts
from ..utils import AlertIssuerWithParentObject


class AlertIssuerWithParentSuperevent(AlertIssuerWithParentObject):
    parent_serializer_class = SupereventSerializer

    def serialize_parent(self):
        return self.parent_serializer_class(self.get_parent_obj()).data

    def _get_parent_obj(self):
        # Assumes that the obj has a direct relation to a superevent
        if not hasattr(self.obj, 'superevent'):
            raise AttributeError(('object of class {0} does not have a direct '
                'relationship to a superevent').format(
                self.obj.__class__.__name__))
        return self.obj.superevent

    def issue_alerts(self):
        issue_alerts(self.get_parent_obj(), self.alert_type,
            self.serialize_obj(), self.serialize_parent())


class SupereventAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventSerializer
    alert_types = ['new', 'update', 'event_added', 'event_removed',
        'confirmed_as_gw']

    def _get_parent_obj(self):
        return self.obj


class SupereventLogAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventLogSerializer
    alert_types = ['log']


class SupereventLabelAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventLabelSerializer
    alert_types = ['label_added', 'label_removed']

    def issue_alerts(self):
        issue_alerts(self.get_parent_obj(), self.alert_type,
            self.serialize_obj(), self.serialize_parent(),
            label=self.obj.label)


class SupereventVOEventAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventVOEventSerializer
    alert_types = ['voevent']


class SupereventEMObservationAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventEMObservationSerializer
    alert_types = ['emobservation']


class SupereventSignoffAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventSignoffSerializer
    alert_types = ['signoff_created', 'signoff_updated', 'signoff_deleted']


class SupereventPermissionsAlertIssuer(AlertIssuerWithParentSuperevent):
    serializer_class = SupereventGroupObjectPermissionSerializer
    alert_types = ['exposed', 'hidden']

    def serialize_obj(self):
        """
        self.obj should be a superevent, but we want to return the list
        of group object permissions here.
        """
        # NOTE: it seems really weird to return a list of permissions here.
        # But exposing/hiding a list of permissions does in fact change
        # multiple permissions. Should give this some more thought.
        gops = self.obj.supereventgroupobjectpermission_set.all()
        return self.serializer_class(gops, many=True).data

    def _get_parent_obj(self):
        return self.obj
