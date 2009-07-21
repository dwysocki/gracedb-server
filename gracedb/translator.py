
import os

from models import EventLog

import glue
from glue.gracedb.utils import InspiralCoincIdBase, InspiralCoincDef
from glue.gracedb.utils import BurstCoincIdBase, BurstCoincDef

from glue.gracedb.utils import insp_event_id_dict
from glue.gracedb.utils import coherent_event_id_dict

from glue.gracedb.utils import populate_inspiral_tables, \
                               populate_burst_tables,    \
                               populate_coinc_tables,    \
                               write_output_files

def handle_uploaded_data(event, datafilename,
                         log_filename='event.log',
                         coinc_table_filename='coinc.xml'):

    if event.analysisType == 'MBTA':
        xmldoc, log_data, detectors = \
                populate_inspiral_tables(datafilename, 0)
                # XXX ligolw wants ints.
                #populate_inspiral_tables(datafilename, #event.graceid())
        xmldoc = populate_coinc_tables(xmldoc,
                                       # XXX ligolw wants ints.
                                       #event.graceid(),
                                       0,
                                       InspiralCoincIdBase,
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
        event.save()

    elif event.analysisType == 'OM': # Omega
        xmldoc, log_data, detectors = populate_burst_tables(datafilename, 0)
        xmldoc = populate_coinc_tables(
                        xmldoc, 0, BurstCoincIdBase, \
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
        event.save()
    else:
        pass
