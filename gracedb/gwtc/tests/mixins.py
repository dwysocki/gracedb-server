from gwtc.models import gwtc_catalog, gwtc_gevent, gwtc_superevent
from superevents.tests.mixins import SupereventCreateMixin

# A class to create test gwtc superevents, events, and catalogs:

class gwtc_create_mixin(SupereventCreateMixin):
    """
    mixin to create test gwtc entries
    """
    @classmethod
    def create_gwtc_catalog(cls, user, gwtc_number='test1'):

        # create one superevent:
        new_superevent = cls.create_superevent(user)

        # Now create a catalog object:
        test_gwtc = gwtc_catalog.objects.create(number = gwtc_number,
                        submitter = user)

        # create the associated gwtc event and superevent:
        test_gwtc_superevent = gwtc_superevent.objects.create(
                                   superevent = new_superevent,
                                   gwtc_catalog = test_gwtc)

        test_gwtc_event = gwtc_gevent.objects.create(
                              gwtc_catalog = test_gwtc,
                              gwtc_superevent = test_gwtc_superevent,
                              gevent = new_superevent.preferred_event,
                              pipeline = new_superevent.preferred_event.pipeline)

        return test_gwtc

#    @classmethod
#    def setUpTestData(cls):
#        super(gwtc_create_mixin, cls).setUpTestData()

        # Create a catalog:
        

