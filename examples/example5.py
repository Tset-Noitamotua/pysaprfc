# This example demonstrates how to use conversion routines. (Those are roughly similar to conversion exits
# in ABAP.)
#
# There are two types of conversions, namely input and output conversions.
# Both types work with ext_values only. Input conversions get triggered when setting
# ext_value and transform the value before it's stored. Output conversions get triggered when
# getting ext_value and transform the value before it's output (without changing the stored value).
# Conversion routine takes two arguments: an instance of SAP datatype which stores the value and the
# value itself, and returns the transformed value.
# Supported datatypes are: C, N, D, T, and P.
#
# Connection to the SAP system is not needed for this example.

import pysap

# This example shows how to peruse conversion routine to do value checking.
def inValue(self,v):
        if not v: v='H' # default value
        v=v.upper()
        if v in ('H','B','T'):
                return v
        else:
                raise ValueError('invalid value')
        
# This is the output conversion routine.
def outValue(self,v):
        return {'H':'home','B':'bussiness','T':'test'}.get(v,'')

S=pysap.create_struct([('desc','C',40),('typ','C',1)])
# Here we set conversion routines for the field 'typ'. set_conversion is a class method. (It sets conversion
# routines for all instances of class S.)
S.set_conversion('typ',inValue,outValue)
s=S()
s['desc']='system 1'
s['typ']='T'
print s
s['desc']='system 2'
# This should trigger a ValueError.
try:
        s['typ']='X'
except ValueError:
        print 'ok'
else:
        print 'Huh?! Something is wrong here.'
s['desc']='system 3'
s['typ']='b'
# ext_value returns 'bussiness' (because of output conversion)
print s.typ.ext_value
# int_value returns 'B' (result of input conversion)
print s.typ.int_value
# Setting in_conv or out_conv to None disables conversion
S.set_conversion('typ',out_conv=None)
# ext_value now returns 'B' as output conversion has been disabled
print s['typ']