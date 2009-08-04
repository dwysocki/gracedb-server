
import os, sys

from models import EventLog
from subprocess import Popen, PIPE

import glue, glue.ligolw.utils
from glue.gracedb.utils import InspiralCoincDef
from glue.gracedb.utils import BurstCoincDef

from glue.gracedb.utils import insp_event_id_dict
from glue.gracedb.utils import coherent_event_id_dict

from glue.gracedb.utils import populate_inspiral_tables, \
                               populate_burst_tables,    \
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
    p = Popen( (prog, "root", "", "gracedb", xml_filename), stdout=PIPE, stderr=PIPE, env=e)
    out = p.stdout.read()
    err = p.stderr.read()
    p.wait()
    out += p.stdout.read()
    if out.find("OK") != 0:
        coinc_id = None
        try:
            f = open('/tmp/foo','a')
            f.write("ERROR (stdin): %s\n" % out)
            f.write("ERROR (stderr): %s\n" % err)
            f.close()
        except: pass
    else:
        coinc_id = out[2:].strip()
    return coinc_id

def handle_uploaded_data(event, datafilename,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml'):

    if event.analysisType == 'HM':
        # Wildly speculative
        xmldoc = glue.ligolw.utils.load_filename(datafilename)
        log_data = "LOG DATA TBD\n"
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

        log = EventLog(event=event,
                       filename=os.path.basename(datafilename),
                       issuer=event.submitter,
                       comment="Original Data")
        log.save()


        # Extract relevant data from xmldoc.
        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincInspiralTable.tableName)
        coinc_table = coinc_table[0]
        event.gpstime = coinc_table[0].end_time

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

    if event.analysisType == 'MBTA':
        #xmldoc, log_data, detectors, cid = populate_inspiral_tables("MbtaFake-930909680-16.gwf")
        #final_xmldoc = populate_coinc_tables(xmldoc,cid,insp_event_id_dict,\
        #                                     InspiralCoincDef,detectors)
        #write the output
        #write_output_files('.', xmldoc, log_data)
        xmldoc, log_data, detectors, cid = \
                populate_inspiral_tables(datafilename)
        xmldoc = populate_coinc_tables(xmldoc,
                                       cid,
                                       insp_event_id_dict,
                                       InspiralCoincDef,
                                       detectors)

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

        log = EventLog(event=event,
                       filename=os.path.basename(datafilename),
                       issuer=event.submitter,
                       comment="Original Data")
        log.save()

        # Extract relevant data from xmldoc.
        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincInspiralTable.tableName)
        coinc_table = coinc_table[0]
        event.gpstime = coinc_table[0].end_time

        coinc_table = glue.ligolw.table.getTablesByName(
                            xmldoc,
                            glue.ligolw.lsctables.CoincTable.tableName)
        coinc_table = coinc_table[0]
        event.instruments = coinc_table[0].instruments
        event.nevents = coinc_table[0].nevents
        event.likelihood = coinc_table[0].likelihood

        xml_filename = os.path.join(output_dir, coinc_table_filename)
        event.coinc_id = insert_ligolw_tables(xml_filename)

        event.save()

    elif event.analysisType == 'OM': # Omega
        #xmldoc, log_data, detectors, cid = populate_burst_tables("initial.data")
        #final_xmldoc = populate_coinc_tables(xmldoc,cid, coherent_event_id_dict,\
        #                                     BurstCoincDef, detectors)
        #write_output_files('.', final_xmldoc, log_data)
        xmldoc, log_data, detectors, cid = populate_burst_tables(datafilename)
        xmldoc = populate_coinc_tables(
                        xmldoc, cid, \
                        coherent_event_id_dict, BurstCoincDef, \
                        detectors)

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

        log = EventLog(event=event,
                       filename=os.path.basename(datafilename),
                       issuer=event.submitter,
                       comment="Original Data")
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
        event.coinc_id = insert_ligolw_tables(xml_filename)

        event.save()
    else:
        pass
