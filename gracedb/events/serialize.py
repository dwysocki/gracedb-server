#!/usr/bin/python

from math import log
from time import gmtime, strftime

from glue.lal import LIGOTimeGPS
from glue.ligolw import ligolw
from glue.ligolw import table
from glue.ligolw import lsctables

from core.vfile import VersionedFile

##############################################################################
#
#          useful variables
#
##############################################################################

#Need these for each search: inspiral, burst, etc.
InspiralCoincDef = lsctables.CoincDef(search = u"inspiral", \
                                      search_coinc_type = 0, \
                                      description = \
                                      u"sngl_inspiral<-->sngl_inspiral coincidences")
#these should work for both Omega and CWB
BurstCoincDef = lsctables.CoincDef(search = u"burst", \
                                      search_coinc_type = 0, \
                                      description = \
                                      u"coherent burst coincidences")

#list of detectors participating in the coinc
#MBTA only sends triples to gracedb at the time being so this list is
#simply for convenience.  burst and future inspiral searches should
#construct this list on the fly
H1L1V1_detlist = ['H1', 'L1', 'V1']
H1L1_detlist = ['H1', 'L1']
H1V1_detlist = ['H1', 'V1']
L1V1_detlist = ['L1', 'V1']
H1_detlist = ['H1']
L1_detlist = ['L1']
V1_detlist = ['V1']

#this is the subset of SnglInspiralTable.validcolumn.keys() that
#are assigned from MBTA coinc triggers
MBTA_set_keys = ['ifo', 'search', 'end_time', 'end_time_ns', 'mass1', 'mass2',\
               'mchirp', 'mtotal', 'eta', 'snr', 'eff_distance', 'event_id',\
               'process_id', 'channel']
#Omega 
Omega_set_keys = ['process_id', 'ifos', 'start_time', 'start_time_ns',\
                 'duration', 'confidence', 'coinc_event_id']
#CWB
CWB_set_keys = ['process_id', 'ifos', 'start_time', 'start_time_ns',\
                'coinc_event_id']

#this dictionary is the simplest way to assign event_id's
#collisions are are taken care of in the process of conversion to sqlite
insp_event_id_dict = {'H1': 'sngl_inspiral:event_id:0',\
                 'L1': 'sngl_inspiral:event_id:1',\
                 'V1': 'sngl_inspiral:event_id:2'}
#this one is designed for coherent searches, which don't have event_ids
coherent_event_id_dict = None

#the names of the variables we're going to get from omega
omega_vars = ['time', 'frequency', 'duration', 'bandwidth', 'modeTheta',\
              'modePhi', 'probSignal', 'probGlitch', 'logSignal','logGlitch',\
              'network', 'URL_web', 'URL_file']
              
##############################################################################
#
#          convenience functions
#
##############################################################################

def compute_mchirp_eta(m1,m2):
  """
  compute and return mchirp and eta for a given pair of masses 
  """
  
  mtot = m1 + m2
  mu = m1*m2/mtot
  eta = mu/mtot
  mchirp = pow(eta,3.0/5.0)*mtot
  
  return float(mchirp), float(eta)

def write_output_files(root_dir, xmldoc, log_content, \
                       xml_fname = 'coinc.xml', log_fname = 'event.log'):
  """
  write the xml-format coinc tables and log file
  """

  f = VersionedFile(root_dir+'/'+xml_fname,'w')
  xmldoc.write(f.file)
  f.close()

  f = VersionedFile(root_dir+'/'+log_fname,'w')
  f.write(log_content)
  f.close()

def get_ifos_for_cwb(cwb_ifos):
  """
  get human-readable things from CWB detector labels
  """
  
  ifos = []
  for i in cwb_ifos:
    if i == '1':  ifos.append('L1')
    if i == '2' : ifos.append('H1')
    if i == '3' : ifos.append('H2')
    if i == '4' : ifos.append('G1')
    if i == '5' : ifos.append('T1')
    if i == '6' : ifos.append('V1')
    if i == '7' : ifos.append('A1')

  return ifos
  
##############################################################################
#
#          table populators
#
##############################################################################

def populate_omega_tables(datafile, set_keys = Omega_set_keys):
  """
  """
  #initialize xml document
  xmldoc = ligolw.Document()
  xmldoc.appendChild(ligolw.LIGO_LW())
  
  #extract the data from the intial Omega file
  f = open(datafile, 'r')
  omega_list = []
  for line in f.readlines():
    if not line.strip(): continue # ignore blank lines
    elif '#' in line.strip()[0]: continue # ignore comments
    elif '=' not in line: raise ValueError("Improperly formatted line")
    else:
      omega_list.extend([dat.strip() for dat in line.split('=',1)])
  f.close()
  omega_data = dict(zip(omega_list[::2],omega_list[1::2]))  
  # basic error checking
