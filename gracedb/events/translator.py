import gzip
import json
import logging
from math import isnan, sqrt
import numbers
import os

from json import JSONDecodeError
from ligo.lw.utils import load_filename, load_fileobj
from ligo.lw.lsctables import CoincInspiralTable, SnglInspiralTable, use_in
from ligo.lw.lsctables import SimInspiralTable, CoincTable
from core.ligolw import GraceDBFlexibleContentHandler
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

# okay?
use_in(GraceDBFlexibleContentHandler)

# A small helper function to unzip gzipped files. normally ligolw would
# handle all this, but since we're selectively parsing certain tables,
# we just unzip the initial upload and then write it as xml. NOTE: this 
# should get uploaded if pipelines adopt any other compression.

def unzip_or_open(filename):
    if filename.endswith('.gz'):
        try:
            # open the file first and read only one byte to test if it's
            # actually zipped. If it fails, then just fall back to a normal
            # open. The user shouldn't be throwing '.gz' files that aren't 
            # zipped, but this is what gracedb would do before, sooo...

            unzipped_file =  gzip.open(filename, 'rb')
            test_bye = unzipped_file.read(1)
            unzipped_file.close()
            return gzip.open(filename, 'rb')
        except OSError as e:
            pass
    return open(filename, 'rb')

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
                         file_version=0,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml',
                         file_contents=None):

    # This is the base file name of the event creation upload:
    base_file_name = ''

    # The log message should be "Original Data" if it's the initial upload
    # (file_version=0), but should reflect that it's an update/replacement 
    # otherwise. 
    if not bool(file_version):
        comment = "Original Data"
    else:
        comment = "Event data replaced by new upload"

    if datafilename:
        # Extract the base filename from the upload:
        base_file_name = os.path.basename(datafilename)
        log = EventLog(event=event,
                       filename=base_file_name,
                       file_version=file_version,
                       issuer=event.submitter,
                       comment=comment)
        log.save()

    # XXX If you can manage to get rid of the MBTA .gwf parsing and
    # the Omega event parsing, you can deprecate temp_data_loc. It 
    # has already been removed from the alerts.
    temp_data_loc = ""
    warnings = []

    pipeline = event.pipeline.name

    if pipeline in [ 'gstlal', 'spiir', 'pycbc', 'PyGRB'] or (pipeline in ['MBTA', 'MBTAOnline'] and '.xml' in datafilename):
        log_comment = "Log File Created"
        # Wildly speculative wrt HM

        try:
            xmldoc = load_filename(datafilename, contenthandler =
                    GraceDBFlexibleContentHandler)
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

        # For some reason, xmldoc.write(..) is failing with  
        # "ElementError: invalid child Table for Document" when trying to
        # write the document read in with the PartialLIGOLWContentHandler.
        # we're trying to rewrite the entire file anyway (for now) and then
        # pass that into write_output_files

        with unzip_or_open(datafilename) as f:
            fullxmldoc = f.read()

        write_output_files(output_dir, fullxmldoc, log_data,
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
                       file_version=int(coinc_table_filename == base_file_name),
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

        # First try loading the event file as json, in the event of a decoding
        # error, then fall back to LIGOLW xml:

        try: 
            typecast = lambda t, v: t(v) if v is not None else v
            n_int = lambda v: typecast(int, v)
            n_float = lambda v: typecast(float, v)

            # Open event file and get data
            event_file = open(datafilename, 'r')
            event_file_contents = event_file.read()
            event_file.close()
            event_dict = json.loads(event_file_contents)

            # Get gpstime and instruments and far:
            event.far = event_dict.get('far', None)
            event.gpstime = event_dict.get('gpstime', None)
            event.instruments = event_dict.get('instruments', None)

            # Set event attributes. Start with float fields: 
            for attr in SimInspiralEvent.INJ_FLOAT_FIELDS:
                setattr(event, attr, n_float(event_dict.get(attr, None)))

            # Now integer fields: 
            for attr in SimInspiralEvent.INJ_INTEGER_FIELDS:
                setattr(event, attr, n_int(event_dict.get(attr, None)))

            # Now character fields:
            for attr in SimInspiralEvent.INJ_CHAR_FIELDS:
                setattr(event, attr, event_dict.get(attr, None))

            # Save the event:
            event.save()

        except JSONDecodeError:
            # If that didn't work, revert to the old ligolw method. If that
            # fails, then it will return the same errors as before:

            if datafilename:
                xmldoc = load_filename(datafilename, contenthandler=FlexibleLIGOLWContentHandler)
            elif file_contents:
                f = StringIO(file_contents)
                xmldoc, digest = load_fileobj(f, contenthandler=FlexibleLIGOLWContentHandler)
            else:
                msg = "If you wanna make an injection event, "\
                      "I'm gonna need a filepath or filecontents."
                raise ValueError(msg)
    
            origdata = SimInspiralTable.get_table(xmldoc)
            origdata = origdata[0]
            end_time = (origdata.geocent_end_time, origdata.geocent_end_time_ns)
            event.gpstime = end_time[0] + float(end_time[1])/1e9
    
            # Assign attributes from the SimInspiralTable
            field_names = SimInspiralEvent.field_names()
            for column in field_names:
                try:
                    value = getattr(origdata, column)
                    setattr(event, column, value)
                except:
                    pass
            event.save()

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

    elif pipeline in ['Swift', 'Fermi', 'SNEWS', 'INTEGRAL',
                      'AGILE', 'CHIME', 'SVOM']:
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

    elif pipeline in ['MLy', 'aframe']:
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
        event.central_freq  		= n_float(event_dict.get('central_freq', None))
        event.central_time  		= n_float(event_dict.get('central_time', None))
        event.bandwidth     		= n_float(event_dict.get('bandwidth', None))
        event.duration      		= n_float(event_dict.get('duration', None))
        event.snr           		= n_float(event_dict.get('SNR', None))
        event.detection_statistic	= n_float(event_dict.get('detection_statistic', None))

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
        event.ifos              = data.get('ifo')
        event.start_time        = data.get('start_time')
        event.start_time_ns     = data.get('start_time_ns')
        event.peak_time         = data.get('peak_time')
        event.peak_time_ns      = data.get('peak_time_ns')
        event.duration          = data.get('duration')
        event.strain            = data.get('strain')
        event.central_freq      = data.get('central_freq')
        event.bandwidth         = data.get('bandwidth')
        event.amplitude         = data.get('snr')
        # ---------------------------------------------------------
        # Note that 'snr' here corresponds to 'rho' in the datafile
        # ---------------------------------------------------------
        event.mchirp            = data.get('mchirp')
        # ---------------------------------------------------------
        # The SNR to use is provided by the likelihood
        # https://dcc.ligo.org/LIGO-G2301201 (slide 5)
        #   cWB SNR = sqrt(sSNR[0]+sSNR[1])= sqrt(likelihood)
        #   Coherent SNR = sqrt(ecor)
        #   Reduced Coherent SNR - cWB detection statistic rho[0]
        # ----------------------------------------------------------
        try:
            event.snr           = sqrt(data.get('likelihood'))
        except:
            event.snr           = 0.0
        event.confidence        = data.get('confidence')
        event.false_alarm_rate  = data.get('false_alarm_rate')
        event.ligo_axis_ra      = data.get('ligo_axis_ra')
        event.ligo_axis_dec     = data.get('ligo_axis_dec')
        event.ligo_angle        = data.get('ligo_angle')
        event.ligo_angle_sig    = data.get('ligo_angle_sig')
        # Single IFO times are cast as a comma-separated string,
        # in same order as the 'ifos' field.
        event.single_ifo_times = data.get('single_ifo_times')
        event.hoft             = data.get('hoft',"")
        event.code             = data.get('code',"")

    def readData(self, datafile):
        needToClose = False
        if isinstance(datafile, str) or isinstance(datafile, unicode):
            datafile = open(datafile, "r")
            filelines = datafile.readlines()
            datafile.close()
        else:
            datafile.seek(0)
            filelines = datafile.readlines()
            datafile.seek(0)

        # cWB data look like
        #
        # key0: value value*
        # ...
        # keyN: value value*
        #
        # ---- They also include "event_time", "far" and "hoft"
        #
        # piles of other data not containing ':'
        # ...
        #  more data we don't care about here
        # ...
        # #significance based on the last 24*6 processed jobs, 4000-1 time shifts
        # 318 1.98515e-05 1026099328 1026503796 53644
        # ...
        #

        rawdata = {}

        # Get Key/Value info
        for line in filelines:
            line = line.split(':',1)
            if len(line) == 1:
                continue
            key, val = line
            key = key.split()[0]
            rawdata[key] = val.split()

        # On May 20th 2023 not all the data to be ingested are in the
        # data section.
        # Here is the failover fields that alow teh injestion of
        # old events that do include the "event_time", "far"
        # fields that are in the keys : values section

        if (rawdata.get('event_time',None) == None or
            rawdata.get('far',None) == None ):

            rawdata['mchirp']     = [rawdata.get('chirp',[0.0,0.0])[1]]
            rawdata['event_time'] = [rawdata.get('time',[0.0])[0]]
            rawdata['fits_skymap_link'] = [None]
            rawdata['ced_link'] = [None]

            for line in filelines:
                if line.startswith("http"):
                    if line.find(".fits") > 0:
                        rawdata['fits_skymap_link'] = [line]
                    else:
                        rawdata['ced_link'] = [line]

            # scan down for FAR
            rawdata['far'] = [0.0]
            rawdata['far_day'] = [0.0]
            for idx,line in enumerate(filelines):
                # Change for Marco Drago, 11/20/14 and Roberto 17/05/23
                if line.startswith("#significance based on the last week"):
                    try:
                        nextline=filelines[idx+1]
                        rawdata['far'] = [float(nextline.split()[1])]
                    except:
                        rawdata['far'] = [1.0]
                if line.startswith("#significance based on the last day"):
                    try:
                        nextline=filelines[idx+1]
                        rawdata['far_day'] = [float(nextline.split()[1])]
                    except:
                        rawdata['far_day'] = [1.0]
            # very old event have just 'far_day'
            if rawdata['far'][0] == 0 and rawdata['far_day'][0] > 0:
                rawdata['far'] = rawdata['far_day']

        # End of failover code

        # lambda function for converting to a type if not None
        typecast = lambda t, v: t(v) if v is not None else v
        n_int = lambda v: typecast(int, v)
        n_float = lambda v: typecast(float, v)

        # Fix import data as derived from rawdata 
        data = {}
        data['rawdata']    = rawdata
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
        start_time =  rawdata.get('start',[None])[0]
        peak_time  =  rawdata.get('time',[None])[0]
        if start_time is not None:
            integer, frac = start_time.split('.')
            data['start_time']    = int(integer)
            data['start_time_ns'] = int(frac+(9-len(frac))*'0')
        else:
            data['start_time']    = None
            data['start_time_ns'] = None
        if peak_time is not None:
            integer, frac = peak_time.split('.')
            data['peak_time']    = int(integer)
            data['peak_time_ns'] = int(frac+(9-len(frac))*'0')
        else:
            data['peak_time']    = None
            data['peak_time_ns'] = None

        data['ifo'] = ','.join(ifos)
        data['duration']      = n_float(rawdata.get('duration',[None])[0])
        data['strain']        = n_float(rawdata.get('strain',[None])[0])
        data['central_freq']  = n_float(rawdata.get('frequency',[None])[0])
        data['bandwidth']     = n_float(rawdata.get('bandwidth',[None])[0])
        data['mchirp']        = n_float(rawdata.get('mchirp',[None])[0])
        #data['snr']           = rawdata.get('snr',[None])[0]
        # rho is what log file says is "effective snr"
        data['confidence']       = None
        data['snr']              = n_float(data['rawdata'].get('rho',[None])[0])
        data['false_alarm_rate'] = n_float(rawdata.get('far',[None])[0])
        data['ligo_axis_ra']   = n_float(data['rawdata'].get('phi',[None,None,None])[2])
        data['ligo_axis_dec']  = n_float(data['rawdata'].get('theta',[None,None,None])[2])
        data['ligo_angle']     = None
        data['ligo_angle_sig'] = None
        data['hoft'] = data['rawdata'].get('hoft',[""])[0]
        data['code'] = data['rawdata'].get('code',[""])[0]

        data['gpstime']    = n_float(rawdata.get('event_time',[None])[0])

        data['ced_link']         = rawdata.get('ced_link',[None])[0]
        data['fits_skymap_link'] = rawdata.get('fits_skymap_link',[None])[0]

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
    # Also grab parameters from embedded group if there, needed for SVOM
    Svom_ident = vp.convenience.get_grouped_params(v).get('Svom_Identifiers')
    Svom_detect = vp.convenience.get_grouped_params(v).get('Detection_Info')
    if Svom_ident is not None:
        VOEvent_params.update(Svom_ident)
    if Svom_detect is not None:
        VOEvent_params.update(Svom_detect)

    trig_dur_params = ["Trig_Dur", "Trans_Duration", "Data_Integ", 
                       "Integ_Time", "Trig_Timescale", "Timescale"]
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
    trigger_id_params = ['TrigID', 'Trans_Num', 'EventID',
                         'Burst_Id']
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
