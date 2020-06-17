from ligo.lw.ligolw import LIGOLWContentHandler
from ligo.lw.lsctables import TableByName
from ligo.lw import table as ligolw_table

import logging

# Set up logger
logger = logging.getLogger(__name__)

class FlexibleLIGOLWContentHandler(LIGOLWContentHandler, object):
    """
    LIGO LW content handler that can parse either the "old" (meaning
    pre ilwd:char--> int_8s conversion), or the "new" format. On detecting
    a depreciated format, the old definitions are added to the validcolumns
    definition for each table.

    This is a bridge to get GraceDB to accept old and new events until everyone
    converts to something else.

    The "diffs" dictionary is hard-wired so i don't have to import glue, but it can
    be regenerated with:

    ----------------------
    from glue.ligolw.lsctables import TableByName as GlueTableByName
    from ligo.lw.lsctables import  TableByName

    # Define table names:
    table_names = ['process',
     'summ_value',
     'sim_ringdown',
     'coinc_definer',
     'coinc_event',
     'coinc_ringdown',
     'time_slide',
     'coinc_event_map',
     'coinc_inspiral',
     'segment_definer',
     'sngl_ringdown',
     'process_params',
     'sim_burst',
     'segment',
     'segment_summary',
     'search_summary',
     'veto_definer',
     'sngl_inspiral',
     'sngl_burst',
     'search_summvars',
     'sim_inspiral']

    # Loop over table names to get validcolumns for each table.

    table_diffs = {}

    for lsc_table in table_names:
        glue_vc = GlueTableByName[lsc_table].validcolumns
        lw_vc = TableByName[lsc_table].validcolumns

        for k in glue_vc.keys():
           if k in lw_vc.keys():
               if glue_vc[k] != lw_vc[k]:
                   column_name_diffs[lsc_table][k] = glue_vc[k]


    print(table_diffs)
    """


    def __init__(self, document, start_handlers = {}):
        super(FlexibleLIGOLWContentHandler, self).__init__(document)

        # Initiate some variables:
        self.current_table = None
        self.depth = 0

        # Restricting conversion between ilwd:char <--> int_8s
        self.allowedTypes = ("ilwd:char", "int_8s")

        # Dictionary of changed column names, per table, with the old
        # types. Explicitly defining this so columns can't be changed
        # arbitrarily. On a table-wise basis, they should adhere to the
        # ligolw spec:

        self.table_diffs = {
           "segment_definer": {
             "process_id": "ilwd:char",
             "segment_def_id": "ilwd:char"
           },
           "coinc_inspiral": {
             "coinc_event_id": "ilwd:char"
           },
           "search_summary": {
             "process_id": "ilwd:char"
           },
           "veto_definer": {
             "process_id": "ilwd:char"
           },
           "segment": {
             "segment_def_id": "ilwd:char",
             "process_id": "ilwd:char",
             "segment_id": "ilwd:char"
           },
           "sim_inspiral": {
             "simulation_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "time_slide": {
             "time_slide_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "summ_value": {
             "summ_value_id": "ilwd:char",
             "segment_def_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "segment_summary": {
             "segment_def_id": "ilwd:char",
             "process_id": "ilwd:char",
             "segment_sum_id": "ilwd:char"
           },
           "process": {
             "process_id": "ilwd:char"
           },
           "sim_ringdown": {
             "simulation_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "sim_burst": {
             "time_slide_id": "ilwd:char",
             "process_id": "ilwd:char",
             "simulation_id": "ilwd:char"
           },
           "coinc_definer": {
             "coinc_def_id": "ilwd:char"
           },
           "coinc_ringdown": {
             "coinc_event_id": "ilwd:char"
           },
           "sngl_inspiral": {
             "event_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "sngl_burst": {
             "event_id": "ilwd:char",
             "process_id": "ilwd:char",
             "filter_id": "ilwd:char"
           },
           "coinc_event": {
             "time_slide_id": "ilwd:char",
             "process_id": "ilwd:char",
             "coinc_def_id": "ilwd:char",
             "coinc_event_id": "ilwd:char"
           },
           "process_params": {
             "process_id": "ilwd:char"
           },
           "search_summvars": {
             "search_summvar_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "sngl_ringdown": {
             "event_id": "ilwd:char",
             "process_id": "ilwd:char"
           },
           "coinc_event_map": {
             "event_id": "ilwd:char",
             "coinc_event_id": "ilwd:char"
           },
           "postcoh": {
             "process_id": "ilwd:char",
             "event_id": "ilwd:char"
           }
         }

    def conversionDict(self,table_name,data_type):
        # Only return conversion dictionary if it is in the allowed types:
        if data_type in self.allowedTypes:
            rd = {k : data_type for k in self.table_diffs[table_name].keys()}
        else:
            raise Exception('Data Type %s is not allowed for this column' % data_type)
        return rd


    def checkAndFilterAttrs(self, attrs):

        if ((None,'Name') in attrs.keys() and (None,'Type') in attrs.keys()):
            # First get the column name as it appears in the validcolumns dict. Note:
            # some styles of ligolw xml may have the column name listed in the
            # Name="table:column" format, so the ColumnName method strips away what is
            # not necessary for the validcolumn lookup.

            col_name = ligolw_table.Column.ColumnName(attrs.getValue((None,'Name')))

            # Next get the data type corresponding to that column in the current tab:

            val_name = attrs.getValue((None,'Type'))

            # I previously defined (by hard-wiring, yolo) a dictionary with the
            # changed data type and corresponding column names (self.table_diffs).
            # Note this dict contains the *old* column names and data types. So, if
            # the current column name appears in the dict of changed values for the
            # current table, then compare the data type. If not, then no conversion
            # is necessary YET for this table, so move on.

            if col_name in self.table_diffs[self.current_table.tableName].keys():

                # If the data type of the current column is not currently part
                # of the validcolumns, then the valid columns need converting,
                # one way or the other (old-> new, new-> old). If we've gotten
                # past the last conditional, then the column is one that could
                # need converting, and the conversionDict routine handles the
                # allowedTypes.

                if val_name != self.current_table.validcolumns.get(col_name):

                    # Update the validcolumns with the new conversion dict.
                    self.current_table.validcolumns.update(self.conversionDict(
                                         self.current_table.tableName, val_name))
        return

    # Get the current table while parsing the xml document:
    def getCurrentTableName(self, attrs):
        if 'Name' in attrs.getQNames():
            try:
                qname, element = attrs.getValueByQName('Name').split(':')
            except Exception as e:
                raise type(e)('Problem parsing attribute qname("Name")')

            if element == 'table':
                # Adding in Error trap for unknown table names that aren't part
                # of the lsctables spec. I'm looking at you spiir/postcoh...
                try:
                    self.current_table = TableByName[qname]
                except:
                    self.current_table = None
            else:
                raise Exception('Problem determining table name')
        return


    def startElementNS(self, uri_localname, qname, attrs):
        (uri, localname) = uri_localname

        # As the contenthandler is iterating through the file, get
        # the name of the current table. Return it as an object.

        if localname == 'Table':
            self.getCurrentTableName(attrs)

        # If the local table has been set, and the current item is a
        # Column definition, then verify the that the column name is
        # part of the "old" definition, and if so, then add it and the
        # other old data types for that table to the valid columns. Don't
        # fully convert it, just add support so the file can get read in without
        # the contenthandler barfing.

        if self.current_table and localname == 'Column':
            self.checkAndFilterAttrs(attrs)

        if self.depth == 0:
            super(FlexibleLIGOLWContentHandler, self).startElementNS((uri, localname), qname, attrs)
        else:
            self.depth += 1

    def endElementNS(self, *args):
        if self.depth == 0:
            super(FlexibleLIGOLWContentHandler, self).endElementNS(*args)
        else:
            self.depth -= 1

    def characters(self, content):
        if self.depth == 0:
            super(FlexibleLIGOLWContentHandler, self).characters(content)

