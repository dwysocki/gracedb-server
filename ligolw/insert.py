#!/usr/bin/env python

#
# preamble
#

import sys, os

import StringIO

import MySQLdb
from MySQLdb import OperationalError

import glue
from glue.ligolw import ligolw
from glue.ligolw import lsctables
# FIXME:  remove the next line when this attribute is initialized properly
# in lsctables.py
lsctables.SnglInspiralTable.next_id = lsctables.SnglInspiralID(0)
# FIXME:  remove the next line when SnglInspiralTable no longer has its own
# custom version of this method
lsctables.SnglInspiralTable.updateKeyMapping = lsctables.table.Table.updateKeyMapping
from glue.ligolw import utils
from glue.ligolw.utils.ligolw_add import reassign_ids as ligolw_reassign_ids
# while importing dbtables, need before and after copies of the
# LIGOLWContentHandler class
class LIGOLWRAMContentHandler(ligolw.LIGOLWContentHandler):
    startTable = ligolw.LIGOLWContentHandler.startTable
    endTable = ligolw.LIGOLWContentHandler.endTable
from glue.ligolw import dbtables
class LIGOLWDBContentHandler(ligolw.LIGOLWContentHandler):
    startTable = ligolw.LIGOLWContentHandler.startTable
    endTable = ligolw.LIGOLWContentHandler.endTable

dbtables.DBTable.maxrowid = lambda self: None

#
# initialize the next_id attributes of all the table classes
#

#------------------------------------------------------------------

#from insert_nextid import next_id
# included below.

import MySQLdb
from MySQLdb.constants import ER

TABLE_NAME = "ligolwids"

create_table_sql = "CREATE TABLE %s (tablename VARCHAR(30) PRIMARY KEY, nextid INTEGER)" % TABLE_NAME
select_id_sql = "SELECT nextid FROM %s WHERE tablename = %%s" % TABLE_NAME
insert_new_sql = "INSERT INTO %s (tablename, nextid) VALUES (%%s, 0)" % TABLE_NAME
update_sql = "UPDATE %s SET nextid = nextid+1 WHERE tablename = %%s" % TABLE_NAME
lock_sql = "LOCK TABLE %s WRITE" % TABLE_NAME
unlock_sql = "UNLOCK TABLES"

def create_id_table(connection):
    connection.cursor().execute(create_table_sql)

def db_get_next_id(connection, table_name, create_table=True, create_row=True):
    cursor = connection.cursor()
    try:
        try:
            cursor.execute(lock_sql)
            cursor.execute(select_id_sql, [table_name])
            next = cursor.fetchone()
            if next is None:
                cursor.execute(insert_new_sql, [table_name])
                cursor.execute(select_id_sql, [table_name])
                next = cursor.fetchone()
            cursor.execute(update_sql, [table_name])
        finally:
            cursor.execute(unlock_sql)
            cursor.close()
    except MySQLdb.ProgrammingError, e:
        if e.args[0] != ER.NO_SUCH_TABLE or not create_table:
            raise
        create_id_table(connection)
        return db_get_next_id(connection, table_name, create_table=False)
    return int(next[0])


#------------------------------------------------------------------

def initialize(connection):
    for cls in lsctables.TableByName.values():
        if cls.next_id is not None:
            cls.get_next_id = lambda self: type(self.next_id)(db_get_next_id(connection, self.next_id.table_name))
            classmethod(cls.get_next_id)

def insert_ligolw_tables(connection, filename, verbose=False):

    initialize(connection)
    #
    # parse .xml file into memory, reassign ids, write xml stream to in-ram
    # buffer
    #
    xmldoc = ligolw_reassign_ids(
        utils.load_filename(
            filename,
            gz = (filename or "stdin").endswith(".gz"),
            verbose = verbose,
            contenthandler = LIGOLWRAMContentHandler
        ),
        verbose = verbose
    )

    # <-- find coinc_event_id
    coinc_table = glue.ligolw.table.get_table(
            xmldoc,
            glue.ligolw.lsctables.CoincTable.tableName)
    coinc_id = coinc_table[0].coinc_event_id


    buf = StringIO.StringIO()
    utils.write_fileobj(xmldoc, buf)
    buf.seek(0)
    #
    # re-parse xml stream from in-ram buffer to sqlite database
    #
    dbtables.DBTable_set_connection(connection)
    xmldoc, digest = utils.load_fileobj(buf, contenthandler = LIGOLWDBContentHandler)
    xmldoc.unlink()
    dbtables.DBTable_set_connection(None)

    return coinc_id

if __name__ == "__main__":
    import sys

    user = sys.argv[1]
    password = sys.argv[2]
    db = sys.argv[3]
    filename = sys.argv[4]

    conn= MySQLdb.connect(user=user, passwd=password, db=db)

    rv = insert_ligolw_tables(conn, filename)
    print "OK", rv
