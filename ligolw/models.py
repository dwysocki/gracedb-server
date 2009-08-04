
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note:
#   You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
#   into your database.

from django.db import models

class CoincDefiner(models.Model):
    search = models.CharField(max_length=150, blank=True)
    description = models.CharField(max_length=150, blank=True)
    coinc_def_id = models.CharField(max_length=150, primary_key=True)
    search_coinc_type = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'coinc_definer'

class TimeSlide(models.Model):
    instrument = models.CharField(max_length=150, primary_key=True)
    time_slide_id = models.CharField(max_length=150, primary_key=True)
    process_id = models.CharField(max_length=150, blank=True)
    offset = models.FloatField(null=True, blank=True)
    class Meta:
        db_table = u'time_slide'

class Process(models.Model):
    program = models.CharField(max_length=150, blank=True)
    version = models.CharField(max_length=150, blank=True)
    cvs_repository = models.CharField(max_length=150, blank=True)
    cvs_entry_time = models.IntegerField(null=True, blank=True)
    comment = models.CharField(max_length=150, blank=True)
    is_online = models.IntegerField(null=True, blank=True)
    node = models.CharField(max_length=150, blank=True)
    username = models.CharField(max_length=150, blank=True)
    unix_procid = models.IntegerField(null=True, blank=True)
    start_time = models.IntegerField(null=True, blank=True)
    end_time = models.IntegerField(null=True, blank=True)
    jobid = models.IntegerField(null=True, blank=True)
    domain = models.CharField(max_length=150, blank=True)
    ifos = models.CharField(max_length=150, blank=True)
    process_id = models.CharField(max_length=150, primary_key=True)
    class Meta:
        db_table = u'process'


class CoincEvent(models.Model):
    coinc_event_id = models.CharField(max_length=150, primary_key=True)
    instruments = models.CharField(max_length=150, blank=True)
    nevents = models.IntegerField(null=True, blank=True)
    #process_id = models.CharField(max_length=150, blank=True)
    process =  models.ForeignKey(Process, blank=True)
    #coinc_def_id = models.CharField(max_length=150, blank=True)
    coinc_def = models.ForeignKey(CoincDefiner, blank=True)
    #time_slide_id = models.CharField(max_length=150, blank=True)
    time_slide = models.ForeignKey(TimeSlide, blank=True)
    likelihood = models.FloatField(null=True, blank=True)
    class Meta:
        db_table = u'coinc_event'

class CoincEventMap(models.Model):
    event_id = models.CharField(max_length=150, blank=True)
    table_name = models.CharField(max_length=150, blank=True)
    coinc_event_id = models.CharField(max_length=150, blank=True)
    class Meta:
        db_table = u'coinc_event_map'

class CoincInspiral(models.Model):
    false_alarm_rate = models.FloatField(null=True, blank=True)
    mchirp = models.FloatField(null=True, blank=True)
    #coinc_event_id = models.CharField(max_length=150, blank=True)
    coinc_event = models.OneToOneField(CoincEvent, primary_key=True)
    combined_far = models.FloatField(null=True, blank=True)
    mass = models.FloatField(null=True, blank=True)
    end_time = models.IntegerField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    end_time_ns = models.IntegerField(null=True, blank=True)
    ifos = models.CharField(max_length=150, blank=True)
    class Meta:
        db_table = u'coinc_inspiral'


class Experiment(models.Model):
    search = models.CharField(max_length=150, blank=True)
    instruments = models.CharField(max_length=150, blank=True)
    search_group = models.CharField(max_length=150, blank=True)
    comments = models.CharField(max_length=150, blank=True)
    lars_id = models.CharField(max_length=150, blank=True)
    experiment_id = models.CharField(max_length=150, primary_key=True)
    gps_start_time = models.IntegerField(null=True, blank=True)
    gps_end_time = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'experiment'

class ExperimentMap(models.Model):
    experiment_summ_id = models.CharField(max_length=150, blank=True)
    #coinc_event_id = models.CharField(max_length=150, blank=True)
    coinc_event = models.ForeignKey(CoincEvent, blank=True)
    class Meta:
        db_table = u'experiment_map'

class ExperimentSummary(models.Model):
    sim_proc_id = models.CharField(max_length=150, blank=True)
    datatype = models.CharField(max_length=150, blank=True)
    experiment_summ_id = models.CharField(max_length=150, primary_key=True)
    nevents = models.IntegerField(null=True, blank=True)
    #experiment_id = models.CharField(max_length=150, blank=True)
    experiment = models.ForeignKey(Experiment, blank=True)
    duration = models.IntegerField(null=True, blank=True)
    #time_slide_id = models.CharField(max_length=150, blank=True)
    time_slide = models.ForeignKey(TimeSlide, blank=True)
    veto_def_name = models.CharField(max_length=150, blank=True)
    rowid = models.IntegerField(unique=True, db_column='ROWID') # Field name made lowercase.
    class Meta:
        db_table = u'experiment_summary'

class Ligolwids(models.Model):
    tablename = models.CharField(max_length=90, primary_key=True)
    nextid = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'ligolwids'

class ProcessParams(models.Model):
    program = models.CharField(max_length=150, blank=True)
    #process_id = models.CharField(max_length=150, blank=True)
    process = models.ForeignKey(Process, blank=True)
    param = models.CharField(max_length=150, blank=True)
    type = models.CharField(max_length=150, blank=True)
    value = models.CharField(max_length=150, blank=True)
    class Meta:
        db_table = u'process_params'

