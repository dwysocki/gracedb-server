import json
import logging
from math import isnan, sqrt
import numbers
import os

from ligo.lw.utils import load_filename, load_fileobj
from ligo.lw.lsctables import CoincInspiralTable, SnglInspiralTable, use_in
from ligo.lw.lsctables import SimInspiralTable, CoincTable
from core.ligolw import FlexibleLIGOLWContentHandler
import voeventparse as vp

from core.time_utils import utc_datetime_to_gps_float
from core.vfile import create_versioned_file
from .models import EventLog
from .models import SingleInspiral
from .models import SimInspiralEvent
from .serialize import populate_omega_tables, write_output_files

try:
    from StringIO import StringIO
except ImportError:  # python >= 3
    from io import StringIO


# Set up logger
logger = logging.getLogger(__name__)

use_in(FlexibleLIGOLWContentHandler)

# This function checks for 'inf' in a float field, asks the database
# what's the maximum value it can accept for that field, and returns
# that value. Since the database query will introduce some overhead,
# I'm not going to use this to check all fields.

from django.db import connection
def cleanData(val, field_name, table_name='events_event'):
    if val is None:
        return val
    elif isinstance(val, float):
        if abs(val)==float('inf'):
            cursor = connection.cursor()
            cursor.execute('SELECT MAX(%s) from %s' % (field_name, table_name))
            maxval = cursor.fetchone()[0]
            return maxval
        else:
            return val
    elif isinstance(val, str):
        raise ValueError("Unrecognized string in the %s column" % field_name)
    else:
        raise ValueError("Unrecognized value in column %s" % field_name)

