
import os

from models import EventLog

import glue
import glue.ligolw.utils

from ligo.gracedb.utils import populate_inspiral_tables, \
                               populate_omega_tables,    \
                               write_output_files

from VOEventLib.Vutil import parse, getWhereWhen
from utils import isoToGps

def handle_uploaded_data(event, datafilename,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml'):

    log = EventLog(event=event,
                   filename=os.path.basename(datafilename),
                   issuer=event.submitter,
                   comment="Original Data")
    log.save()

    temp_data_loc = ""
    if event.analysisType in [ 'HM', 'LM' ]:
        log_comment = "Log File Created"
        # Wildly speculative wrt HM
        xmldoc = glue.ligolw.utils.load_filename(datafilename)

        # Create Log Data
        # XXX This is messy and redundant.  All of this is also below.
        try:
            log_data = ["Event Type: %s" % event.getTypeLabel(event.analysisType)]
            origdata = glue.ligolw.table.getTablesByName(
                                        xmldoc,
                                        glue.ligolw.lsctables.CoincInspiralTable.tableName)

            mchirp   = origdata[0][0].mchirp
            mass     = origdata[0][0].mass
            end_time = (origdata[0][0].end_time, origdata[0][0].end_time_ns)
            snr      = origdata[0][0].snr
            ifos     = origdata[0][0].ifos
            far      = origdata[0][0].combined_far

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

        # XXX provate_data_url unused
        #private_data_url = os.path.join(event.weburl(), 'private')

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
        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincInspiralTable.tableName)
        coinc_table = coinc_table[0]
        event.gpstime = coinc_table[0].end_time
        event.far = coinc_table[0].combined_far

        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincTable.tableName)
        coinc_table = coinc_table[0]
        event.instruments = coinc_table[0].instruments
        event.nevents = coinc_table[0].nevents
        event.likelihood = coinc_table[0].likelihood

        # XXX xml_filename unused
        #xml_filename = os.path.join(output_dir, coinc_table_filename)

        event.save()

    elif event.analysisType == "HWINJ":
        log_comment = "Log File Created"
        xmldoc = glue.ligolw.utils.load_filename(datafilename)

        # Create Log Data
        # XXX This is messy and redundant.  All of this is also below.
        try:
            log_data = ["Event Type: %s" % event.getTypeLabel(event.analysisType)]
            origdata = glue.ligolw.table.getTablesByName(
                                        xmldoc,
                                        glue.ligolw.lsctables.SimInspiralTable.tableName)

            mchirp   = origdata[0][0].mchirp
            mass     = (origdata[0][0].mass1, origdata[0][0].mass2)
            spin1    = (origdata[0][0].spin1x, origdata[0][0].spin1y, origdata[0][0].spin1z)
            spin2    = (origdata[0][0].spin2x, origdata[0][0].spin2y, origdata[0][0].spin2z)
            end_time = (origdata[0][0].geocent_end_time, origdata[0][0].geocent_end_time_ns)
            # XXX unused
            #waveform = origdata[0][0].waveform

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

        # XXX private_data_url unused
        #private_data_url = os.path.join(event.weburl(), 'private')

        event.gpstime = end_time[0]
        event.save()

        log = EventLog(event=event,
                       filename=log_filename,
                       issuer=event.submitter,
                       comment=log_comment)
        log.save()
    elif event.analysisType == 'MBTA':
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

        # XXX provate_data_url unused
        #private_data_url = os.path.join(event.weburl(), 'private')

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
        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincInspiralTable.tableName)
        coinc_table = coinc_table[0]
        event.gpstime = coinc_table[0].end_time
        # Per Patrick 02FEB12.  All MBTA events with null far should have zero far.
        event.far = coinc_table[0].combined_far or 0

        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincTable.tableName)
        coinc_table = coinc_table[0]
        event.instruments = coinc_table[0].instruments
        event.nevents = coinc_table[0].nevents
        event.likelihood = coinc_table[0].likelihood

        # XXX xml_filename unused
        #xml_filename = os.path.join(output_dir, coinc_table_filename)

        event.save()

    elif event.analysisType == 'OM': # Omega
        #here's how it works for bursts
        #xmldoc, log_data, temp_data_loc = populate_burst_tables("initial.data")
        #write_output_files('.', final_xmldoc, log_data)

        xmldoc, log_data, temp_data_loc = populate_omega_tables(datafilename)
        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data)

        # Create EventLog entries about these files.

        # XXX provate_data_url unused
        #private_data_url = os.path.join(event.weburl(), 'private')

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
        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.MultiBurstTable.tableName)
        coinc_table = coinc_table[0]
        event.gpstime = coinc_table[0].start_time

        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincTable.tableName)
        coinc_table = coinc_table[0]
        event.instruments = coinc_table[0].instruments
        event.nevents = coinc_table[0].nevents
        event.likelihood = coinc_table[0].likelihood

        # XXX xml_filename unused.
        #xml_filename = os.path.join(output_dir, coinc_table_filename)

        event.save()
    elif event.analysisType == 'CWB':

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

    elif event.analysisType == 'HWINJ':
        try:
            f = open(datafilename, "r")
            for line in f.readlines():
                if line.startswith("gpstime:"):
                    times = line.split()
                    event.gpstime = int(float(times[1]))
                    event.save()
                    break
            f.close()
        except:
            pass
    elif event.analysisType == 'GRB':
        # Get the event time from the VOEvent file
        try:
            event.gpstime = getGpsFromVOEvent(datafilename)
        except:
            event.gpstime = 0
        event.save()
    else:
        # XXX should we do something here?
        pass

    return temp_data_loc

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
        for key in ['gpstime', 'likelihood']:
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

        event.save()

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
            f = open(path, 'w')
            f.write(data)
            f.close()
        return True



class CwbData(Translator):
    event_type = "cWB"
    CWB_IFO_MAP = {
        '1' : 'L1',
        '2' : 'H1',
        '3' : 'H2',
        '4' : 'G1',
        '5' : 'T1',
        '6' : 'V1',
        '7' : 'A1',
    }

    def __init__(self, datafile, *args, **kwargs):
        self.datafile = datafile
        self.data = None

    def getData(self):
        if not self.data:
            data = self.readData(self.datafile)
            self.castData(data)
        return self.data

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
        rawdata = {}

        # Get Key/Value info
        for line in datafile:
            line = line.split(':',1)
            if len(line) == 1:
                break
            key, val = line
            rawdata[key] = val.split()

        # scan down for FAR
        next_line_is_far = False
        for line in datafile:
            if line.startswith("#significance based on the last 24*6"):
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

        ifos = []
        for ifo in rawdata.get('ifo',[]):
            ifos.append(self.CWB_IFO_MAP[ifo])
        ifos.sort()
        data['instruments'] = ','.join(ifos)

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
