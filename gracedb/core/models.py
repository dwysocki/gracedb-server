from collections import OrderedDict
import logging
import re

from django.db import models, connection
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
        This custom save method does a SELECT and INSERT in a single raw SQL
        query in order to properly handle a quasi-autoincrementing field, which
        is used to identify instances associated with a ForeignKey. With this
        method, concurrency issues are handled by the database backend.
        Ex: EventLog instances associated with an Event should be numbered from
        1 to N, based on the order of their submission.

        This has been tested with the following classes:
            EventLog, EMObservation, EMFootprint, EMBBEventLog, VOEvent

        Thorough testing is needed to use this method for a new model. Note
        that this method may not work properly for non-MySQL backends.

        Requires AUTO_FIELD and AUTO_CONSTRAINTS to be defined.
        """

        # Check database type
        if connection.vendor != 'mysql':
            raise DatabaseError(_('The custom AutoIncrementModel '
                'auto_increment_save method is not compatible with non-MySQL '
                'backends'))

        # Get some useful information
        meta = self.__class__._meta
        pk_set = self._get_pk_val() is not None

        # Get model fields, except for primary key field.
        fields = [f for f in meta.local_concrete_fields if not
            isinstance(f, models.fields.AutoField)]

        # Check type of self.AUTO_CONSTRAINTS
        if not isinstance(self.AUTO_CONSTRAINTS, (tuple, list)):
            raise TypeError(_('AUTO_CONSTRAINTS should be a tuple or list'))

        # Check constraint fields
        f_names = [f.name for f in fields]
        for constraint_field in self.AUTO_CONSTRAINTS:
            if constraint_field not in f_names:
                raise ValueError(_(('Constraint {0} is not a field for '
                    'model {1}').format(constraint_field,
                    self.__class__.__name__)))

        # Check auto field
        if self.AUTO_FIELD not in f_names:
            raise ValueError(_(('AUTO_FIELD {0} is not a field for '
                'model {1}').format(self.auto_field, self.__class__.__name__)))

        # Setup for generating base SQL query for doing an INSERT.
        query = models.sql.InsertQuery(self.__class__)
        query.insert_values(fields, objs=[self])
        compiler = query.get_compiler(using=self.__class__._base_manager.db)
        compiler.return_id = meta.has_auto_field and not pk_set

        # Useful function
        qn = compiler.quote_name_unless_alias

        # Compile multiple constraints with AND
        constraint_fields = map(meta.get_field, self.AUTO_CONSTRAINTS)
        constraint_list = ["{0}=%s".format(qn(f.column))
            for f in constraint_fields]
        constraint_values = [f.get_db_prep_value(getattr(self, f.column),
            compiler.connection) for f in constraint_fields]
        constraint_str = " AND ".join(constraint_list)

        with compiler.connection.cursor() as cursor:
            # Get base SQL query as string.
            for sql, params in compiler.as_sql():
                # Modify SQL string to do an INSERT with SELECT.
                # NOTE: it's unlikely that the following will generate
                # a functional database query for non-MySQL backends.

                # Replace VALUES (%s, %s, ..., %s) with
                # SELECT %s, %s, ..., %s
                sql = re.sub(r"VALUES \((.*)\)", r"SELECT \1", sql)

                # Add table to SELECT from, as well as constraints
                sql += " FROM {tbl_name} WHERE {constraints}".format(
                    tbl_name=qn(meta.db_table),
                    constraints=constraint_str
                )

                # Get index corresponding to AUTO_FIELD.
                af_idx = [f.attname for f in fields].index(self.AUTO_FIELD)
                # Put this directly in the SQL; cursor.execute quotes it
                # as a literal, which causes the SQL command to fail.
                # We shouldn't have issues with SQL injection because
                # AUTO_FIELD should never be a user-defined parameter.
                del params[af_idx]
                sql = re.sub(r"((%s, ){{{0}}})%s".format(af_idx),
                    r"\1IFNULL(MAX({af}),0)+1", sql, 1).format(
                    af=self.AUTO_FIELD)

                # Add constraint values to params
                params += constraint_values

                # Execute SQL command.
                cursor.execute(sql, params)

            # Get primary key from database and set it in memory.
            if compiler.connection.features.can_return_id_from_insert:
                id = compiler.connection.ops.fetch_returned_insert_id(cursor)
            else:
                id = compiler.connection.ops.last_insert_id(cursor,
                    meta.db_table, meta.pk.column)
            self._set_pk_val(id)

            # Refresh object in memory in order to get AUTO_FIELD value.
            self.refresh_from_db()

            # Prevents check for unique primary key - needed to prevent an
            # IntegrityError when the object was just created and we try to
            # update it while it's still in memory
            self._state.adding = False


    def auto_increment_update(self, update_field_name, constraints=[],
        allow_update_to_nonnull=False):
        """
        UPDATE superevents_superevent SET gw_date_number = (SELECT N FROM (SELECT IFNULL(MAX(gw_date_number),0)+1 as N FROM superevents_superevent WHERE t_0_date='1980-01-06' AND is_gw=1) AS y) WHERE id=41;
        """

        if (not allow_update_to_nonnull and getattr(self, update_field_name)
            is not None):
            raise ValueError(_(('Attempt to update a non-null constrained auto'
                'field for object {0}. Not allowed.').format(self.__str__)))

        # Setup for generating base SQL query for doing an update
        meta = self._meta
        field = meta.get_field(update_field_name)
        values = [(field, None, field.pre_save(self, False))]
        query = models.sql.UpdateQuery(self.__class__)
        query.add_update_fields(values)
        compiler = query.get_compiler(using=self.__class__._base_manager.db)

        # Useful function
        qn = compiler.quote_name_unless_alias

        # SQL for doing autoincrement
        custom_sql= ("(SELECT N FROM (SELECT IFNULL(MAX({field}),0)+1 AS N "
            "FROM {tbl_name}").format(tbl_name=qn(meta.db_table),
            field=update_field_name)

        # Convert list of field names to be used as constraints into database
        # column names and their values (retrieved from the instance itself)
        constraint_fields = [meta.get_field(f) for f in constraints]
        constraint_list = ["{0}=%s".format(qn(f.column)) for f in constraint_fields]
        values = [f.get_db_prep_value(getattr(self, f.column),
            compiler.connection) for f in constraint_fields]

        # Add constraints to custom SQL (if they are provided)
        if constraint_list:
            custom_sql += (" WHERE " + " AND ".join(constraint_list))

        # Add end
        custom_sql += (") AS temp) WHERE id={pk};".format(pk=self.pk))

        # Replace NULL in base sql update query
        base_sql = compiler.as_sql()[0]
        sql = base_sql.replace('NULL', custom_sql)

        # Execute sql
        compiler.connection.cursor().execute(sql, values)

        # Refresh from database
        self.refresh_from_db(fields=[update_field_name])


class LogBase(models.Model):
    """
    Abstract base class for log message-type objects. Concrete derived
    classes will probably want to add a ForeignKey to another model.

    Used in events.EventLog, superevents.Log
    """
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(UserModel, null=False)
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
        '%(app_label)s_%(class)s_set')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