def handle_uploaded_data(event, datafilename,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml',
                         file_contents=None):

    if datafilename:
        log = EventLog(event=event,
                       filename=os.path.basename(datafilename),
                       file_version=0,
                       issuer=event.submitter,
                       comment="Original Data")
        log.save()

    # XXX If you can manage to get rid of the MBTA .gwf parsing and
    # the Omega event parsing, you can deprecate temp_data_loc. It 
    # has already been removed from the alerts.
    temp_data_loc = ""
    warnings = []

    pipeline = event.pipeline.name

    if pipeline in [ 'gstlal', 'spiir', 'pycbc', ] or (pipeline in ['MBTA', 'MBTAOnline'] and '.xml' in datafilename):
        log_comment = "Log File Created"
        # Wildly speculative wrt HM

        try:
            xmldoc = load_filename(datafilename, contenthandler = FlexibleLIGOLWContentHandler)
        except Exception as e:
            message = "Could not read data (%s)" % str(e)
            EventLog(event=event, issuer=event.submitter, comment=message).save()
            return

        # Try reading the CoincInspiralTable
        try:
            coinc_table = CoincInspiralTable.get_table(xmldoc)[0]
        except Exception as e:
            warnings.append("Could not extract coinc inspiral table.")
            return temp_data_loc, warnings

        # Create Log Data
        try:
            log_data = ["Pipeline: %s" % pipeline]
            if event.search:
                log_data.append("Search: %s" % event.search.name)

            mchirp   = coinc_table.mchirp
            mass     = coinc_table.mass
            end_time = (coinc_table.end_time, coinc_table.end_time_ns)

            # Awful kludge for handling nan for snr
            snr = coinc_table.snr
            try:
                if (isinstance(snr, numbers.Number) and isnan(snr)):
                    snr = None
            except Exception as e:
                pass

            ifos     = coinc_table.ifos
            far      = coinc_table.combined_far

            if mchirp is not None:
                log_data.append("MChirp: %0.3f" % mchirp)
            else:
                log_data.append("MChirp: ---")
            log_data.append("MTot: %s" % mass)
            log_data.append("End Time: %d.%09d" % end_time)
            if snr is not None:
                log_data.append("SNR: %0.3f" % snr)
            else:
                log_data.append("SNR: ---")
            log_data.append("IFOs: %s" % ifos)
            if far is not None:
                log_data.append("FAR: %0.3e" % far)
            else:
                log_data.append("FAR: ---")
        except Exception as e:
            log_comment = "Problem Creating Log File"
            log_data = ["Cannot create log file", "error was:", str(e)]

        log_data = "\n".join(log_data)

        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data,
                           xml_fname=coinc_table_filename,
                           log_fname=log_filename)

        # Create EventLog entries about these files.

        log = EventLog(event=event,
                       filename=log_filename,
                       file_version=0,
                       issuer=event.submitter,
                       comment=log_comment)
        log.save()

        log = EventLog(event=event,
                       filename=coinc_table_filename,
                       file_version=0,
                       issuer=event.submitter,
                       comment="Coinc Table Created")
        log.save()

        # Extract relevant data from xmldoc to put into event record.
        event.gpstime = coinc_table.end_time + float(coinc_table.end_time_ns)/1.e9
        event.far = coinc_table.combined_far
        # Try to get the coinc_event_table
        try:
            coinc_event_table = CoincTable.get_table(xmldoc)[0]
        except Exception as e:
            warnings.append("Could not extract coinc event table.")
            return temp_data_loc, warnings
        event.nevents = coinc_event_table.nevents
        event.likelihood = cleanData(coinc_event_table.likelihood,'likelihood')

        # event.instruments is attached to the base Event and event.ifos is
        # part of the CoincInspiralEvent
        event.ifos             = ifos
        event.instruments      = ifos
        event.end_time         = end_time[0]
        event.end_time_ns      = end_time[1]
        event.mass             = mass
        event.mchirp           = mchirp
        event.minimum_duration = getattr(coinc_table, "minimum_duration", None)
        event.snr              = snr
        event.false_alarm_rate = getattr(coinc_table, "false_alarm_rate", None)
        event.combined_far     = far
        event.save()

        # Extract Single Inspiral Information
        s_inspiral_table = SnglInspiralTable.get_table(xmldoc)
        # If this is a replacement, we might already have single inspiral tables
        # associated. So we should re-create them.
        event.singleinspiral_set.all().delete()
        SingleInspiral.create_events_from_ligolw_table(s_inspiral_table, event)

    elif pipeline == 'HardwareInjection':
        log_comment = "Log File Created"
        if datafilename:
            xmldoc = load_filename(datafilename, contenthandler=FlexibleLIGOLWContentHandler)
        elif file_contents:
            f = StringIO(file_contents)
            xmldoc, digest = load_fileobj(f, contenthandler=FlexibleLIGOLWContentHandler)
        else:
            msg = "If you wanna make an injection event, I'm gonna need a filepath or filecontents."
            raise ValueError(msg)

        origdata = SimInspiralTable.get_table(xmldoc)
        origdata = origdata[0]
        end_time = (origdata.geocent_end_time, origdata.geocent_end_time_ns)
        event.gpstime = end_time[0] + float(end_time[1])/1e9

#        # Create Log Data
#        try:
#            log_data = ["Pipeline: %s" % pipeline]
#            mchirp   = origdata.mchirp
#            mass     = (origdata.mass1, origdata.mass2)
#            spin1    = (origdata.spin1x, origdata.spin1y, origdata.spin1z)
#            spin2    = (origdata.spin2x, origdata.spin2y, origdata.spin2z)
#            #waveform = origdata.waveform
#
#            if mchirp is not None:
#                log_data.append("MChirp: %0.3f" % mchirp)
#            else:
#                log_data.append("MChirp: ---")
#            log_data.append("Component Masses: %f %f" % mass)
#            log_data.append("Component 1 Spin: (%f, %f, %f)" % spin1)
#            log_data.append("Component 2 Spin: (%f, %f, %f)" % spin2)
#            log_data.append("Geocentric End Time: %d.%09d" % end_time)
#        except Exception as e:
#            log_comment = "Problem Creating Log File"
#            log_data = ["Cannot create log file", "error was:", str(e)]
#        log_data = "\n".join(log_data)

        # Assign attributes from the SimInspiralTable
        field_names = SimInspiralEvent.field_names()
        for column in field_names:
            try:
                value = getattr(origdata, column)
                setattr(event, column, value)
            except:
                pass
        event.save()

        # XXX Let's not write output files for the injections. There are 
        # simply too many of them.
        #
        #output_dir = os.path.dirname(datafilename)
        #write_output_files(output_dir, xmldoc, log_data,
        #                   xml_fname=coinc_table_filename,
        #                   log_fname=log_filename)
        #log = EventLog(event=event,
        #               filename=log_filename,
        #               issuer=event.submitter,
        #               comment=log_comment)
        #log.save()