# for key in omega_data:
#   if not (key in omega_vars):
#     raise ValueError("Unknown variable")
    
  #create the content for the event.log file
  log_data = '\nLog File created '\
             +strftime("%a, %d %b %Y %H:%M:%S", gmtime())\
             +'\n'

  for var in omega_vars:
    log_data += var + ': ' + omega_data[var] + '\n'
  
  #pull out the ifos
  detectors = [ifo for ifo in omega_data['network'].split(',')]
  
  #fill the MutliBurstTable
  mb_table = lsctables.New(lsctables.MultiBurstTable)
  xmldoc.childNodes[0].appendChild(mb_table)
  row = mb_table.RowType()
  row.process_id = lsctables.ProcessTable.get_next_id()
  row.set_ifos(detectors)
  st = LIGOTimeGPS(omega_data['time'])
  row.start_time = st.seconds
  row.start_time_ns = st.nanoseconds
  row.duration = None
  row.confidence = -log(float(omega_data['probGlitch']))
  cid = lsctables.CoincTable.get_next_id()
  row.coinc_event_id = cid
  for key in mb_table.validcolumns.keys():
      if key not in set_keys:
        setattr(row,key,None)
  mb_table.append(row)

  xmldoc = populate_coinc_tables(xmldoc,cid, coherent_event_id_dict,\
                                     BurstCoincDef, detectors)
  
  return xmldoc, log_data, omega_data['URL_file']

def populate_cwb_tables(datafile, set_keys=CWB_set_keys):
  """
  """
  #initialize xml document
  xmldoc = ligolw.Document()
  xmldoc.appendChild(ligolw.LIGO_LW())

  #extract the data from the file
  f = open(datafile,'r')
  cwb_list = []
  for line in f.readlines():
    if not line.strip(): continue #ignore blanks
    elif '#' in line.strip()[0]: continue #skip comments
    elif 'H1:' in line.strip() or 'L1:' in line.strip() or 'V1:' in line.strip(): continue #skip DQ stuff
    elif ':' in line.strip(): cwb_list.extend([dat.strip() for dat in line.split(':',1)])

  f.close()
  cwb_data = dict(zip(cwb_list[::2],cwb_list[1::2]))
  
  #create the content for the event.log file
  log_data = '\nLog File created '\
             +strftime("%a, %d %b %Y %H:%M:%S", gmtime())\
             +'\n'
  detectors = get_ifos_for_cwb(cwb_data['ifo'].split())

  for var in cwb_data:
    log_data += var + ': ' + cwb_data[var] + '\n'

  #fill the MutliBurstTable
  mb_table = lsctables.New(lsctables.MultiBurstTable)
  xmldoc.childNodes[0].appendChild(mb_table)
  row = mb_table.RowType()
  row.process_id = lsctables.ProcessTable.get_next_id()
  row.set_ifos(detectors)
  st = LIGOTimeGPS(cwb_data['start'][0])
  row.start_time = st.seconds
  row.start_time_ns = st.nanoseconds
  cid = lsctables.CoincTable.get_next_id()
  row.coinc_event_id = cid
  for key in mb_table.validcolumns.keys():
      if key not in set_keys:
        setattr(row,key,None)
  mb_table.append(row)

  xmldoc = populate_coinc_tables(xmldoc,cid, coherent_event_id_dict,\
                                    BurstCoincDef, detectors)
  
  return xmldoc, log_data, None
  
      
    
def populate_coinc_tables(xmldoc, coinc_event_id, event_id_dict,\
                          CoincDef, detectors, \
                          time_slide_id = None, likelihood = None):
  """
  populate a set of coinc tables
  xmldoc:  xml file to append the tables to
  CoincDef: pre-initialized CoincDef table row
  detectors: detectors participating in the coinc
  """
  #make sure there's actually a coinc there to write
  if len(detectors) < 2:
    return xmldoc
  else:
    #CoincTable
    coinc_table = lsctables.New(lsctables.CoincTable)
    xmldoc.childNodes[0].appendChild(coinc_table)
    row = coinc_table.RowType()
    row.process_id = lsctables.ProcessTable.get_next_id()
    row.coinc_event_id =  coinc_event_id
    coinc_def_id = lsctables.CoincDefTable.get_next_id()
    row.coinc_def_id = coinc_def_id
    row.time_slide_id = time_slide_id
    row.set_instruments(detectors)
    if 'inspiral' in CoincDef.search:
      row.nevents = len(detectors)
    elif 'burst' in CoincDef.search:
      row.nevents = 1
    else:
      raise ValueError("Unrecognize CoincDef.search")
    row.likelihood = likelihood
    coinc_table.append(row)

    #CoincMapTable
    coinc_map_table = lsctables.New(lsctables.CoincMapTable)
    xmldoc.childNodes[0].appendChild(coinc_map_table)
    for ifo in detectors:
      row = coinc_map_table.RowType()
      row.coinc_event_id = coinc_event_id
      if 'inspiral' in CoincDef.search:
        row.table_name = lsctables.SnglInspiralTable.tableName.split(':')[0]
      elif 'burst' in CoincDef.search:
        row.table_name = lsctables.MultiBurstTable.tableName.split(':')[0]
      else:
        raise ValueError("Unrecognize CoincDef.search")
      if event_id_dict:
        row.event_id = event_id_dict[ifo]
        coinc_map_table.append(row)
    if not event_id_dict:
      row.event_id = coinc_event_id
      coinc_map_table.append(row)

    #CoincDefTable
    coinc_def_table = lsctables.New(lsctables.CoincDefTable)
    xmldoc.childNodes[0].appendChild(coinc_def_table)
    row = coinc_def_table.RowType()
    row.coinc_def_id = coinc_def_id
    row.search = CoincDef.search
    row.search_coinc_type = CoincDef.search_coinc_type
    row.description = CoincDef.description
    coinc_def_table.append(row)
    
    return xmldoc 
