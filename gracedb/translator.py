
import os, sys

from models import EventLog
from subprocess import Popen, PIPE

from django.conf import settings

import glue, glue.ligolw.utils
from glue.gracedb.utils import InspiralCoincDef
from glue.gracedb.utils import BurstCoincDef

from glue.gracedb.utils import insp_event_id_dict
from glue.gracedb.utils import coherent_event_id_dict

from glue.gracedb.utils import populate_inspiral_tables, \
                               populate_omega_tables,    \
                               populate_coinc_tables,    \
                               write_output_files

# Importing this messes with other ligolw table actions.
#from gracedb.ligolw.insert import insert_ligolw_tables
import gracedb.ligolw

def insert_ligolw_tables(xml_filename):
    #insert_ligolw_tables(django.db.connection, xml_filename)
    prog = os.path.dirname(gracedb.ligolw.__file__)
    prog = os.path.join(prog, "insert.py")
    e = dict(os.environ)
    ppath = e.get("PYTHONPATH") or ""
    ppath = ppath.split(':')
    ppath = ppath + sys.path
    e['PYTHONPATH'] = ':'.join(ppath)
    p = Popen( (prog,
                 settings.DATABASE_USER,
                 settings.DATABASE_PASSWORD,
                 settings.DATABASE_NAME,
                 xml_filename),
               stdout=PIPE, stderr=PIPE, env=e)
    out = p.stdout.read()
    err = p.stderr.read()
    p.wait()
    out += p.stdout.read()
    if out.find("OK") != 0:
        coinc_id = None
    else:
        coinc_id = out[2:].strip()
    return coinc_id

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
        private_data_url = os.path.join(event.weburl(), 'private')

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

        xml_filename = os.path.join(output_dir, coinc_table_filename)
        event.coincEvent_id = insert_ligolw_tables(xml_filename)

        event.save()

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
        private_data_url = os.path.join(event.weburl(), 'private')

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

        xml_filename = os.path.join(output_dir, coinc_table_filename)
        event.coincEvent_id = insert_ligolw_tables(xml_filename)

        event.save()

    elif event.analysisType == 'OM': # Omega
        #here's how it works for bursts
        #xmldoc, log_data, temp_data_loc = populate_burst_tables("initial.data")
        #write_output_files('.', final_xmldoc, log_data)

        xmldoc, log_data, temp_data_loc = populate_omega_tables(datafilename)
        output_dir = os.path.dirname(datafilename)
        write_output_files(output_dir, xmldoc, log_data)

        # Create EventLog entries about these files.
        private_data_url = os.path.join(event.weburl(), 'private')

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

        xml_filename = os.path.join(output_dir, coinc_table_filename)
        event.coincEvent_id = insert_ligolw_tables(xml_filename)

        event.save()
    elif event.analysisType == 'CWB':
        try:
            f = open(datafilename, "r")
            for line in f.readlines():
                if line.startswith("time:"):
                    times = line.split()
                    event.gpstime = int(float(times[1]))
                    event.save()
                    break
            f.close()
        except:
            pass
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
    else:
        # XXX should we do something here?
        pass

    return temp_data_loc