#   elif pipeline == 'Omega':
#       #here's how it works for bursts
#       #xmldoc, log_data, temp_data_loc = populate_burst_tables("initial.data")
#       #write_output_files('.', final_xmldoc, log_data)

#       xmldoc, log_data, temp_data_loc = populate_omega_tables(datafilename)
#       output_dir = os.path.dirname(datafilename)
#       write_output_files(output_dir, xmldoc, log_data)

#       # Create EventLog entries about these files.
#       log = EventLog(event=event,
#                      filename=log_filename,
#                      file_version=0,
#                      issuer=event.submitter,
#                      comment="Log File Created" )
#       log.save()

#       log = EventLog(event=event,
#                      filename=coinc_table_filename,
#                      file_version=0,
#                      issuer=event.submitter,
#                      comment="Coinc Table Created")
#       log.save()

#       # Extract relevant data from xmldoc.
#       mb_table = MultiBurstTable.get_table(xmldoc)
#       mb_table = mb_table[0]
#       event.gpstime = mb_table.start_time

#       # Try reading the CoincInspiralTable to get the ifos
#       warnings = []
#       try:
#           coinc_table = CoincInspiralTable.get_table(xmldoc)[0]
#       except Exception as e:
#           warnings += "Could not extract coinc inspiral table."
#           return temp_data_loc, warnings

