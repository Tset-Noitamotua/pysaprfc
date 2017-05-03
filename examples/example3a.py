# This example shows how to retrieve data from SAP R/3.
# It also shows how to extend structure obtained from SAP system with custom fields.

# This example needs connection to SAP R/3 system.

# This example is basically the same as example3.py but it uses data conversion routine to
# translate inverted date to 'normal' date instead of using additional table.
import pysap
import time

def inv_to_date(obj,inv_date):
    # Small function to convert SAPs inverse date to 'normal' date
    dat=99999999-int(inv_date)
    year,day=divmod(dat,100)
    year,month=divmod(year,100)
    return time.strftime(pysap.RFC_DATE_FORMAT,(year,month,day,0,0,0,0,0,0))

# Change next line to be able to connect to your SAP system
sap_conn=pysap.Rfc_connection(conn_file='sapconn.ini',conn_name='my_connection')
sap_conn.open()
# Read at most 20 entries from TCURR for AUD and exchange rate type 'M'
itab_tcurr=sap_conn.read_table('TCURR',options=["fcurr eq 'AUD' and ","kurst eq 'M'"],max_rows=20)
# Set (output) conversion routine for field 'gdatu'
itab_tcurr.struc.set_conversion('gdatu',out_conv=inv_to_date)
# Create sort function for the table
# Sort by date (gdatu) using its int_value (inverted date) in ascending order
sort_fnc=pysap.create_sort_func(('gdatu','int_value',1))
# Sort table
itab_tcurr.sort(sort_fnc)
# Print data (table lines act like dictionaries using field names as keys)
for l in itab_tcurr:
    print '%(gdatu)-20s%(fcurr)5s%(tcurr)5s%(ukurs)16.4f' % l
