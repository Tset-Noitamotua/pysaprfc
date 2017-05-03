# Sample configuration file for sap_get_defs.py script

connection_string='ASHOST=localhost SYSNR=17 CLIENT=000 USER=developer PASSWD=***'
db_name='/opt/src/rfcsdk6.2/rfcsdk/test_sap'

structure_defs=[('t002','T002')]
field_defs=[('tcurr-kurst','TCURR','KURST'),('tcurr-fcurr','TCURR','FCURR')]
function_defs=[('func1','STFC_CONNECTION')]