#       coinc_event_table = CoincTable.get_table(xmldoc)[0]
#       event.instruments = coinc_table.ifos
#       event.nevents = coinc_event_table.nevents
#       event.likelihood = cleanData(coinc_event_table.likelihood, 'likelihood')
#       event.save()
    elif pipeline in ['CWB', 'CWB2G']:

        data = CwbData(datafilename)

        # XXX Refactor
        # the following should be common if/when the other analyses get a Translator class.

        data.populateEvent(event)
        event.save()

        outputDataDir = os.path.dirname(datafilename)

        if data.writeCoincFile( os.path.join(outputDataDir, "coinc.xml") ):
            log = EventLog(event=event,
                           filename="coinc.xml",
                           file_version=0,
                           issuer=event.submitter,
                           comment="Coinc Table Created")
            log.save()

        if data.writeLogfile(outputDataDir, "event.log"):
            log = EventLog(event=event,
                           filename="event.log",
                           file_version=0,
                           issuer=event.submitter,
                           comment="Log File Created" )
            log.save()

        # Log the link to the CED.
        if data.data['ced_link']:
            comment = '<a href="%s">Coherent Event Display (CED)</a>' % data.data['ced_link']
            log = EventLog(event=event,
                           issuer=event.submitter,
                           comment=comment)
            log.save()


        # Log the link to the skymap.
        if data.data['fits_skymap_link']:
            comment = '<a href="%s">FITS skymap</a>' % data.data['fits_skymap_link']
            log = EventLog(event=event,
                           issuer=event.submitter,
                           comment=comment)
            log.save()

    elif pipeline in ['Swift', 'Fermi', 'SNEWS', 'INTEGRAL','AGILE']:
        # Get the event time from the VOEvent file
        error = None
        populateGrbEventFromVOEventFile(datafilename, event)
    elif pipeline == 'oLIB':
        # lambda function for converting to a type if not None
        typecast = lambda t, v: t(v) if v is not None else v
        n_int = lambda v: typecast(int, v)
        n_float = lambda v: typecast(float, v)

        # Open event file and get data
        event_file = open(datafilename, 'r')
        event_file_contents = event_file.read()
        event_file.close()
        event_dict = json.loads(event_file_contents)

        # Extract relevant data from dictionary to put into event record.
        event.gpstime     = n_float(event_dict.get('gpstime'))
        event.far         = n_float(event_dict.get('FAR'))
        event.instruments = event_dict['instruments']
        event.nevents     = n_int(event_dict.get('nevents', 1))
        event.likelihood  = n_float(event_dict.get('likelihood', None))

        # Assign analysis-specific attributes
        event.bci         = n_float(event_dict.get('BCI', None))
        event.quality_mean = n_float(event_dict.get('quality_posterior_mean', None))
        event.quality_median = n_float(event_dict.get('quality_posterior_median', None))
        event.bsn         = n_float(event_dict.get('BSN', None))
        event.omicron_snr_network = n_float(event_dict.get('Omicron_SNR_Network', None))
        event.omicron_snr_H1 = n_float(event_dict.get('Omicron_SNR_H1', None))
        event.omicron_snr_L1 = n_float(event_dict.get('Omicron_SNR_L1', None))
        event.omicron_snr_V1 = n_float(event_dict.get('Omicron_SNR_V1', None))
        event.hrss_mean   = n_float(event_dict.get('hrss_posterior_mean', None))
        event.hrss_median   = n_float(event_dict.get('hrss_posterior_median', None))
        event.frequency_mean   = n_float(event_dict.get('frequency_posterior_mean', None))
        event.frequency_median = n_float(event_dict.get('frequency_posterior_median', None))
        event.save()

    elif pipeline == 'MLy':
        # copying this bit for MLy json files.
        # lambda function for converting to a type if not None
        typecast = lambda t, v: t(v) if v is not None else v
        n_int = lambda v: typecast(int, v)
        n_float = lambda v: typecast(float, v)

        # Open event file and get data
        event_file = open(datafilename, 'r')
        event_file_contents = event_file.read()
        event_file.close()
        event_dict = json.loads(event_file_contents)

        # Extract attributes:
        event.gpstime   = n_float(event_dict.get('gpstime'))
        event.far       = n_float(event_dict.get('far'))

        # Extract other attributes:
        event.central_freq  = n_float(event_dict.get('central_freq', None))
        event.central_time  = n_float(event_dict.get('central_time', None))
        event.bandwidth     = n_float(event_dict.get('bandwidth', None))
        event.duration      = n_float(event_dict.get('duration', None))

        # event.instruments is attached to the base Event and event.ifos is
        # part of the MLyBurstEvent
        ifos                = event_dict.get('ifos', None)
        event.ifos          = ifos
        event.instruments   = ifos



        # Safely check for 'scores' dictionary:
        scores = event_dict.get('scores', None)
        if isinstance(scores, dict):
            event.score_coinc   = n_float(scores.get('coincidence'))
            event.score_coher   = n_float(scores.get('coherency'))
            event.score_comb    = n_float(scores.get('combined'))

        event.save()

    else:
        # XXX should we do something here?
        pass

    return temp_data_loc, warnings

# Let's try to:
#
#    - get ligolw stuff out of gracedb client.
#    - re-factor this stuff to be easier to read/maintain/update
#
# We shall start with cWB
#

def val_or_dashes(val):
    if val is None:
        return "---"
    return val

class Translator(object):
    event_type = "Undefined"  # override

    def getData(self):
        # override
        raise(NotImplemented)

    def castData(self, data):

        # convert floats to floats
        for key in ['far']:
            if data[key]:
                data[key] = float(data[key])

    def populateEvent(self, event):
        data = self.getData()

        event.gpstime = data.get('gpstime')
        event.likelihood = data.get('likelihood')
        event.instruments = data.get('instruments')
        event.far = data.get('far')

    def logData(self):
        data = self.getData()
        logdata = []
        logdata.append("Event Type: %s" % self.event_type)
        logdata.append("Time: %s" % data.get('gpstime', '---'))
        logdata.append("Duration: %s" % data['rawdata'].get('duration',["---"])[0])
        logdata.append("Frequency: %s" % data['rawdata'].get('frequency',["---"])[0])
        logdata.append("Bandwidth: %s" % data['rawdata'].get('bandwidth',["---"])[0])
        logdata.append("RA: %s" % data['rawdata'].get('phi',[None,None,"---"])[2])
        logdata.append("Dec: %s" % data['rawdata'].get('theta',[None,None,"---"])[2])
        logdata.append("Effective SNR: %s" % data['rawdata'].get('rho',["---"])[0])
        logdata.append("IFOs: %s" % val_or_dashes(data.get('instruments')))
        logdata.append("FAR: %s" % val_or_dashes(data.get('far')))
        return "\n".join(logdata)

    def writeLogfile(self, data_directory, filename):
        data = self.logData()
        if data:
            create_versioned_file(filename, data_directory, data)
        return True



