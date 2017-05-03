"""Small tool to retrieve data definitions and function interfaces from SAP R/3 and store them locally,
using the pysap.Storage object.
The script takes one argument - the name of configuration file. Configuration file
is a simple Python script containing data definitions.
Following variables must be defined in configuration file:
db_name - filename of the database where data will be stored
either connection_string or connection_file (and optionally connection_name) - connection data to be passed to
pysap.Rfc_connection __init__ method

Tool recognizes three configuration variables:

structure_defs - a list of structure definitions to retrieve from SAP.
Each item is a list of form (data_key,structure_name,*field_names). Structure definition is retrieved from
SAP system calling get_structure(structure_name,*field_names) method of pysap.Rfc_connection and stored in
database using data_key as key.

field_defs - a list of field definitons to retrieve.
Each item is a list with three items: data_key, structure_name, field_name. A tuple of exid (SAP datattype),
length, and decimals is stored in the database using data_key as key.

function_defs - a list of function interfaces to retrieve.
Each item is a list of two elements: data_key and function_name. Definition of function_name is retrieved from
SAP system using the get_interface method of pysap.Rfc_connection and stored in database using data_key as key.

serv_function_defs - similiar to function_defs but only stores parameter definition. Usefull for Python functions
with ABAP proxies. Use the _interface_from_ attribute of RFC_SERV_FUNCTION to restore parameter definitions. This
attribute should be a list having two items: a pysap.Storage instance and data key.

Retrieving stored objects in your programs

Open a pysap.Storage object (using the same file name as in db_name)
db=pysap.Storage('/path/to/my/database')

Structures:
struc=db['t002'] # retrieve structure definition
s1=struc()       # create structure instance

Field definitions:
fld=pysap.create_simple(*db['tcurr-kurst']) # create a variable using the TCURR-KURST definition from DDIC

Functions:
# create and open connection to SAP system
db=pysap.Storage('/path/to/db')
conn=pysap.Rfc_connection(...)
conn.open()
# retrieve function definition from the database (You can do this before the connection to SAP system is estabilished)
func1=db['stfc_connection']
func1.reconnect(conn.handle) # IMPORTANT - allways reconnect function to actual connection before usage
# fill import parameters
...
# perform function call
func1()
...

Server functions:
db=pysap.Storage('/path/to/db')
class MyFunc(pysap.RFC_SERV_FUNC):
    _name_='Z_MY_FUNC'
    _interface_from_=db,'z_my_func_def'
    def run(self,handle):
        ...
"""

import sys
import pysap
import imp
import os.path

if len(sys.argv)<2:
        print 'Usage sap_get_defs.py config_file'
        sys.exit(1)

config={}        

execfile(sys.argv[1],globals(),config)

if not config.has_key('db_name'):
        print 'Error: "db_name" missing'
        sys.exit(1)
if not config.has_key('connection_string') and not config.has_key('connection_file'):
        print 'Error: specify either "connection_string" or "connection_file"'
        sys.exit(1)
        
if config.has_key('connection_string'):
        conn=pysap.Rfc_connection(conn_string=config['connection_string'])
else:
        if not config.has_key('connection_name'):
                config['connection_name']=''
        conn=pysap.Rfc_connection(conn_file=config['connection_file'],conn_name=config['connection_name'])

try:
        conn.open()
except pysap.SapRfcError,e:
        print 'Error opening connection: "%s"' % e
        sys.exit(1)
try:
        db=pysap.Storage(config['db_name'])
except Exception,e:
        print 'Error opening database: "%s"' % e
        sys.exit(1)
if config.has_key('structure_defs'):
        for el in config['structure_defs']:
                try:
                        struct=conn.get_structure(*el[1:])
                except pysap.SapRfcError,e:
                        print 'Warning: getting structure "%s" failed, reported error was "%s"' % (el[1],e)
                else:
                        db[el[0]]=struct

if config.has_key('field_defs'):
        for el in config['field_defs']:
                ky,struc_name,fld_name=el
                try:
                        fld_lst=conn.get_fieldlist(struc_name,fld_name)
                except pysap.SapRfcError,e:
                        print 'Warning: getting field definiton "%s-%s" failed, reported error was "%s"' % (struc_name,fld_name,e)
                else:
                        db[ky]=fld_lst[0][1:]
                        
if config.has_key('function_defs'):
        for ky,f in config['function_defs']:
                try:
                        func=conn.get_interface(f)
                except pysap.SapRfcError,e:
                        print 'Warning: getting function interface "%s" failed, reported error was "%s"' % (f,e)
                else:
                        db[ky]=func

if config.has_key('serv_function_defs'):
    for ky,f in config['serv_function_defs']:
        try:
            func=conn.get_interface(f)
        except pysap.SapRfcError,e:
            print 'Warning: getting server function interface "%s" failed, reported error was "%s"' % (f,e)
        else:
            db[ky]=func.args()

conn.close()
print 'ok'