class SearchSummary(models.Model):
    #process_id = models.CharField(max_length=150, blank=True)
    process = models.ForeignKey(Process, blank=True)
    shared_object = models.CharField(max_length=150, blank=True)
    lalwrapper_cvs_tag = models.CharField(max_length=150, blank=True)
    lal_cvs_tag = models.CharField(max_length=150, blank=True)
    comment = models.CharField(max_length=150, blank=True)
    ifos = models.CharField(max_length=150, blank=True)
    in_start_time = models.IntegerField(null=True, blank=True)
    in_start_time_ns = models.IntegerField(null=True, blank=True)
    in_end_time = models.IntegerField(null=True, blank=True)
    in_end_time_ns = models.IntegerField(null=True, blank=True)
    out_start_time = models.IntegerField(null=True, blank=True)
    out_start_time_ns = models.IntegerField(null=True, blank=True)
    out_end_time = models.IntegerField(null=True, blank=True)
    out_end_time_ns = models.IntegerField(null=True, blank=True)
    nevents = models.IntegerField(null=True, blank=True)
    nnodes = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = u'search_summary'

class SearchSummvars(models.Model):
    #process_id = models.CharField(max_length=150, blank=True)
    process = models.ForeignKey(Process, blank=True)
    name = models.CharField(max_length=150, blank=True)
    string = models.CharField(max_length=150, blank=True)
    value = models.FloatField(null=True, blank=True)
    search_summvar_id = models.CharField(max_length=150, primary_key=True)
    class Meta:
        db_table = u'search_summvars'

class SnglInspiral(models.Model):
    process_id = models.CharField(max_length=150, blank=True)
    ifo = models.CharField(max_length=150, blank=True)
    search = models.CharField(max_length=150, blank=True)
    channel = models.CharField(max_length=150, blank=True)
    end_time = models.IntegerField(null=True, blank=True)
    end_time_ns = models.IntegerField(null=True, blank=True)
    end_time_gmst = models.FloatField(null=True, blank=True)
    impulse_time = models.IntegerField(null=True, blank=True)
    impulse_time_ns = models.IntegerField(null=True, blank=True)
    template_duration = models.FloatField(null=True, blank=True)
    event_duration = models.FloatField(null=True, blank=True)
    amplitude = models.FloatField(null=True, blank=True)
    eff_distance = models.FloatField(null=True, blank=True)
    coa_phase = models.FloatField(null=True, blank=True)
    mass1 = models.FloatField(null=True, blank=True)
    mass2 = models.FloatField(null=True, blank=True)
    mchirp = models.FloatField(null=True, blank=True)
    mtotal = models.FloatField(null=True, blank=True)
    eta = models.FloatField(null=True, blank=True)
    kappa = models.FloatField(null=True, blank=True)
    chi = models.FloatField(null=True, blank=True)
    tau0 = models.FloatField(null=True, blank=True)
    tau2 = models.FloatField(null=True, blank=True)
    tau3 = models.FloatField(null=True, blank=True)
    tau4 = models.FloatField(null=True, blank=True)
    tau5 = models.FloatField(null=True, blank=True)
    ttotal = models.FloatField(null=True, blank=True)
    psi0 = models.FloatField(null=True, blank=True)
    psi3 = models.FloatField(null=True, blank=True)
    alpha = models.FloatField(null=True, blank=True)
    alpha1 = models.FloatField(null=True, blank=True)
    alpha2 = models.FloatField(null=True, blank=True)
    alpha3 = models.FloatField(null=True, blank=True)
    alpha4 = models.FloatField(null=True, blank=True)
    alpha5 = models.FloatField(null=True, blank=True)
    alpha6 = models.FloatField(null=True, blank=True)
    beta = models.FloatField(null=True, blank=True)
    f_final = models.FloatField(null=True, blank=True)
    snr = models.FloatField(null=True, blank=True)
    chisq = models.FloatField(null=True, blank=True)
    chisq_dof = models.IntegerField(null=True, blank=True)
    bank_chisq = models.FloatField(null=True, blank=True)
    bank_chisq_dof = models.IntegerField(null=True, blank=True)
    cont_chisq = models.FloatField(null=True, blank=True)
    cont_chisq_dof = models.IntegerField(null=True, blank=True)
    sigmasq = models.FloatField(null=True, blank=True)
    rsqveto_duration = models.FloatField(null=True, blank=True)
    gamma0 = models.FloatField(null=True, db_column='Gamma0', blank=True) # Field name made lowercase.
    gamma1 = models.FloatField(null=True, db_column='Gamma1', blank=True) # Field name made lowercase.
    gamma2 = models.FloatField(null=True, db_column='Gamma2', blank=True) # Field name made lowercase.
    gamma3 = models.FloatField(null=True, db_column='Gamma3', blank=True) # Field name made lowercase.
    gamma4 = models.FloatField(null=True, db_column='Gamma4', blank=True) # Field name made lowercase.
    gamma5 = models.FloatField(null=True, db_column='Gamma5', blank=True) # Field name made lowercase.
    gamma6 = models.FloatField(null=True, db_column='Gamma6', blank=True) # Field name made lowercase.
    gamma7 = models.FloatField(null=True, db_column='Gamma7', blank=True) # Field name made lowercase.
    gamma8 = models.FloatField(null=True, db_column='Gamma8', blank=True) # Field name made lowercase.
    gamma9 = models.FloatField(null=True, db_column='Gamma9', blank=True) # Field name made lowercase.
    event_id = models.CharField(max_length=150, primary_key=True)
    class Meta:
        db_table = u'sngl_inspiral'