class CwbData(Translator):
    event_type = "cWB"

    def __init__(self, datafile, *args, **kwargs):
        self.datafile = datafile
        self.data = None

    def getData(self):
        if not self.data:
            data = self.readData(self.datafile)
            self.castData(data)
        return self.data

    def populateEvent(self, event):
        Translator.populateEvent(self, event)

        # MultiBurst table attributes
        data = self.getData()
        event.ifos          = data.get('ifo')
        event.start_time    = data.get('start_time')
        event.start_time_ns = data.get('start_time_ns')
        event.duration      = data.get('duration')
        event.central_freq  = data.get('central_freq')
        event.bandwidth     = data.get('bandwidth')
        # Single IFO times are cast as a comma-separated string,
        # in same order as the 'ifos' field.
        event.single_ifo_times = data.get('single_ifo_times')

        try:
            event.snr       = sqrt(data.get('likelihood'))
        except:
            event.snr       = 0.0
        # Note that 'snr' here corresponds to 'rho' in the datafile
        event.amplitude     = data.get('snr')
        event.ligo_axis_ra  = data.get('ligo_axis_ra')
        event.ligo_axis_dec = data.get('ligo_axis_dec')

    def readData(self, datafile):
        needToClose = False
        if isinstance(datafile, str) or isinstance(datafile, unicode):
            datafile = open(datafile, "r")
            needToClose = True

        # cWB data look like
        #
        # key0: value value*
        # ...
        # keyN: value value*
        # piles of other data not containing ':'
        # ...
        #  more data we don't care about here
        # ...
        # #significance based on the last 24*6 processed jobs, 4000-1 time shifts
        # 318 1.98515e-05 1026099328 1026503796 53644
        # ...
        #
        #   The 2nd number following the "24*6" line is FAR.
        #
        # https://... (link to CED)
        # https://... (link to fits skymap)

        rawdata = {}

        # Get Key/Value info
        for line in datafile:
            line = line.split(':',1)
            if len(line) == 1:
                break
            key, val = line
            rawdata[key] = val.split()

        datafile.seek(0)
        # scan down for FAR
        next_line_is_far = False
        for line in datafile:
            # Change for Marco Drago, 11/20/14
            #if line.startswith("#significance based on the last 24*6"):
            if line.startswith("#significance based on the last day"):
                next_line_is_far = True
                break
        if next_line_is_far:
            # Can't just do datafile.readline() -- Python objects.
            for line in datafile:
                try:
                    rawdata['far'] = [float(line.split()[1])]
                except Exception:
                    # whatever.
                    pass
                break

        # lambda function for converting to a type if not None
        typecast = lambda t, v: t(v) if v is not None else v
        n_int = lambda v: typecast(int, v)
        n_float = lambda v: typecast(float, v)

        data = {}
        data['rawdata'] = rawdata
        data['gpstime']    = n_float(rawdata.get('time',[None])[0])
        data['likelihood'] = n_float(rawdata.get('likelihood',[None])[0])
        data['far']        = n_float(rawdata.get('far',[None])[0])


        # Get ifos and corresponding GPS times.
        ifos = rawdata.get('ifo',[])
        single_ifo_times = rawdata.get('time',[])
        # Sort both by ifo.
        single_ifo_times = [x for (y,x) in sorted(zip(ifos,single_ifo_times), 
                                                  key=lambda pair: pair[0])]
        ifos.sort()
        data['instruments'] = ','.join(ifos)
        data['single_ifo_times'] = ','.join(single_ifo_times)

        # MultiBurst table attributes
        start =  rawdata.get('start',[None])[0]
        if start is not None:
            integer, frac = start.split('.')
            data['start_time']    = int(integer)
            data['start_time_ns'] = int(frac+(9-len(frac))*'0')
        else:
            data['start_time']    = None
            data['start_time_ns'] = None

        data['ifo'] = ','.join(ifos)
        data['duration']      = n_float(rawdata.get('duration',[None])[0])
        data['central_freq']  = n_float(rawdata.get('frequency',[None])[0])
        data['bandwidth']     = n_float(rawdata.get('bandwidth',[None])[0])
        #data['snr']           = rawdata.get('snr',[None])[0]
        # rho is what log file says is "effective snr"
        data['snr']           = n_float(data['rawdata'].get('rho',[None])[0])
        data['ligo_axis_ra']     = n_float(data['rawdata'].get('phi',[None,None,None])[2])
        data['ligo_axis_dec']    = n_float(data['rawdata'].get('theta',[None,None,None])[2])

        # Check for the links at the end.
        ced_link = None
        fits_skymap_link = None
        datafile.seek(0)
        for line in datafile:
            if line.startswith("http"):
                if line.find(".fits") > 0:
                    fits_skymap_link = line
                else:
                    ced_link = line

        data['ced_link'] = ced_link
        data['fits_skymap_link'] = fits_skymap_link

        if needToClose:
            datafile.close()

        self.data = data
        return data

    def writeCoincFile(self, path):
        pass


