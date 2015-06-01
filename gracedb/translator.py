
import os

from .models import EventLog
from .models import SingleInspiral

from glue.ligolw.utils import load_filename
from glue.ligolw.lsctables import CoincInspiralTable, SnglInspiralTable, use_in
from glue.ligolw.lsctables import SimInspiralTable, MultiBurstTable, CoincTable
from glue.ligolw.ligolw import LIGOLWContentHandler

from gracedb.serialize import populate_inspiral_tables, \
                               populate_omega_tables,    \
                               write_output_files

from VOEventLib.Vutil import parse, getWhereWhen, findParam
from utils import isoToGps, isoToGpsFloat
from utils.vfile import VersionedFile

import json

use_in(LIGOLWContentHandler)

# This function checks for 'inf' in a float field, asks the database
# what's the maximum value it can accept for that field, and returns
# that value. Since the database query will introduce some overhead,
# I'm not going to use this to check all fields.

from django.db import connection
def cleanData(val, field_name, table_name='gracedb_event'):
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
    elif isinstance(val, basestring):
        raise ValueError("Unrecognized string in the %s column" % field_name)
    else:
        raise ValueError("Unrecognized value in column %s" % field_name)

def handle_uploaded_data(event, datafilename,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml'):

    log = EventLog(event=event,
                   filename=os.path.basename(datafilename),
                   issuer=event.submitter,
                   comment="Original Data")
    log.save()

    # XXX If you can manage to get rid of the MBTA .gwf parsing and
    # the Omega event parsing, you can deprecate temp_data_loc. It 
    # has already been removed from the alerts.
    temp_data_loc = ""
    warnings = []

    pipeline = event.pipeline.name

    if pipeline in [ 'gstlal', 'gstlal-spiir' ] or (pipeline=='MBTAOnline' and '.xml' in datafilename):
        log_comment = "Log File Created"
        # Wildly speculative wrt HM

        try:
            xmldoc = load_filename(datafilename, contenthandler = LIGOLWContentHandler)
        except Exception, e:
            message = "Could not read data (%s)" % str(e)
            EventLog(event=event, issuer=event.submitter, comment=message).save()
            return

        # Try reading the CoincInspiralTable
        try:
            coinc_table = CoincInspiralTable.get_table(xmldoc)[0]
        except Exception, e:
            warnings += "Could not extract coinc inspiral table."
            return temp_data_loc, warnings

        # Create Log Data
        try:
            log_data = ["Pipeline: %s" % pipeline]
            if event.search:
                log_data.append("Search: %s" % event.search.name)

            mchirp   = coinc_table.mchirp
            mass     = coinc_table.mass
            end_time = (coinc_table.end_time, coinc_table.end_time_ns)
            snr      = coinc_table.snr
            ifos     = coinc_table.ifos
            far      = coinc_table.combined_far

            if mchirp is not None:
                log_data.append("MChirp: %0.3f" % mchirp)
            else:
                log_data.append("MChirp: ---")
            log_data.append("MTot: %s" % mass)
            log_data.append("End Time: %d.%d" % end_time)
            if snr is not None:
                log_data.append("SNR: %0.3f" % snr)
            else:
                log_data.append("SNR: ---")
            log_data.append("IFOs: %s" % ifos)
            if far is not None:
                log_data.append("FAR: %0.3e" % far)
            else:
                log_data.append("FAR: ---")
        except Exception, e:
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
                       issuer=event.submitter,
                       comment=log_comment)
        log.save()

        log = EventLog(event=event,
                       filename=coinc_table_filename,
                       issuer=event.submitter,
                       comment="Coinc Table Created")
        log.save()

        # Extract relevant data from xmldoc to put into event record.
        event.gpstime = coinc_table.end_time + float(coinc_table.end_time_ns)/1.e9
        event.far = coinc_table.combined_far
        # Try to get the coinc_event_table
        try:
            coinc_event_table = CoincTable.get_table(xmldoc)[0]
        except Exception, e:
            warnings += "Could not extract coinc event table."
            return temp_data_loc, warnings
        event.instruments = coinc_event_table.instruments
        event.nevents = coinc_event_table.nevents
        event.likelihood = cleanData(coinc_event_table.likelihood,'likelihood')

        event.ifos             = ifos
        event.end_time         = end_time[0]
        event.end_time_ns      = end_time[1]
        event.mass             = mass
        event.mchirp           = mchirp
        event.minimum_duration = getattr(coinc_table, "minimum_duration", None)
        event.snr              = snr
        event.false_alarm_rate = getattr(coinc_table, "false_alarm_rate", None)
        event.combined_far     = far

        # XXX xml_filename unused
        #xml_filename = os.path.join(output_dir, coinc_table_filename)
        event.save()

        # Extract Single Inspiral Information
        s_inspiral_table = SnglInspiralTable.get_table(xmldoc)
        # If this is a replacement, we might already have single inspiral tables
        # associated. So we should re-create them.
        event.singleinspiral_set.all().delete()
        SingleInspiral.create_events_from_ligolw_table(s_inspiral_table, event)

    elif pipeline == 'HardwareInjection':
        log_comment = "Log File Created"
        xmldoc = load_filename(datafilename, contenthandler=LIGOLWContentHandler)

        # Create Log Data
        # XXX This is messy and redundant.  All of this is also below.
        try:
            log_data = ["Pipeline: %s" % pipeline]
            origdata = SimInspiralTable.get_table(xmldoc)
            origdata = origdata[0]
            mchirp   = origdata.mchirp
            mass     = (origdata.mass1, origdata.mass2)
            spin1    = (origdata.spin1x, origdata.spin1y, origdata.spin1z)
            spin2    = (origdata.spin2x, origdata.spin2y, origdata.spin2z)
            end_time = (origdata.geocent_end_time, origdata.geocent_end_time_ns)
            # XXX unused
            #waveform = origdata.waveform

            if mchirp is not None:
                log_data.append("MChirp: %0.3f" % mchirp)
            else:
                log_data.append("MChirp: ---")
            log_data.append("Component Masses: %f %f" % mass)
            log_data.append("Component 1 Spin: (%f, %f, %f)" % spin1)
            log_data.append("Component 2 Spin: (%f, %f, %f)" % spin2)
            log_data.append("Geocentric End Time: %d.%d" % end_time)
        except Exception, e:
            log_comment = "Problem Creating Log File"
            log_data = ["Cannot create log file", "error was:", str(e)]

        log_data = "\n".join(log_data)

        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data,
                           xml_fname=coinc_table_filename,
                           log_fname=log_filename)

        # Create EventLog entries about these files.

        #event.gpstime = end_time[0]
        event.gpstime = end_time[0] + float(end_time[1])/1e9
        event.save()

        log = EventLog(event=event,
                       filename=log_filename,
                       issuer=event.submitter,
                       comment=log_comment)
        log.save()
    # XXX Submitting MBTA events by frame file is now deprecated as of 19 Dec. 2014.
    # Feel free to break this after 19 Dec. 2015.
    elif pipeline == 'MBTAOnline' and '.gwf' in datafilename:
        warnings += ['Submitting MBTA events via frame file is deprecated. Please use coinc.xml file instead.']
        #here's how it works for inspirals
        #populate the tables
        #xmldoc, log_data, temp_data_loc = populate_inspiral_tables("MbtaFake-930909680-16.gwf") 
        #write the output
        #write_output_files('.', xmldoc, log_data)

        xmldoc, log_data, temp_data_loc = \
                populate_inspiral_tables(datafilename)

        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data,
                           xml_fname=coinc_table_filename,
                           log_fname=log_filename)

        # Create EventLog entries about these files.
        log = EventLog(event=event,
                       filename=log_filename,
                       issuer=event.submitter,
                       comment="Log File Created" )
        log.save()

        log = EventLog(event=event,
                       filename=coinc_table_filename,
                       issuer=event.submitter,
                       comment="Coinc Table Created")
        log.save()

        # Extract relevant data from xmldoc.
        coinc_table = CoincInspiralTable.get_table(xmldoc)
        coinc_table = coinc_table[0]
        #event.gpstime = coinc_table.end_time
        event.gpstime = coinc_table.end_time + float(coinc_table.end_time_ns)/1e9
        # Per Patrick 02FEB12.  All MBTA events with null far should have zero far.
        event.far = coinc_table.combined_far or 0

        event.instruments = coinc_table.instruments
        event.nevents = coinc_table.nevents
        event.likelihood = cleanData(coinc_table.likelihood,'likelihood')

        # extended attributes
        event.ifos             = coinc_table.ifos
        event.end_time         = coinc_table.end_time
        event.end_time_ns      = coinc_table.end_time_ns
        event.mass             = coinc_table.mass
        event.mchirp           = coinc_table.mchirp
        #event.minimum_duration = coinc_table.minimum_duration
        event.snr              = coinc_table.snr
        event.false_alarm_rate = coinc_table.false_alarm_rate
        event.combined_far     = coinc_table.combined_far

        event.save()

        # Extract Single Inspiral Information
        s_inspiral_table = SnglInspiralTable.get_table(xmldoc)

        SingleInspiral.create_events_from_ligolw_table(s_inspiral_table, event)

    elif pipeline == 'Omega':
        #here's how it works for bursts
        #xmldoc, log_data, temp_data_loc = populate_burst_tables("initial.data")
        #write_output_files('.', final_xmldoc, log_data)

        xmldoc, log_data, temp_data_loc = populate_omega_tables(datafilename)
        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data)

        # Create EventLog entries about these files.
        log = EventLog(event=event,
                       filename=log_filename,
                       issuer=event.submitter,
                       comment="Log File Created" )
        log.save()

        log = EventLog(event=event,
                       filename=coinc_table_filename,
                       issuer=event.submitter,
                       comment="Coinc Table Created")
        log.save()

        # Extract relevant data from xmldoc.
        mb_table = MultiBurstTable.get_table(xmldoc)
        mb_table = mb_table[0]
        event.gpstime = mb_table.start_time

        coinc_table = CoincTable.get_table(xmldoc)
        coinc_table = coinc_table[0]
        event.instruments = coinc_table.instruments
        event.nevents = coinc_table.nevents
        event.likelihood = cleanData(coinc_table.likelihood, 'likelihood')

        # XXX xml_filename unused.
        #xml_filename = os.path.join(output_dir, coinc_table_filename)

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
                           issuer=event.submitter,
                           comment="Coinc Table Created")
            log.save()

        if data.writeLogfile( os.path.join(outputDataDir, "event.log") ):
            log = EventLog(event=event,
                           filename="event.log",
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

    elif pipeline in ['Swift', 'Fermi', 'SNEWS']:
        # Get the event time from the VOEvent file
        error = None
        try:
            #event.gpstime = getGpsFromVOEvent(datafilename)
            populateGrbEventFromVOEventFile(datafilename, event)
        except Exception, e:
            error = "Problem parsing VOEvent: %s" % e.__repr__()
        event.save()
        if error is not None:
            log = EventLog(event=event,
                           issuer=event.submitter,
                           comment=error)
            log.save()
    elif pipeline == 'LIB':
        event_file = open(datafilename, 'r')
        event_file_contents = event_file.read()
        event_file.close()
        event_dict = json.loads(event_file_contents)

        # Extract relevant data from dictionary to put into event record.
        event.gpstime     = event_dict['gpstime']
        event.far         = event_dict['FAR']
        event.instruments = event_dict['instruments']
        event.nevents     = event_dict.get('nevents', 1)
        event.likelihood  = event_dict.get('likelihood', None)
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
        # convert ints to ints
        # No longer casting gpstime to integer.
        #for key in ['gpstime', 'likelihood']:
        for key in ['likelihood']:
            if data[key]:
                data[key] = int(float(data[key]))

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

    def writeLogfile(self, path):
        data = self.logData()
        if data:
            f = VersionedFile(path, 'w')
            f.write(data)
            f.close()
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
        event.ifo           = data.get('ifo')
        event.start_time    = data.get('start_time')
        event.start_time_ns = data.get('start_time_ns')
        event.duration      = data.get('duration')
        event.central_freq  = data.get('central_freq')
        event.bandwidth     = data.get('bandwidth')
        event.snr           = data.get('snr')
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

        data = {}
        data['rawdata'] = rawdata
        data['gpstime']    = rawdata.get('time',[None])[0]
        data['likelihood'] = rawdata.get('likelihood',[None])[0]
        data['far']        = rawdata.get('far',[None])[0]

        ifos = rawdata.get('ifo',[])
        ifos.sort()
        data['instruments'] = ','.join(ifos)

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
        data['duration']      = rawdata.get('duration',[None])[0]
        data['central_freq']  = rawdata.get('frequency',[None])[0]
        data['bandwidth']     = rawdata.get('bandwidth',[None])[0]
        #data['snr']           = rawdata.get('snr',[None])[0]
        # rho is what log file says is "effective snr"
        data['snr']           = data['rawdata'].get('rho',[None])[0]
        data['ligo_axis_ra']     = data['rawdata'].get('phi',[None,None,None])[2]
        data['ligo_axis_dec']    = data['rawdata'].get('theta',[None,None,None])[2]

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

def getGpsFromVOEvent(filename):
    v = parse(filename)
    wwd = getWhereWhen(v)
    gpstime = isoToGps(wwd['time'])
    return gpstime

def populateGrbEventFromVOEventFile(filename, event):
    v = parse(filename)
    wherewhen = getWhereWhen(v)

    event.gpstime = isoToGpsFloat(wherewhen['time'])
    event.ivorn = v.ivorn

    event.author_shortname = v.get_Who().Author.shortName[0]
    event.author_ivorn = v.get_Who().AuthorIVORN

    event.observatory_location_id = wherewhen['observatory']
    event.coord_system = wherewhen['coord_system']
    event.ra = wherewhen['longitude']
    event.dec = wherewhen['latitude']
    event.error_radius = wherewhen['positionalError']

    event.how_description = v.get_How().get_Description()[0]  
    event.how_reference_url = v.get_How().get_Reference()[0].uri

    # try to find a trigger_duration value
    # Fermi uses Trig_Dur, while Swift uses Integ_Time
    # One or the other may be present, but not both
    trigger_duration = None
    try:
        trigger_duration = findParam(v, '', 'Trig_Dur').get_value()
    except:
        pass
    try:
        trigger_duration = findParam(v, '', 'Integ_Time').get_value()
    except:
        pass
    event.trigger_duration = trigger_duration
