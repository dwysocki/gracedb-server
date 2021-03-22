from collections import OrderedDict
import logging
import re

from django.db import models, connection, IntegrityError
from django.db.models import Q, Max
from django.utils import six
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from core.vfile import VersionedFile

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


class CleanSaveModel(models.Model):
    """Abstract model which automatically runs full_clean() before saving"""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super(CleanSaveModel, self).save(*args, **kwargs)


class AutoIncrementModel(models.Model):
    """
    An abstract class used as a base for classes which need the
    autoincrementing save method described below.

    AUTO_FIELD: name of field which acts as an autoincrement field.
    AUTO_CONSTRAINTS: tuple of field names to use as a constraint; i.e., the
                      AUTO_FIELD increments relative to the number of rows in
                      the table which have the same values for these fields.
    """
    AUTO_FIELD = None
    AUTO_CONSTRAINTS = None
    max_retries = 5

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):

        # Do a normal save if this is not an insert (i.e., the instance has a
        # primary key already), or if the required fields are not set
        pk_set = self._get_pk_val() is not None
        if (pk_set or (self.AUTO_FIELD is None or
                       self.AUTO_CONSTRAINTS is None)):
            super(AutoIncrementModel, self).save(*args, **kwargs)
        else:
            self.auto_increment_insert(*args, **kwargs)

    def auto_increment_insert(self, *args, **kwargs):
        """

        This has been tested with the following classes:
            EventLog, EMObservation, EMFootprint, EMBBEventLog, VOEvent


        Requires AUTO_FIELD and AUTO_CONSTRAINTS to be defined.
        """


        # Check for the existence of the required fields:
        if not self.AUTO_CONSTRAINTS or not self.AUTO_FIELD:
            raise TypeError('AUTO_CONSTRAINTS or AUTO_FIELD not set.')

        # Check type of self.AUTO_CONSTRAINTS
        if not isinstance(self.AUTO_CONSTRAINTS, (tuple, list)):
            raise TypeError(_('AUTO_CONSTRAINTS should be a tuple or list'))

        # Get some useful information
        meta = self.__class__._meta
        current_class = self.__class__

        # Get model fields, except for primary key field.
        fields = [f for f in meta.local_concrete_fields if not
            isinstance(f, models.fields.AutoField)]

        # Check constraint fields
        f_names = [f.name for f in fields]
        for constraint_field in self.AUTO_CONSTRAINTS:
            if constraint_field not in f_names:
                raise ValueError(_(('Constraint {0} is not a field for '
                    'model {1}').format(constraint_field,
                    current_class.__name__)))

        # Check auto field
        if self.AUTO_FIELD not in f_names:
            raise ValueError(_(('AUTO_FIELD {0} is not a field for '
                'model {1}').format(self.auto_field, self.__class__.__name__)))


        # Set up Q query for multiple constraints. For instance, superevents'
        # base_date_number is constrained by both category and the date. So
        # for example, there can exist S123456a, TS123456a, and MS123456a. The
        # t_0_date is the same, but the category is different. So they each get
        # an "a". 

        const_query = Q()
        for const in self.AUTO_CONSTRAINTS:
            const_query = const_query & Q(**{const: getattr(self, const)})

        # get the queryset that meets the constraints: 

        qs = current_class.objects.filter(const_query)

        # Set AUTO_FIELD to one-plus-the-maximum of the value of AUTO_FIELD
        # in the constained set. Note that since some superevents get removed
        # or other circumstances, the max does not always equal to the number 
        # entries in the set. This caused some db integrity errors in testing.

        if qs:
            setattr(self, self.AUTO_FIELD,
                    qs.aggregate(max_val=Max(self.AUTO_FIELD))['max_val'] + 1)
        else:
            setattr(self, self.AUTO_FIELD, 1)

        # Save object and check constraints. Add ability to retry on the event
        # of DB Integrity errors. 

        this_try = 0
        while this_try < self.max_retries:
            try:
                self.full_clean()
                super(AutoIncrementModel, self).save(*args, **kwargs)
            except IntegrityError as e:
                logger.warning("Database integrity error when saving {}. ",
                "Incrementing and retrying.".format(self))
                setattr(self, self.AUTO_FIELD, 
                        getattr(self,self.AUTO_FIELD) + 1)
                this_try += 1
            else:
                break

    def auto_increment_update(self, update_field_name, constraints=[],
        allow_update_to_nonnull=False):
        """
        UPDATE superevents_superevent SET gw_date_number = (SELECT N FROM (SELECT IFNULL(MAX(gw_date_number),0)+1 as N FROM superevents_superevent WHERE t_0_date='1980-01-06' AND is_gw=1) AS y) WHERE id=41;
        """

        if (not allow_update_to_nonnull and getattr(self, update_field_name)
            is not None):
            raise ValueError(_(('Attempt to update a non-null constrained auto'
                'field for object {0}. Not allowed.').format(self.__str__())))

        # Get current class:
        current_class = self.__class__

        # Set up query based on the constraints:
        query = Q()
        for i in constraints:
            query = query & Q(**{i: getattr(self, i)})

        # get the queryset that meets the constraints:

        qs = current_class.objects.filter(query)

        # Set AUTO_FIELD to one-plus-the-maximum of the value of AUTO_FIELD
        # in the constained set. Note that since some superevents get removed
        # or other circumstances, the max does not always equal to the number
        # entries in the set. This caused some db integrity errors in testing.

        if qs:
            setattr(self, update_field_name,
                    qs.aggregate(max_val=Max(update_field_name))['max_val'] + 1)
        else:
            setattr(self, update_field_name, 1)


class LogBase(models.Model):
    """
    Abstract base class for log message-type objects. Concrete derived
    classes will probably want to add a ForeignKey to another model.

    Used in events.EventLog, superevents.Log
    """
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(UserModel, null=False, on_delete=models.CASCADE)
    filename = models.CharField(max_length=100, default="", blank=True)
    file_version = models.IntegerField(null=True, default=None, blank=True)
    comment = models.TextField(null=False)
    N = models.IntegerField(null=False, editable=False)

    class Meta:
        abstract = True
        ordering = ['-created', '-N']

    @property
    def versioned_filename(self):
        if self.filename:
            actual_filename = self.filename
            if self.file_version is not None:
                actual_filename += ",{n}".format(n=self.file_version)
        else:
            actual_filename = None
        return actual_filename

    def fileurl(self):
        # Override this on derived classes
        return NotImplemented

    def hasImage(self):
        # XXX hacky
        IMAGE_EXT = ['png', 'gif', 'jpg']
        return (self.filename and self.filename[-3:].lower() in IMAGE_EXT)

    @staticmethod
    def split_versioned_filename(versioned_name):
        filename, version = VersionedFile.split_versioned_name(versioned_name)
        return filename, version


class m2mThroughBase(models.Model):
    """
    Abstract base class which is useful for providing "through" access for a
    many-to-many relationship and recording the relationship creator and
    creation time.
    """
    creator = models.ForeignKey(UserModel, null=False, related_name=
        '%(app_label)s_%(class)s_set', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