def populateGrbEventFromVOEventFile(filename, event):

    # Load file into vp.Voevent instance
    with open(filename, 'rb') as f:
        v = vp.load(f)

    # Get gpstime
    utc_time = vp.convenience.get_event_time_as_utc(v)
    gpstime = utc_datetime_to_gps_float(utc_time)

    # Get event position
    pos2d = vp.get_event_position(v)

    # Assign information to event
    event.gpstime = gpstime
    event.ivorn = v.get('ivorn')
    event.author_shortname = v.Who.Author.shortName.text
    event.author_ivorn = v.Who.AuthorIVORN.text
    event.observatory_location_id = \
        v.WhereWhen.ObsDataLocation.ObservatoryLocation.get('id')
    event.coord_system = pos2d.system
    event.ra = pos2d.ra
    event.dec = pos2d.dec
    event.error_radius = pos2d.err
    event.how_description = v.How.Description.text
    event.how_reference_url = v.How.Reference.get('uri')

    # Try to find a trigger_duration value
    # Fermi uses Trig_Dur or Data_Integ, while Swift uses Integ_Time
    # One or the other may be present, but not both
    VOEvent_params = vp.convenience.get_toplevel_params(v)
    trig_dur_params = ["Trig_Dur", "Trans_Duration", "Data_Integ", 
                       "Integ_Time", "Trig_Timescale"]
    trigger_duration = None
    for param in trig_dur_params:
        if (param in VOEvent_params):
            trigger_duration = float(VOEvent_params.get(param).get('value'))
            break

    # Fermi GCNs (after the first one) often set Trig_Dur or Data_Integ
    # to 0.000 (not sure why). We don't want to overwrite the currently
    # existing value in the database with 0.000 if this has happened, so
    # we only update the value if trigger_duration is non-zero.
    if trigger_duration:
        event.trigger_duration = trigger_duration

    # try to find a trigger_id value
    trigger_id = None
    trigger_id_params = ['TrigID', 'Trans_Num', 'EventID']
    for param in trigger_id_params:
        if (param in VOEvent_params):
            trigger_id = VOEvent_params.get(param).get('value')
            break
    event.trigger_id = trigger_id

    # Check for the existance of FAR in the VOEvent_params. if it exists,
    # Then add it to the event. This change was made on 2/7/2020 in support
    # of SWIFT event uploads. Note: FAR is in Hz.

    if ('FAR' in VOEvent_params):
        event.far = float(VOEvent_params.get('FAR').get('value'))

    # Save event
    event.save()
