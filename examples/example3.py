# This example shows how to retrieve data from SAP R/3.
# It also shows how to extend structure obtained from SAP system with custom fields.

# This example needs connection to SAP R/3 system.

# In this example we'll read exchange rates from SAP system. Exchange rates are stored in
# transparent table TCURR. We'd like our output to be: date, forreign currency (ISO code),
# local currency (ISO code), exchange rate. The problem is SAP stores dates in TCURR in so-called
# inverse format which is not suitable for display. Therefore we'll create additional table
# having same fields as TCURR with an extra date field added. In this field we'll store the
# converted date. We'll then sort the new table by date in ascending order and print it.

import pysap

def inv_to_date(inv_date):
    # Small function to convert SAPs inverse date to 'normal' date (internal format)
    return str(99999999-int(inv_date))

# Change next line to be able to connect to your SAP system
sap_conn=pysap.Rfc_connection(conn_file='sapconn.ini',conn_name='my_connection')
sap_conn.open()
# Get field description for structure TCURR (foreign currency exchange rates) from DDIC
tcurr_fld_lst_ext=sap_conn.get_fieldlist('TCURR')
# Append additional field
tcurr_fld_lst_ext.append(('datum','D'))
# Read 20 entries from TCURR for AUD and exchange rate type 'M'
itab_tcurr=sap_conn.read_table('TCURR',options=["fcurr eq 'AUD' and ","kurst eq 'M'"],max_rows=20)
# Create new internal table with extended structure - new table has same fields as itab_tcurr plus
# additional field 'datum' to store dates
itab_tcurr_ext=pysap.create_table('itab1',tcurr_fld_lst_ext)
#Fill created table with entries from SAP
for l in itab_tcurr:
    l1=itab_tcurr_ext.struc()
    l1.copy_corresp_from(l)
    l1['datum']=inv_to_date(l['gdatu']) #Convert inverse date to normal date - this field was added to extended structure
    itab_tcurr_ext.append(l1)
# Create sort function for the extended table
# Sort by date (datum) using its int_value (allways use int_value when sorting dates) in ascending order
sort_fnc=pysap.create_sort_func(('datum','int_value',0))
# Sort table
itab_tcurr_ext.sort(sort_fnc)
# Print data (table lines act like dictionaries using field names as keys)
for l in itab_tcurr_ext:
    print '%(datum)-20s%(fcurr)5s%(tcurr)5s%(ukurs)16.4f' % l
