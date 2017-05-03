# This examples shows how to perform remote function calls
# It shows new way to use the get_interface method in a more
# pythonic way and the new make_py_func method.

# Connection to SAP R/3 system is needed for this example

import pysap
import sys
import ctypes

# Modify next line to suit your connection details
sap_conn=pysap.Rfc_connection(conn_file='sapconn.ini')
sap_conn.open()

# Create remote function interface
# func_args and func_res specify arguments to be sent to/received from SAP system
func=sap_conn.get_interface('RFC_GET_TABLE_ENTRIES',func_args=['TABLE_NAME','MAX_ENTRIES'],func_res=['ENTRIES'])

# Print its description
print func.desc

# Perform function call
# Only the arguments specified will be passed to/from SAP. This reduces bandwith.
# Note: Trying to access other parameters defined by 'RFC_GET_TABLE_ENTRIES'
# but not defined by func_args and func_res will raise SapRfcError.
# We pass values as arguments, both positional and keyword arguments are possible.
# The order of positional arguments is specified by func_args.
# entries is an ItTable instance containg the results.
try:
    entries=func('T001',20)
# Keyword arguments are also possible:
##    entries=func(MAX_ENTRIES=20,TABLE_NAME='T001')
except pysap.SapRfcError,desc:
    print "Error invoking 'RFC_GET_TABLE_ENTRIES': %s" % desc
else:
# Everything went well
# Now we have to translate received table (entries) to the format of T001
# First create an internal table having structure of T001 as defined in DDIC
    itab=sap_conn.get_table('T001')
# Then copy rows of 'ENTRIES' to itab - this also converts rows structure on the fly
    itab.append_from_table(entries)
# Using slicing above line could be rewritten as:
#itab[:]=entries
# Print some fields from itab to show it worked
    for p in itab:
        print '%(BUKRS)5s %(BUTXT)-30s %(ORT01)-25s' % p
        
# Now let's get function module interface for BAPI
# We will use make_py_func method which is a wrapper for the new
# style of get_interface returning a function object wrapping the actual
# RFC_FUNC object.
func=sap_conn.make_py_func('BAPI_SALESORDER_GETLIST',func_args=['CUSTOMER_NUMBER','SALES_ORGANIZATION','DOCUMENT_DATE'],func_res=['SALES_ORDERS'])

# Perform function call (modify values to fit your system)
# Allthough 'CUSTOMER_NUMBER' is defined as CHAR, numerical values passed to it must be formatted as NUMC
# Note: when using make_py_func only keyword arguments are allowed
try:
    sales_orders=func(CUSTOMER_NUMBER='%010d' % 7315,SALES_ORGANIZATION='0500',DOCUMENT_DATE='22.6.2001') # DOCUMENT_DATE='20010622' if you don't have mxDateTime
except pysap.SapRfcError,desc:
    print "Error invoking 'BAPI_SALESORDER_GETLIST': %s" % desc
else:
# Everything went ok - print the results (if any)
    for p in sales_orders:
        print p
# Additional notes:
# To pass SAP structure as a argument use a valid structure instance or a dictionary of field_name:field_value pairs.
# To pass SAP table as argument use a valid ItTable instance or a list of dictionaries, strings, or lists describing rows.


# Create structure using definition of VBAK from DDIC
# Structure contains only fields specified
s_vbak=sap_conn.get_structure('VBAK','vbeln','kunnr','erdat')
# Create an instance ...
tst=s_vbak()
# ... fill it with data ...
tst.from_list(('10029','1282','20030414'))
# ... and print it
print tst

# Close the connection before quiting
sap_conn.close()
print 'ok'
