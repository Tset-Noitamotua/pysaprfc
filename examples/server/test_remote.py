#! /usr/bin/python

# This is a simple example of Python SAP RFC server script.

import pysap
import sys

class Test(pysap.RFC_SERV_FUNC):
        _name_='Z_TEST1'
        _doc_="""
Z_TEST1
  IMPORTING
    IN_VALUE
    IN_VALUE2
    IN_VALUE3
  EXPORTING
    OUT_VALUE
    OUT_DATE
    OUT_STRUCT
  TABLES
    ITAB
  EXCEPTIONS
    NOT_NULL"""
        
        _importing_=[('IN_VALUE','I'),
                     ('IN_VALUE2','I'),
                     ('IN_VALUE3','D')]
        _exporting_=[('OUT_VALUE','I'),
                     ('OUT_DATE','D'),
                     ('OUT_STRUCT',
                      [('name','C',40),
                       ('val1','N',10),
                       ('date','D')])]
        _tables_=[('ITAB',
                   [('name','C',30),
                    ('val1','N',8),
                    ('val2','N',8),
                    ('val3','P',8,2),
                    ('val4','D')])]

        def run(self,handle):
                if self['IN_VALUE']==0: # Raise error (and fill the table ITAB) if IN_VALUE equals 0
                        self['ITAB'].refresh()
                        wa=self['ITAB'].struc()
                        wa.from_list(['Data error!',0,0,0])
                        self['ITAB'].append(wa)
                        raise pysap.SapFuncError('NOT_NULL')
                self['OUT_VALUE']=5*self['IN_VALUE']+self['IN_VALUE2']
                self['OUT_DATE']=self['IN_VALUE3']
                self['OUT_STRUCT']['NAME']='Test 1'
                self['OUT_STRUCT']['VAL1']=200
                self['OUT_STRUCT']['DATE']='20030604'
                # Modify rows of ITAB received from remote system
                for wa in self['ITAB']:
                        wa['val3']=wa['val2']*wa['val3']*self['IN_VALUE']
                # Add few rows to ITAB
                for i in range(3):
                        wa=self['ITAB'].struc()
                        wa.from_list(['Test %d' % i,i,5*i,1.5*i,'20030605'])
                        self['ITAB'].append(wa)                

# Create server
srv=pysap.RfcServerEx()
try:
        srv.register_func(Test) # Register function ...
        srv.main_loop(sys.argv) # ... and enter the main loop
except pysap.SapRfcError,desc:
        sys.exit(1)
