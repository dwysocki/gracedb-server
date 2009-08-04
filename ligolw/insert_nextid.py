import MySQLdb
from MySQLdb.constants import ER

conn = MySQLdb.connect(db='ligolw', user='root')

TABLE_NAME = "ligolwids"

create_table_sql = "CREATE TABLE %s (tablename VARCHAR(30) PRIMARY KEY, nextid INTEGER)" % TABLE_NAME
select_id_sql = "SELECT nextid FROM %s WHERE tablename = %%s" % TABLE_NAME
insert_new_sql = "INSERT INTO %s (tablename, nextid) VALUES (%%s, 0)" % TABLE_NAME
update_sql = "UPDATE %s SET nextid = nextid+1 WHERE tablename = %%s" % TABLE_NAME
lock_sql = "LOCK TABLE %s WRITE" % TABLE_NAME
unlock_sql = "UNLOCK TABLES"

def create_id_table(connection):
    connection.cursor().execute(create_table_sql)

def next_id(connection, table_name, create_table=True, create_row=True):
    next = None
    cursor = connection.cursor()
    try:
        try:
            cursor.execute(lock_sql)
            cursor.execute(select_id_sql, [table_name])
            next = cursor.fetchone()
            if not next:
                cursor.execute(insert_new_sql, [table_name])
                cursor.execute(select_id_sql, [table_name])
                next = cursor.fetchone()
            cursor.execute(update_sql, [table_name])
        finally:
            cursor.execute(unlock_sql)
            cursor.close()
    except MySQLdb.ProgrammingError, e:
        # XXX remove
        global foo
        foo = e
        cursor.close()
        if e.args[0] == ER.NO_SUCH_TABLE:
            if not create_table:
                raise
            create_id_table(connection)
            return next_id(connection, table_name, create_table=False)
        else:
            raise
    cursor.close()
    return next[0]

