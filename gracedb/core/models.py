from django.contrib.auth import get_user_model
from django.db import models, connection
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from django.forms.models import model_to_dict
from django.db.models import QuerySet

import re
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

UserModel = get_user_model()


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
    AUTO_CONSTRAINT: name of field which is used as a constraint; i.e., the
                     AUTO_FIELD increments relative to the number of rows in
                     the table which share the same value of this field.
    """
    AUTO_FIELD = None
    AUTO_CONSTRAINT = None

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):

        # Do a normal save if this is not an insert (i.e., the instance has a
        # primary key already).
        pk_set = self._get_pk_val() is not None
        if pk_set:
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

        Requires AUTO_FIELD and AUTO_CONSTRAINT to be defined.
        """

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

        # Setup for generating base SQL query for doing an INSERT.
        query = models.sql.InsertQuery(self.__class__)
        query.insert_values(fields, objs=[self])
        compiler = query.get_compiler(using=self.__class__._base_manager.db)
        compiler.return_id = meta.has_auto_field and not pk_set

        # Useful function
        qn = compiler.quote_name_unless_alias

        fk_field = meta.get_field(self.AUTO_CONSTRAINT)
        with compiler.connection.cursor() as cursor:
            # Get base SQL query as string.
            for sql, params in compiler.as_sql():
                # Modify SQL string to do an INSERT with SELECT.
                # NOTE: it's unlikely that the following will generate
                # a functional database query for non-MySQL backends.

                # Replace VALUES (%s, %s, ..., %s) with
                # SELECT %s, %s, ..., %s
                sql = re.sub(r"VALUES \((.*)\)", r"SELECT \1", sql)

                # Add table to SELECT from and ForeignKey id corresponding to
                # our autoincrement field.
                sql += " FROM {tbl_name} WHERE {fk_name}='{fk_id}'".format(
                    tbl_name=qn(meta.db_table),
                    fk_name=qn(fk_field.column),
                    fk_id=fk_field.get_db_prep_value(
                        getattr(self, fk_field.column), compiler.connection)
                )

                # Get index corresponding to AUTO_FIELD.
                af_idx = [f.name for f in fields].index(self.AUTO_FIELD)
                # Put this directly in the SQL; cursor.execute quotes it
                # as a literal, which causes the SQL command to fail.
                # We shouldn't have issues with SQL injection because
                # AUTO_FIELD should never be a user-defined parameter.
                del params[af_idx]
                sql = re.sub(r"((%s, ){{{0}}})%s".format(af_idx),
                    r"\1IFNULL(MAX({af}),0)+1", sql, 1).format(
                    af=self.AUTO_FIELD)

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

        if not allow_update_to_nonnull and getattr(self, update_field_name) is not None:
            logger.warning('Attempt to auto increment a non-null field for '
                'object {0}. Not allowed.'.format(self.__str__))
            return

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
        constraint_list = ["{0}=%s".format(qn(f.attname)) for f in constraint_fields]
        values = [f.get_db_prep_value(getattr(self, f.attname),
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

    def fileurl(self):
        # Override this on derived classes
        return NotImplemented

    def hasImage(self):
        # XXX hacky
        IMAGE_EXT = ['png', 'gif', 'jpg']
        return (self.filename and self.filename[-3:].lower() in IMAGE_EXT)


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


class ModelToDictMixin(object):
    """
    Defines a to_dict() method which deserializes a model object to
    a dictionary. Allows the addition of keys which are not directly attached
    to the model and whose values are customizable.

    Default configuration for the dict is provided by the
    default_dict_mapping() method.

    The update_dict_mapping() method is used to override parts of the
    default mapping. Should not need to be customized, since to_dict() passes
    kwargs to it which it should be able to handle.
    """
    QS_KEY = 'queryset'
    QS_PROP_KEY = 'object_property'

    def to_dict(self, **kwargs):
        """
        Usage:
            object.to_dict()
            object.to_dict(**{'creator': object.creator.pk})
            object.to_dict(**{'comments': {'object_property': 'pk'}})
        """
        dict_mapping = self.default_dict_mapping()
        dict_mapping = self._update_dict_mapping(dict_mapping, **kwargs)
        if not dict_mapping:
            return model_to_dict(self)

        out_dict = OrderedDict()
        for k,v in dict_mapping.iteritems():
            if isinstance(v, dict):
                if not (v.has_key(self.QS_KEY) and 
                        v.has_key(self.QS_PROP_KEY)):
                    raise KeyError(_('Must specify {qs_key} and {qs_prop_key} '
                        'when mapping model queryset "fields" to dict'))

                queryset = v[self.QS_KEY]
                prop = v[self.QS_PROP_KEY]
                if prop.endswith('()'):
                    prop = prop[:-2]
                if callable(getattr(queryset.model, prop)):
                    value = [getattr(obj, prop)() for obj in queryset]
                else: 
                    value = [getattr(obj, prop) for obj in queryset]
            else:
                value = v
            out_dict[k] = value

        return out_dict

    def _update_dict_mapping(self, dict_mapping, **kwargs):
        for k,v in kwargs.iteritems():
            if isinstance(v, dict):
                if not dict_mapping.has_key(kw):
                    dict_mapping[kw] = {}
                for k2,v2 in v.iteritems():
                    dict_mapping[k][k2] = v2
            else:
                dict_mapping[k] = v

        return dict_mapping

    def default_dict_mapping(self):
        """
        Defines a schema for mapping model fields or related object fields
        to a dictionary.  Cases where a field returns multiple objects (like
        m2m or reverse foreign key relationships) should be provided as a dict
        which has the 'queryset' and 'object_property' (REQUIRED).

        Example:
            mapping = {
                'creator': self.creator.username,
                'comments': {
                    self.QS_KEY: self.comment_set.all(),
                    self.QS_PROP_KEY: 'message',
                },
            }

        This method should be overridden by classes which use this mixin.
        """
        return {}
