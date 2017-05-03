# This is an example of how to use the Select object of the pyabap module.
# Connection to a SAP R/3 system is needed for this example.
#
# pyabap.py is currently in its testing stage and is there to demonstrate the usage
# of exec_abap method which was added to RfcConnection in release 0.99.0. In future it
# migth become part of standard pysaprfc package.

import pysap
import pyabap
import time
import sys

conn='LCHECK=1 ASHOST=localhost CLIENT=000 SYSNR=17 USER=developer PASSWD=***'
sap_conn=pysap.Rfc_connection(conn)
try:
    sap_conn.open()
except pysap.SapRfcError,desc:
    print desc
    sys.exit(1)
itab=sap_conn.get_table('TCURR')
# Uncomment the next line if you want to just fetch a subset of fields
#itab=pysap.ItTable('itab',sap_conn.get_structure('TCURR','FCURR','TCURR','KURST','UKURS'))
s=pyabap.Select(sap_conn,'TCURR',itab,['fcurr'],from_line=10,to_line=20)
s.append_cond('fcurr','I','=','EUR')
try:
    t=time.time()
    rez=s()
    t=time.time()-t
except pysap.SapRfcError,desc:
    print desc
else:
    for l in rez:
        print l
    print t,len(rez)
sap_conn.close()
