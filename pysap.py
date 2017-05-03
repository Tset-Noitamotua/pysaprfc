import ctypes as c
import os,sys,types
import shelve as _shelve

__version__='1.0.0rc1'

has_mx=1
try:
    from mx import DateTime
except ImportError:
    has_mx=0
    date_parser=None
has_fp=1
try:
    from fixedpoint import FixedPoint
except ImportError:
    has_fp=0
# Variables available for customization    
RFC_DATE_FORMAT='%d.%m.%Y'
RFC_TIME_FORMAT='%H:%M:%S'

#Constants
RFC_SIMPLE_DATA=0
RFC_STRUCTURE=1
RFC_TABLE=2

if sys.version_info[:2]<(2,2):
    raise ImportError('Python 2.2+ needed, your version_info is %r' % sys.version_info)

if os.name=='posix':
    librfc=c.cdll.LoadLibrary('librfccm.so')
    libc=c.cdll.LoadLibrary('/lib/libc.so.6')
    SAP_CALLBACK_FUNC=c.CFUNCTYPE(c.c_int,c.c_int)
    if has_mx:
        def date_parser(datum):
            return DateTime.strptime(datum,'%Y%m%d')
        def time_parser(time):
            return DateTime.strptime(time,'%H%M%S')
elif os.name=='nt':
    librfc=c.windll.librfc32
    libc=c.cdll.msvcrt
    SAP_CALLBACK_FUNC=c.WINFUNCTYPE(c.c_int,c.c_int)
    if has_mx:
        def date_parser(datum):
            return DateTime.Parser.DateFromString(datum)
        def time_parser(time):
            time='%06d' % int(time)
            return DateTime.Time(int(time[:2]),int(time[2:4]),int(time[4:]))
else:
    raise ImportError('sorry, %s is not supported' % os.name)

char_to_bcd=librfc.RfcConvertCharToBcd
bcd_to_char=librfc.RfcConvertBcdToChar

def setSystemCodePage(cpage):
    rc=librfc.RfcSetSystemCodePage(cpage)
    if rc:
        raise SapRfcError('unable to set system code page')

def RfcSetBcd(v,lng,decs):
    """Helper function for SAP packed datatype (BCD)"""
    if isinstance(v,(float,int,long)): vs='%.*f' % (decs,v)
    elif has_fp and isinstance(v,FixedPoint): vs=str(v)
    elif isinstance(v,str): vs=v
    elif isinstance(v,unicode): vs=str(v)
    else: raise TypeError('argument 1 to RfcSetBcd should be either float, int, long, string, or fixed point')
    c_decs=c.c_int(decs)
    rez=(c.c_ubyte*lng)()
    rc=char_to_bcd(vs,len(vs),c.byref(c_decs),c.byref(rez),lng)
    if rc==0: return rez
    else: raise ValueError('error converting %s to packed' % vs)
    
def RfcGetBcd(v,lng,decs):
    """Helper function for SAP packed datatype (BCD)"""
    vs='\x00'*33
    rc=bcd_to_char(v,lng,decs,vs,33)
    vs=vs.strip()
    if vs[-1]=='-':
        vs='-'+vs[:-1]
    if rc==0:
        if has_fp: return FixedPoint(vs,decs)
        else: return eval(vs)
    else: raise ValueError('error converting %r from packed' % v)

class _Sap_string(c.c_char_p):
    encoding=sys.getdefaultencoding()
    def __init__(self,v=None):
        if v:
            v1=self.__convert_to_utf_8(v)
            c.c_char_p.__init__(self,v1)
        else:
            c.c_char_p.__init__(self)
    def __setattr__(self,ky,v):
        if ky=='value':
            raise AttributeError('value is read-only, use ext_value or int_value instead')
        else:
            c.c_char_p.__setattr__(self,ky,v)
    def __convert_to_utf_8(self,v):
        if isinstance(v,unicode):
            v1=v.encode('utf_8')
        elif isinstance(v,str):
            v1=v.decode(self.encoding).encode('utf_8')
        else:
            raise TypeError('string expected instead of %s instance' % v.__class__.__name__)
        return v1
    def __get_ext_value(self):
        v=c.c_char_p.__getattribute__(self,'value')
        if v:
            return v.decode('utf_8').encode(self.encoding)
        else:
            return ''
    def __set_value(self,v):
        v1=self.__convert_to_utf_8(v)
        c.c_char_p.__setattr__(self,'value',v1)
    def __get_int_value(self):
        v=c.c_char_p.__getattribute__(self,'value')
        if v:
            return self.value.decode('utf_8')
        else:
            return ''
    def set_encoding(cls,encoding):
        cls.encoding=encoding
    set_encoding=classmethod(set_encoding)
    ext_value=property(__get_ext_value,__set_value)
    int_value=property(__get_int_value,__set_value)

def set_encoding(enc):
    _Sap_string.set_encoding(enc)
    
class _SapInt(c.c_int):
    def __set_value(self,v):
        if v is None: v=0
        if isinstance(v,(str,unicode)): v=int(v)
        c.c_int.__setattr__(self,'value',v)
    def __get_value(self):
        return c.c_int.__getattribute__(self,'value')
    ext_value=property(__get_value,__set_value)
    int_value=ext_value

class _SapInt2(c.c_short):
    def __set_value(self,v):
        if v is None: v=0
        if isinstance(v,(str,unicode)): v=int(v)
        c.c_short.__setattr__(self,'value',v)
    def __get_value(self):
        return c.c_short.__getattribute__(self,'value')
    ext_value=property(__get_value,__set_value)
    int_value=ext_value

class _SapInt1(c.c_byte):
    def __set_value(self,v):
        if v is None: v=0
        if isinstance(v,(str,unicode)): v=int(v)
        c.c_byte.__setattr__(self,'value',v)
    def __get_value(self):
        return c.c_byte.__getattribute__(self,'value')
    ext_value=property(__get_value,__set_value)
    int_value=ext_value

class _SapFloat(c.c_float):
    def __set_value(self,v):
        if v is None: v=0.0
        if isinstance(v,(str,unicode)): v=float(v)
        c.c_float.__setattr__(self,'value',v)
    def __get_value(self):
        return c.c_float.__getattribute__(self,'value')
    ext_value=property(__get_value,__set_value)
    int_value=ext_value

def _do_conversion_in(obj,v):
    # Helper function for value conversions
    if hasattr(obj,'convert_input') and callable(obj.convert_input):
        return obj.convert_input(obj,v)
    else:
        return v

def _do_conversion_out(obj,v):
    # Helper function for value conversions
    if hasattr(obj,'convert_output') and callable(obj.convert_output):
        return obj.convert_output(obj,v)
    else:
        return v

def STRING(length):
    """
String type compatible with SAP CHAR datatype
"""
    class cls_string(c.Array):
        _type_=c.c_ubyte
        _length_=length
        def __set_val(self,niz):
            c_niz=c.c_buffer(niz)
            libc.memcpy(self,c_niz,self._length_)
        def __get_val(self):
            c_niz=(c.c_char*(length+1))()
            libc.memcpy(c_niz,self,length)
            return c_niz.value
        int_value=property(__get_val,__set_val)
        def __get_value(self):
            if self.int_value: return _do_conversion_out(self,self.int_value.strip())
            else: return _do_conversion_out(self,'')
        def __set_value(self,v):
            v=_do_conversion_in(self,v)
            if not v: v=' '
            if isinstance(v,int) and v<=sys.maxint:
                self.int_value='%0*d' % (self._length_,v)
            elif v.isdigit():
                try:
                    v1=int(v)
                    if v1<=sys.maxint: v=v1
                except ValueError:
                    self.int_value=v.ljust(self._length_)
                else:
                    if isinstance(v,int):
                        self.int_value='%0*d' % (self._length_,v)
                    else:
                        self.int_value=v.ljust(self._length_)
            else:
                self.int_value=v.ljust(self._length_)
        ext_value=property(__get_value,__set_value)
        def __str__(self):
            return self.ext_value
        def __repr__(self):
            return repr(self.ext_value)
    return cls_string

def NUM_STRING(length):
    """
SAP NUMC datatype (string representation of an integer value)
Internal value is a zero-filled string of length LENGTH.
External value is an integer.
"""
    class num_string(c.Array):
        _type_=c.c_ubyte
        _length_=length
        def __set_val(self,niz):
            c_niz=(c.c_char*(length+1))()
            c_niz.value=niz
            libc.memcpy(self,c_niz,self._length_)
        def __get_val(self):
            c_niz=(c.c_char*(length+1))()
            libc.memcpy(c_niz,self,self._length_)
            return c_niz.value
        int_value=property(__get_val,__set_val)
        def __set_value(self,v):
            v=_do_conversion_in(self,v)
            if v is None: v=0
            if isinstance(v,(str,unicode)): v=int(v)
            self.int_value='%0*d' % (self._length_,v)
        def __get_value(self):
            if self.int_value:
                return _do_conversion_out(self,int(self.int_value))
            return _do_conversion_out(self,0)
        ext_value=property(__get_value,__set_value)
        def __str__(self):
            return str(self.ext_value)
    return num_string

def DATE_STRING():
    """
SAP DATE datatype
Internal value is a string in format YYYYMMDD.
External value format is specified by RFC_DATE_FORMAT.
"""
    class date_string(c.Array):
        _type_=c.c_ubyte
        _length_=8
        def __str__(self):
            if self.int_value:
                if has_mx: return self.ext_value
                else: return self.int_value
            else: return ''
        def __repr__(self):
            return repr(str(self))
        def __nonzero__(self):
            return self.int_value and self.int_value!='00000000'
        def __set_val(self,niz):
            if niz is None: niz='00000000'
            c_niz=(c.c_char*(self._length_+1))()
            c_niz.value=niz
            libc.memcpy(self,c_niz,self._length_)
        def __get_val(self):
            c_niz=(c.c_char*(self._length_+1))()
            libc.memcpy(c_niz,self,self._length_)
            return c_niz.value
        int_value=property(__get_val,__set_val)
        def __set_value(self,v):
            v=_do_conversion_in(self,v)
            if not v or v=='00000000':
                self.int_value='00000000'
                return
            #if v is None: return
            if has_mx:
                if type(v) is type(DateTime.now()): self.int_value=v.strftime('%Y%m%d')
                elif isinstance(v,str):
                    self.int_value=DateTime.Parser.DateFromString(v).strftime('%Y%m%d')
                else: raise ValueError('Only DateTime or strings allowed')
            else:
                if isinstance(v,str): self.int_value=v
                else: raise ValueError('Only strings allowed')
        def __get_value(self):
            if self.int_value!='00000000':
                if has_mx: return _do_conversion_out(self,date_parser(self.int_value).strftime(RFC_DATE_FORMAT))
                else: return _do_conversion_out(self,self.int_value)
            return _do_conversion_out(self,'')
        ext_value=property(__get_value,__set_value)
    return date_string
        
def TIME_STRING():
    """
SAP TIME datatype
Internal value is a string of format HHMMSS.
External value format is specified by RFC_TIME_FORMAT.
"""
    class time_string(c.Array):
        _type_=c.c_ubyte
        _length_=6
        def __str__(self):
            if self.int_value:
                if has_mx: return self.ext_value
                else: return self.int_value
            else: return ''
        def __repr__(self):
            return repr(str(self))
        def __set_val(self,niz):
            c_niz=(c.c_char*(self._length_+1))()
            c_niz.value=niz
            libc.memcpy(self,c_niz,self._length_)
        def __get_val(self):
            c_niz=(c.c_char*(self._length_+1))()
            libc.memcpy(c_niz,self,self._length_)
            return c_niz.value
        int_value=property(__get_val,__set_val)
        def __set_value(self,v):
            v=_do_conversion_in(self,v)
            if v is None: v='000000'
            if has_mx:
                if type(v) is type(DateTime.now()): self.int_value=v.strftime('%H%M%S')
                elif isinstance(v,str):
                    if len(v)<=6 and str.isdigit():
                        self.int_value='%06d' % int(v)
                    else:
                        self.int_value=DateTime.Parser.TimeFromString(v).strftime('%H%M%S')
                else: raise ValueError('Only DateTime or strings allowed')
            else:
                if isinstance(v,str): self.int_value=v
                else: raise ValueError('Only strings allowed')
        def __get_value(self):
            if self.int_value:
                if has_mx: return _do_conversion_out(self,time_parser(self.int_value).strftime(RFC_TIME_FORMAT))
                else: return _do_conversion_out(self,self.int_value)
            return _do_conversion_out(self,'000000')
        ext_value=property(__get_value,__set_value)
    return time_string

def BCD(length,decs):
    """
SAP Packed datatype. Packed is basically a BCD (Binary Coded Decimal).
Sap Rfc routines are used to convert Packed to string and vice versa (see
RfcSetBcd and RfcGetBcd).
Internal value is a C UBYTE array holding SAP compatible representation of arguments value.
External value is a float or if the fixedpoint module is installed a FixedPoint instance.
"""
    class cls_bcd(c.Array):
        _type_=c.c_ubyte
        _length_=length
        _decs_=decs
        def __set_value(self,v):
            v=_do_conversion_in(self,v)
            if v is None: v=0.0
            rez=RfcSetBcd(v,self._length_,self._decs_)
            if rez: libc.memcpy(self,rez,self._length_)
        def __get_value(self):
            return _do_conversion_out(self,RfcGetBcd(self,self._length_,self._decs_))
        int_value=property(__get_value,__set_value)
        ext_value=int_value
        def __str__(self):
            return str(self.ext_value)
        def __repr__(self):
            if has_fp: return repr(str(self.ext_value))
            else: return repr(self.ext_value)
            
    return cls_bcd

def BYTES(length):
    """
SAP BYTES datatype
I don't have much experience with this datatype. Errors are thus possible, so handle with care.
"""
    class cls_bytes(c.Array):
        _type_=c.c_ubyte
        _length_=length
        def __set_value(self,v):
            if v is None:
                self.reset()
            else:
                if isinstance(v,str):
                    lng=min(len(v),self._length_)
                    libc.memcpy(self,v,lng)
                else:
                    raise ValueError('string expected')
        def __get_value(self):
            buff=c.c_buffer(self._length_+1)
            libc.memcpy(c.byref(buff),self,self._length_)
            return buff.raw[:-1]
        ext_value=property(__get_value,__set_value)
        int_value=ext_value
        def reset(self):
            zeroes=(c.c_char*length)()
            zeroes.raw='\x00'*length
            libc.memcpy(self,zeroes,length)
    return cls_bytes

# Helper functions used by structure builder
def XINT(length=0,decs=0):
    return _SapInt
def XINT2(length=0,decs=0):
    return _SapInt2
def XINT1(length=0,decs=0):
    return _SapInt1
def XCHAR(length,decs=0):
    return STRING(length)
def XFLOAT(length=0,decs=0):
    return _SapFloat
def XBCD(length,decs):
    return BCD(length,decs)
def XNUMC(length,decs=0):
    return NUM_STRING(length)
def XBYTES(length,decs=0):
    return BYTES(length)

def XDATE(length=0,decs=0):
    return DATE_STRING()
def XTIME(length=0,decs=0):
    return TIME_STRING()
def XSTRING(length=0,decs=0):
    return _Sap_string

SAP_MAP={'C':XCHAR,'N':XNUMC,'P':XBCD,'D':XDATE,'T':XTIME,'I':XINT,'F':XFLOAT,'X':XBYTES,'g':XSTRING,'s':XINT2,'b':XINT1}
SAP_ARG_TYP={'C':0,'N':6,'P':2,'D':1,'T':3,'I':8,'F':7,'X':4,'g':29,'s':9,'b':10}
SAP_INIT_VALUES={'C':('ext_value',' '),'N':('ext_value',0),'P':('ext_value',0.0),
                 'D':('int_value','00000000'),'T':('int_value','000000'),
                 'I':('value',0),'F':('value',0.0),'g':('ext_value',''),
                 's':('value',0),'b':('value',0)}

def _sap_def(typ,lng,dec):
    if typ in ('C','N','X'):
        return '%s%d' % (typ,lng)
    elif typ=='P':
        return '%s%d.%d' % (typ,lng,dec)
    else:
        return typ
    
class RFC_TYPE_ELEMENT(c.Structure):
    _fields_=[('name',c.c_char_p),
              ('type',c.c_uint),
              ('length',c.c_uint),
              ('decimals',c.c_uint),
              ('_not_used',c.c_uint)]

class Storage:
    def __init__(self,fname):
        self.__db=_shelve.open(fname)
    def __del__(self):
        self.__db.close()
    def close(self):
        self.__db.close()
    def __setitem__(self,ky,obj):
        if hasattr(obj,'_sap_struct_'): # Structures
            self.__db[ky]=('struct',obj._field_defs_)
        else: # Other objects
            self.__db[ky]=('',obj)
    def __getitem__(self,ky):
        ind,obj=self.__db[ky]
        if ind=='struct':
            return create_struct(obj)
        else:
            return obj
        
def create_simple(exid,lng=1,decs=0):
    if not SAP_MAP.has_key(exid):
        raise SapRfcError('unknow SAP datatype %s' % exid)
    return SAP_MAP[exid](lng,decs)()

def create_struct(desc):
    """
Class factory - creates a C structure compatible with SAP structure definition.
desc - list of field descriptions
Each field description is a tuple with at least two and at most four elements:
  name (mandatory)
  type (mandatory, SAP datatype - should be one of 'C' ,'N' ,'P', 'D', 'T', 'F', 'I', or 'X')
  length (mandatory for types 'C', 'N', 'P', and 'X')
  number of decimals (mandatory for type 'P')
Example:
STRUCT=create_struct([('description','C',30),('date','D'),('value','P',16,2)]) #Create structure class
s1=STRUCT()                                                                    #Create structure instance
#Now let's fill the structure with some values
s1['description']='Item 1'
s1['date']='16.1.2003'                                                         #If you have mxDateTime package installed
#s1['date']='20030116'                                                         #without mxDateTime package
s1['value']=10.45
print s1
"""
    fields=[]
    sap_field_types={}
    for fld in desc:
        fld_full=(tuple(fld)+(0,0))[:4]
        fld_name,fld_typ,fld_len,fld_dec=fld_full
        fld_c_type=SAP_MAP[fld_typ]
        fields.append((fld_name,fld_c_type(fld_len,fld_dec)))
        sap_field_types[fld_name]=fld_typ,fld_len,fld_dec
    #entries=(RFC_TYPE_ELEMENT*len(sap_field_types))()
    #i=0
    #for (name,desc) in sap_field_types.items():
        #typ,lng,decs=desc
        #entries[i].name=name
        #entries[i].type=SAP_ARG_TYP[typ]
        #entries[i].length=lng
        #entries[i].decimals=decs
        #i+=1
    #type_handle=c.c_ushort()
    #rc=librfc.RfcInstallStructure('STRUCT',c.byref(entries),len(entries),c.byref(type_handle))
    #if rc: raise SapRfcError('error installing structure')
    
    class STRUCT(c.Structure):
        _fields_=fields
        _sfield_names_=[fld[0].lower() for fld in fields]
        _sfield_sap_types_=sap_field_types
        _field_defs_=desc
        _type_handle_=0
        _sap_struct_=1 # type indicator (for Storage)
        _sfield_input_convs_={}
        _sfield_output_convs_={}
        _sfield_convs_={}
        def set_conversion(cls,fld,in_conv='',out_conv=''):
            # in_conv, out_conv: emtpy string means 'leave previous', None means 'remove'
            if isinstance(fld,(list,tuple)):
                for f in fld:
                    cls.set_conversion(f,in_conv,out_conv)
            else:
                if fld in cls._sfield_names_:
                    if in_conv!='': cls._sfield_input_convs_[fld]=in_conv
                    if out_conv!='': cls._sfield_output_convs_[fld]=out_conv
                    if in_conv or out_conv: cls._sfield_convs_[fld]=1
                    else:
                        if cls._sfield_input_convs_.get(fld,None) or cls._sfield_output_convs_.get(fld,None):
                            pass
                        else:
                            try:
                                del cls._sfield_convs_[fld]
                            except KeyError:
                                pass
                else:
                    raise KeyError(fld)
        set_conversion=classmethod(set_conversion)
        def __str__(self):
            s=''
            for f in self._fields_:
                s+='%s = %r\n' % (f[0],self[f[0]])
            return s
        def __getattribute__(self,ky):
            s_getattr=c.Structure.__getattribute__
            field_names=s_getattr(self,'_sfield_convs_')
            if ky in field_names:
                # Workaround: it seems that changing attributes of structure fields is not possible
                v=s_getattr(self,ky)
                if isinstance(v,(int,long,float,str,unicode)): return v
                v.convert_input=s_getattr(self,'_sfield_input_convs_').get(ky,None)
                v.convert_output=s_getattr(self,'_sfield_output_convs_').get(ky,None)
                return v
            else: return s_getattr(self,ky)
        def __getitem__(self,ky):
            """
This is a shortcut to self.attr.ext_value and also a preferred way to access ext_values of STRUCT fields.
"""
            if not isinstance(ky,(str,unicode)): raise TypeError('key must be string')
            ky=ky.lower()
            if ky in self._sfield_names_:
                v=getattr(self,ky)
                if hasattr(v,'ext_value'): return v.ext_value
                elif hasattr(v,'int_value'): return v.int_value
                elif hasattr(v,'value'): return v.value
                else: return v
            else:
                raise KeyError(ky)
        def __setitem__(self,ky,v):
            """
This is a shortcut to self.attr.ext_value and also a preferred way to access ext_values of STRUCT fields.
"""
            if not isinstance(ky,(str,unicode)): raise TypeError('key must be string')
            ky=ky.lower()
            if ky in self._sfield_names_:
                atr=getattr(self,ky)
                if hasattr(atr,'ext_value'): atr.ext_value=v
                elif hasattr(atr,'int_value'): atr.int_value=v
                elif hasattr(atr,'value'): atr.value=v
                else:
                    if isinstance(atr,int):
                        if isinstance(v,(str,unicode)): v=int(v)
                    elif isinstance(atr,float):
                        if isinstance(v,(str,unicode)): v=float(v)
                    elif isinstance(atr,str):
                        if v=='': v=' '
                    setattr(self,ky,v)
            else:
                raise KeyError(ky)
        def __eq__(self,other):
            if not isinstance(other,c.Structure):
                raise TypeError('structure required')
            return libc.memcmp(c.byref(self),c.byref(other),min(c.sizeof(self),c.sizeof(other)))==0
        def __ne__(self,other):
            return self.__eq__(other)==0
        def __len__(self):
            return c.sizeof(self)
        def from_structure(self,other):
            """
Copies structure other to self. Both structures must be compatible.
"""
            libc.memcpy(c.byref(self),c.byref(other),min(c.sizeof(self),c.sizeof(other)))
        def from_list(self,lst):
            """
lst - list of values.
"""
            i=0
            for l in lst:
                self[self._fields_[i][0]]=l
                i+=1
        def from_dict(self,dic):
            #flds=[fld[0] for fld in self._fields_]
            for ky,v in dic.items():
                ky=ky.lower()
                if ky in self._sfield_names_:
                    self[ky]=v
        def to_dict(self,*kys):
            rez={}
            for ky in [fld_name for fld_name in self._sfield_names_ if not kys or fld_name in kys]:
                rez[ky]=self[ky]
            return rez
        def copy_corresp_from(self,other,*fld_lst):
            """
Copies fields from other to fields of self having the same name. If fld_lst is given only the fields in fld_lst
are copied. Error will be raised if trying to copy from uncompatible types.
"""
            for fld,v in other._fields_:
                if fld in self._sfield_names_:
                    if not fld_lst or fld in fld_lst:
                        self[fld]=other[fld]
        def sum_corresp_from(self,other,*fld_lst):
            """
Similar to copy_corresp_from but this one adds fields of other to fields of self having the same name. 
"""
            for fld,v in other._fields_:
                if fld in self._sfield_names_:
                    if not fld_lst or fld in fld_lst:
                        self[fld]+=other[fld]
        def is_equal(self,other,*flds):
            if flds:
                if len(flds)==1:
                    return self[flds[0]]==other[flds[0]]
                else:
                    for fld in flds:
                        if (fld not in self._sfield_names_) or (fld not in other._sfield_names_):
                            return 0
                        if self[fld]!=other[fld]:
                            return 0
                    return 1
            else:
                return self==other
        def to_string(self,lng=0):
            if lng==0: lng=c.sizeof(self)
            buff=c.c_buffer('\x00',lng+1)
            libc.memcpy(c.byref(buff),c.byref(self),lng)
            return buff.raw[:-1]
        def from_string(self,str_val):
            buff=c.c_buffer(len(str_val)+1)
            buff.raw=str_val
            libc.memcpy(c.byref(self),buff,min(c.sizeof(self),len(str_val)))
        def sap_type(cls,fld_name):
            """Returns SAP type of field fld_name as single letter"""
            return cls._sfield_sap_types_[fld_name][0]
        sap_type=classmethod(sap_type)
        def sap_len(cls,fld_name):
            """Returns length of field fld_name"""
            return cls._sfield_sap_types_[fld_name][1]
        sap_len=classmethod(sap_len)
        def sap_decs(cls,fld_name):
            """Returns number of decimal places for field fld_name"""
            return cls._sfield_sap_types_[fld_name][2]
        sap_decs=classmethod(sap_decs)
        def sap_def(cls,fld_name):
            return _sap_def(*cls._sfield_sap_types_[fld_name])
        sap_def=classmethod(sap_def)
            
    return STRUCT

def create_sort_func(*fields):
    """
Function factory - creates sort function to use with sort method of ItTable instances.
fields - tuples with three elements (triples?):
  field name
  field attribute - should be one of 'int_value', 'ext_value', or '' (default, i.e. ext_value)
  sort direction - 0: ascending, 1: descending
See ItTable.sort documentation string for more info.
"""
    def sort_itab(l1,l2):
        for fld_name,attr_name,sort_dir in fields:
            if attr_name:
                v1=getattr(getattr(l1,fld_name),attr_name)
                v2=getattr(getattr(l2,fld_name),attr_name)
            else:
                v1,v2=l1[fld_name],l2[fld_name]
            if sort_dir: rez=cmp(v2,v1)
            else: rez=cmp(v1,v2)
            if rez:
                break
        return rez
    return sort_itab

class ItabFieldEventHandler:
    """
Event handler for fields of ItTable.
Assign callback functions to its on_new, on_endof, and on_every properties. Signature of callback functions must
be f(fh,wa). fh is an instance of ItabFieldEventHandler (self), and wa is an instance of STRUCTURE holding the current
line of the associated ItTable instance.
Events will be fired when looping through ItTable instance (or by calling its next method).
Note 1: you should use the add_field_handler method of the ItTable instance to instantiate the ItabEventHandler instance
(and not the class __init__ method), i.e. use fh=itab.add_field_handler('field1') instead of fh=ItabFieldHandler(itab,'field1').
Note 2: ItTable should be sorted for event handling to function correctly.
"""
    def __init__(self,itab,fld):
        self.itab=itab
        self.fld=fld
        if isinstance(fld,(list,tuple)):
            self.fld=fld
        else:
            self.fld=[fld]
        self.on_new=None
        self.on_endof=None
        self.on_every=None
    def _check_new(self,indx):
        """Check if the field value has changed from previous step."""
        prev=indx-1
        if (indx<len(self.itab)) and (prev<0 or not self.itab[indx].is_equal(self.itab[prev],*self.fld)):
            if self.on_new: self.on_new(self,self.itab[indx])
    def _check_endof(self,indx):
        """Check if field value will change in next step."""
        nxt=indx+1
#        if (indx<len(self.itab)) and (nxt>=(len(self.itab)) or self.itab[indx][self.fld]!=self.itab[nxt][self.fld]):
        if (indx<len(self.itab)) and (nxt>=(len(self.itab)) or not self.itab[indx].is_equal(self.itab[nxt],*self.fld)):
            if self.on_endof: self.on_endof(self,self.itab[indx])
    def _check_every(self,indx):
        """Executes once for each step."""
        if indx<len(self.itab):
            if self.on_every: self.on_every(self,self.itab[indx])

class ItTable(object):
    """
Pythonic representation of what is called internal table in SAP R/3.
ItTable tries to behave as python list - it supports indexing, slicing, sorting etc.
Indices starts with 0 (Python fashion) and not with 1 (SAP fashion).
ItTable provides event handling similar to AT FIRST, AT LAST, AT NEW, and AT ENDOF events of ABAP loops.
Assign callback functions to on_first and/or on_last properties to simulate AT FIRST and AT LAST behaviour of
ABAP loops in Python, and create field event handlers with add_field_handler to
simulate ABAP AT NEW and AT ENDOF for choosen fields.
"""
    def __init__(self,name,struc,occurs=0,handle=0):
        """
name - the name of internal table, used internally by SAP
struct - class (not instance!) created with create_struct class factory
occurs (optional) - see SAP documentation

Each line of the ItTable is an instance of the STRUCT class.
"""
        self.__struct=struc
        self.occurs=occurs
        self.name=name
        self.on_first=None
        self.on_last=None
        if handle:
            self.__handle=handle
            self.__external_handle=1
        else:
            self.__handle=librfc.ItCreate(name,c.sizeof(self.__struct),occurs,0)
            self.__external_handle=0
        self.__index=0
        self.__fld_handlers=[]

    def refresh(self):
        """
Clears the table.
"""
        if self.__handle: librfc.ItFree(self.__handle)

    def __len__(self):
        return self.count
        
    def append(self,data):
        """
Appends new line to the end of the table. Data must be an instance of self.struc.
"""
        p=librfc.ItAppLine(self.__handle)
        if p:
            libc.memcpy(p,c.addressof(data),c.sizeof(self.__struct))
            self.__index=self.count
        else:
            raise SapRfcError('error appending line')

    def insert(self,indx,data):
        """Inserts new line at given index."""
        p=librfc.ItInsLine(self.__handle,indx+1)
        if p:
            libc.memcpy(p,c.addressof(data),c.sizeof(self.__struct))
            self.__index=indx
        else:
            raise SapRfcError('error inserting line')

    def append_from_table(self,other):
        """
Appends all lines of ItTable other to the end of itself. self.struc and other.struc must be compatible
(but not necessary the same). See also STRUCT.from_structure.
"""
        l=self.__struct()
        for lo in other:
            l.from_structure(lo)
            self.append(l)

    def append_from_list(self,lst):
        """
Appends new line to the end of table and fills it with corresponding values from list lst.
"""
        l=self.__struct()
        l.from_list(lst)
        self.append(l)

    def append_from_dict(self,dic):
        """
Appends new line to the end of table and fills it with corresponding values from dictionary dict.
"""
        l=self.__struct()
        l.from_dict(dic)
        self.append(l)

    def append_from_string(self,s):
        l=self.__struct()
        l.from_string(s)
        self.append(l)

    def append_corresp_from_struct(self,other):
        """
Appends new line to the end of table and fills it with corresponding fields of structure other.
See also STRUCT.copy_corresp_from.
"""
        l=self.__struct()
        l.copy_corresp_from(other)
        self.append(l)

    def append_corresp_from_table(self,other):
        """
Appends new lines to the end of table and fills them with corresponding fields from lines of table other.
See also STRUCT.copy_corresp_from.
"""
        for l in other:
            self.append_corresp_from(l)

    def fill(self,val_list):
        """
Appends new lines to the end of table and fills them with values stored in a list of values val_list.
Allowed value types are str, list, tuple, dict, and ItTable.
"""
        for v in val_list:
            if isinstance(v,dict):
                self.append_from_dict(v)
            elif isinstance(v,str):
                self.append_from_string(v)
            elif isinstance(v,(tuple,list)):
                self.append_from_list(v)
            elif isinstance(v,ItTable):
                self.append_from_table(v)
            else:
                raise TypeError('str, list, tuple, dict or ItTable expected as list item type')

    def refresh_fill(self,val_list):
        """
Empties the table and then fills it with values stored in a list of values val_list.
See also ItTable.fill.
"""
        self.refresh()
        self.fill(val_list)
            
    def get_line(self,lno):
        p=librfc.ItGupLine(self.__handle,lno+1)
        if p:
            rez=self.__struct.from_address(p)
            return rez
        else:
            raise IndexError('Table %s - index out of range' % self.name)
        
    def copy_line(self,lno):
        """
Returns a copy of lno-th line of the table.
Changes to returned line will not be reflected in ItTable.
"""
        p=librfc.ItGetLine(self.__handle,lno+1)
        if p:
            rez=self.__struct()
            libc.memcpy(c.addressof(rez),p,c.sizeof(self.__struct))
            return rez
        else:
            raise IndexError('Table %s - index out of range' % self.name)
        
    def create_line(self):
        """
Creates a new instance of self.__struct. Alias for self.struct().
"""
        return self.__struct()

    def to_list(self,*kys):
        return [l.to_dict(*kys) for l in self] 
        
    def __get_count(self):
        return librfc.ItFill(self.__handle)
    
    def __del__(self):
        if self.__external_handle==0: librfc.ItDelete(self.__handle)
        
    def __get_struct(self):
        return self.__struct
    
    def __get_handle(self):
        return self.__handle
    
    def __set_handle(self,new_handle):
        if self.__handle and not self.__external_handle: librfc.ItDelete(self.__handle)
        self.__handle=new_handle
        self.__external_handle=1
        
    def __getitem__(self,indx):
        if type(indx) is types.SliceType:
            lo,hi,step=self.__handle_slice(indx)
            new_tab=ItTable(self.name,self.struc,self.occurs)
            new_tab._copy_handlers(self.__fld_handlers)
            new_tab.on_first=self.on_first
            new_tab.on_last=self.on_last
            for i in range(lo,hi,step):
                new_tab.append(self[i])
            return new_tab
        else:
            if indx<0: indx+=self.count
            if indx<0 or indx>self.count-1: raise IndexError('table %s - list index out of range' % self.name)
            return self.get_line(indx)
    
    def __setitem__(self,indx,data):
        if type(indx) is types.SliceType:
            lo,hi,step=self.__handle_slice(indx)
            if step!=1: raise IndexError('stepping not supported when assigning to slice')
            if isinstance(data,ItTable):
                st=lo
                for wa1 in data:
                    wa=self.__struct()
                    wa.from_structure(wa1)
                    if st<hi:
                        self[st]=wa
                    else:
                        self.insert(st,wa)
                    st+=step
                if len(data)<(hi-lo):
                    for i in range(hi-lo-len(data)):
                        del self[st]
            else:
                raise TypeError('must assing ItTable to slice')
        else:
            if indx<0: indx+=self.count
            if indx<0 or indx>self.count-1: raise IndexError('table %s - list index out of range' % self.name)
            rc=librfc.ItPutLine(self.__handle,indx+1,c.byref(data))
            if rc==-1:
                raise ValueError('Table %s - value error' % self.name)

    def __handle_slice(self,indx):
        #Handles slices
        lo,hi,step=indx.start,indx.stop,indx.step
        if lo and lo<0: lo+=self.count
        if hi and hi<0: hi+=self.count
        if not step: step=1
        if not(0<=lo<self.count): lo=None
        if not(0<=hi<=self.count): hi=None
        if not hi:
            if step<0:
                hi=-1
            else:
                hi=self.count
        if not lo:
            if step<0:
                lo=self.count-1
            else:
                lo=0
        return lo,hi,step
        
    def __delitem__(self,indx):
        if type(indx) is types.SliceType:
            lo,hi,step=self.__handle_slice(indx)
            if step<0: lo,hi,step=hi,lo,-step
            hi=min(hi,self.count-1)
            for i in range(hi,lo,-step):
                del self[i]
        else:
            rc=librfc.ItDelLine(self.__handle,indx+1)
            if rc>0:
                raise IndexError('Table %s - index out of range' % self.name)
            elif rc<0:
                raise RuntimeError('Error when deleting line %d from table %s' % (indx,self.name))
            if self.__index>self.count: self.__index=self.count
    
    def __iter__(self):
        self.__index=0
        return self
    
    def next(self):
        if self.__index>=self.__get_count():
            if self.__fld_handlers: self.__handle_endof()
            if self.on_last: self.on_last(self)
            raise StopIteration
        else:
            if self.__fld_handlers and self.__index>0: self.__handle_endof() #don't handle endof at first item
            self.__index+=1
            if self.__index==1 and self.on_first: self.on_first(self)
            if self.__fld_handlers: self.__handle_new()
            if self.__fld_handlers: self.__handle_every()
            return self[self.__index-1]

    def add_field_handler(self,fld_name):
        """
Adds an ItabFieldHandler instance to list of field handlers and returns its reference for further manipulation. 
"""
        fh=ItabFieldEventHandler(self,fld_name)
        self.__fld_handlers.append(fh)
        return fh
    
    def get_field_handler(self,indx):
        """
Returns ItabFieldHandler instance with index indx from field handlers list.
"""
        return self.__fld_handlers(indx)
        
    def remove_field_handler(self,indx):
        """
Removes ItabFieldHandler instance with index indx from field handlers list.
"""
        del self.__fld_handlers[indx]

    def remove_field_handlers(self):
        """Empties field handlers list."""
        self.__fld_handlers=[]

    def remove_all_handlers(self):
        """Like remove_field_handlers but it also empties on_first and on_last properties."""
        self.remove_field_handlers()
        self.on_first=None
        self.on_last=None
        
    def __handle_new(self):
        for e in self.__fld_handlers:
            e._check_new(self.__index-1)
            
    def __handle_endof(self):
        self.__fld_handlers.reverse()
        try:
            for e in self.__fld_handlers:
                e._check_endof(self.__index-1)
        finally:
            self.__fld_handlers.reverse()

    def __handle_every(self):
        for e in self.__fld_handlers:
            e._check_every(self.__index-1)

    def _copy_handlers(self,f_hnds):
        self.__fld_handlers=f_hnds[:]
        for fh in self.__fld_handlers:
            fh.itab=self
    
    def __get_size(self):
        return c.sizeof(self.__struct)
    
    def __partition(self,cmp_func,start,end):
        # Written by Magnus Lie Hetland (http://www.hetland.org/python/quicksort.html)
        pivot = self.copy_line(end)
        bottom = start-1
        top = end    
        done = 0
        while not done:    
            while not done:
                bottom=bottom+1    
                if bottom==top:
                    done = 1
                    break    
                if cmp_func(self[bottom],pivot)>0:
                    self[top]=self.copy_line(bottom)
                    break    
            while not done:
                top=top-1                
                if top==bottom:
                    done=1
                    break    
                if cmp_func(self[top],pivot)<0:
                    self[bottom]=self.copy_line(top)
                    break    
        self[top] = pivot
        return top

    def __quicksort(self,cmp_func,start,end):
        # Written by Magnus Lie Hetland (http://www.hetland.org/python/quicksort.html)
        if start < end:
            split=self.__partition(cmp_func,start,end)
            self.__quicksort(cmp_func,start,split-1)
            self.__quicksort(cmp_func,split+1,end)
        else:
            return
        
    def sort(self,cmp_func):
        """
Sort table using cmp_func.
Use the create_sort_func function to create cmp_func.
(You can also code your own sort function, of course).
"""
        self.__quicksort(cmp_func,0,self.count-1)
        
    struc=property(__get_struct,doc="Structure class definiton - read only")
    handle=property(__get_handle,__set_handle,doc="Rfc table handle - read only")
    count=property(__get_count,doc="Number of lines - read only")
    size=property(__get_size,doc="Size (in bytes) of a line - read only")
    
def create_table(name,struc,occurs=0,handle=0):
    """
Helper function - creates an instance of ItTable.
struct - list of field definitions (same format as for create_struct)
occurs - see SAP documentation
"""
    return ItTable(name,create_struct(struc),occurs=occurs,handle=handle)

class RFC_PARAM(object):
    """
This class stores information about single parameter of the RFC function module - its name, sap type,
parameter type (simple, structure, or table), length and so on. It's meant to be used as a part of function
module interface.
"""
    def __init__(self,param_name,param_typ,param_exid,param_length,data_type,param,active=1):
        self.name=param_name.upper()
        self.typ=param_typ
        if param_exid.strip()=='': param_exid='C'
        self.exid=param_exid
        if data_type==RFC_SIMPLE_DATA: self.arg_typ=SAP_ARG_TYP[param_exid]
        elif data_type==RFC_STRUCTURE: self.arg_typ=param._type_handle_
        else: self.arg_typ=0
        self.length=param_length
        self.data_type=data_type
        self.__value=param
        self.active=active
    def __getstate__(self):
        odict=self.__dict__.copy()
        del odict['_RFC_PARAM__value'] # remove __value (structures and tables are not pickable)
        if self.data_type==RFC_SIMPLE_DATA:
            if hasattr(self.__value,'_decs_'):
                decs=self.__value._decs_
            else:
                decs=0
            odict['_data_def']=self.exid,self.length,decs
        elif self.data_type==RFC_STRUCTURE:
            odict['_data_def']=self.__value._field_defs_
        else:
            odict['_data_def']=self.__value.struc._field_defs_
        return odict
    def __setstate__(self,dict):
        data_def=dict['_data_def']
        del dict['_data_def']
        self.__dict__.update(dict)
        if self.data_type==RFC_SIMPLE_DATA:
            exid,lng,decs=data_def
            self.__value=SAP_MAP[exid](lng,decs)()
        elif self.data_type==RFC_STRUCTURE:
            self.__value=create_struct(data_def)()
            self.arg_typ=self.__value._type_handle_
        else:
            self.__value=create_table(self.name,data_def)
            self.arg_typ=self.__value.struc._type_handle_
    def __as_arg(self):
        return c.byref(self.__value)
    def __get_value(self):
        if hasattr(self.__value,'ext_value'): return self.__value.ext_value
        elif hasattr(self.__value,'int_value'): return self.__value.int_value
        elif hasattr(self.__value,'value'): return self.__value.value
        else: return self.__value
    def __set_value(self,v):
        if hasattr(self.__value,'ext_value'): self.__value.ext_value=v
        elif hasattr(self.__value,'int_value'): self.__value.int_value=v
        elif hasattr(self.__value,'value'): self.__value.value=v
        else: self.__value=v
    def __get_raw(self):
        return self.__value
    def reset(self):
        if self.data_type==RFC_TABLE:
            self.value.refresh()
        elif self.data_type==RFC_STRUCTURE:
            self.value=self.value.__class__()
        else:
            if self.exid=='X':
                self.value.reset()
            else:
                atr,v=SAP_INIT_VALUES[self.exid]
                setattr(self.__value,atr,v)
    as_arg=property(__as_arg)
    value=property(__get_value,__set_value)
    raw=property(__get_raw)
    
class RFC_ARGS:
    """
This class is a collection of parameters (see RFC_PARAM) defined by the function module interface. It's purpose
is to store parameters and to build data structures needed by remote function calls.
"""
    def __init__(self):
        self.params={}
        self.__stack=0
    def __getitem__(self,ky):
        ky=ky.upper()
        if not self.params[ky].active: raise ValueError('parameter %s is inactive' % ky)
        return self.params[ky].value
    def __setitem__(self,ky,v):
        ky=ky.upper()
        if self.params[ky].data_type==RFC_STRUCTURE:
            self.params[ky].reset()
            if isinstance(v,dict):
                self.params[ky].value.from_dict(v)
            elif isinstance(v,str):
                self.params[ky].value.from_string(v)
            elif issubclass(type(v),c.Structure):
                if v is not self.params[ky].value:
                    self.params[ky].value.from_structure(v)
            else:
                raise TypeError('inapropriate argument type %s for %s - dict, string or structure expected' % (type(v),ky))
        elif self.params[ky].data_type==RFC_TABLE:
            if isinstance(v,(list,tuple)):
                self.params[ky].value.refresh_fill(v)
            elif isinstance(v,ItTable):
                if v is not self.params[ky].value:
                    self.params[ky].value.refresh()
                    self.params[ky].value.append_from_table(v)
            else:
                raise TypeError('inapropriate argument type %s for %s - list, tuple or pysap.ItTable expected' % (type(v),ky))
        else:
            self.params[ky].value=v
    def __getstate__(self):
        odict=self.__dict__.copy()
        odict['_RFC_ARGS__stack']=0
        return odict
    def field(self,ky):
        return self.params[ky]
    def raw_value(self,ky):
        return self.params[ky].raw
    def add_param(self,p):
        self.params[p.name]=p
    def __num_params(self,typ):
        return len([p for p in self.params.values() if p.typ==typ and p.active])
    def __add_imports(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='E' and p.active]:
            RfcAddImportParam(self.__stack,i,ip.name,len(ip.name),ip.arg_typ,ip.length,ip.as_arg)
            i+=1
    def __add_exports(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='I' and p.active]:
            RfcAddExportParam(self.__stack,i,ip.name,len(ip.name),ip.arg_typ,ip.length,ip.as_arg)
            i+=1
    def __add_tables(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='T' and p.active]:
            RfcAddTable(self.__stack,i,ip.name,len(ip.name),ip.value.struc._type_handle_,ip.value.size,ip.value.handle)
            i+=1
    def __add_imports_srv(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='I']:
            RfcAddImportParam(self.__stack,i,ip.name,len(ip.name),ip.arg_typ,ip.length,ip.as_arg)
            i+=1
    def __add_exports_srv(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='E']:
            RfcAddExportParam(self.__stack,i,ip.name,len(ip.name),ip.arg_typ,ip.length,ip.as_arg)
            i+=1
    def __add_tables_srv(self):
        i=0
        for ip in [p for p in self.params.values() if p.typ=='T']:
            RfcAddTable(self.__stack,i,ip.name,len(ip.name),0,0,0)
            ip.arg_num=i # Store the argument number, we need this for RfcGetTableHandle
            i+=1
    def __add_all(self):
        self.__add_imports()
        self.__add_exports()
        self.__add_tables()
    def get_stack(self):
        if self.__stack:
            librfc.RfcFreeParamSpace(self.__stack)
        self.__stack=RfcAllocParamSpace(self.__num_params('I'),self.__num_params('E'),self.__num_params('T'))            
        self.__add_all()
        return self.__stack
    def get_stack_srv(self):
        if self.__stack:
            librfc.RfcFreeParamSpace(self.__stack)
        self.__stack=RfcAllocParamSpace(self.__num_params('E'),self.__num_params('I'),self.__num_params('T'))            
        self.__add_imports_srv()
        self.__add_tables_srv()
        return self.__stack
    def set_stack_srv(self):
        self.__add_exports_srv()
    def __del__(self):
        if self.__stack: librfc.RfcFreeParamSpace(self.__stack)
    def values(self):
        return self.params.values()
    def items(self):
        return self.params.items()
    def keys(self):
        return self.params.keys()
    def reset(self):
        for p in self.params.values():
            p.reset()
            
class RFC_FUNC(object):
    """
This class stores the function module interface. It's constructed from SAP function module by querrying
its interface using the get_interface method of the Rfc_connection. Arguments are stored in self.__args and
can be accesed as keys or attributes of the class. (func.kunnr.ext_value or func['kunnr'])
"""
    def __init__(self,hnd,func_name,args,desc=''):
        """
Do not instantiate RFC_FUNC directly. Use the get_interface method of Rfc_connection to get its interface
from SAP system.
"""
        self.name=func_name
        self.__args=args
        self.__handle=hnd
        self.desc=desc
        self.__results=None
        self.__arguments=None
    def __call__(self,*args,**kyw):
        """
Executes the remote function call in the SAP system passing all active arguments or if args is non-zero only
those arguments listed in args.
It raises SapRfcError on exceptions.
"""
        if not self.__handle:
            raise SapRfcError("can't perform RFC - no connection handle available")
        if self.__arguments is not None or self.__results is not None:
            self.set_all_active(0)
        if self.__arguments is not None:
            if len(self.__arguments)<len(args)+len(kyw):
                raise TypeError('%s expected at most %d arguments, got %d' % (self.name,len(self.arguments),len(args)+len(kyw)))
            for i in range(len(args)):
                self[self.__arguments[i]]=args[i]
                self.set_active(self.__arguments[i])
            for name,value in kyw.items():
                if name in self.__arguments:
                    self[name]=value
                    self.set_active(name)
                else:
                    raise TypeError("%s got unexpected keyword argument '%s'" % (self.name,name))
        else:
            if args:
                for p in self.__args.params.keys():
                    if p in args: self.set_active(p)
                    else: self.set_active(p,0)
            for name,value in kyw.items():
                self[name]=value
                self.set_active(name)
        if self.__results is not None:
            for p in self.__results:
                self.set_active(p)
        excep=c.c_buffer('',513)
        rc=RfcCallReceiveExt(self.__handle,self.__args.get_stack(),self.name,c.byref(excep))
        if rc:
#            err_info=RFC_ERROR_INFO_EX()
#            rc=librfc.RfcLastErrorEx(c.byref(err_info))
#            raise SapRfcError('%d - %s, %s' % (err_info.group,err_info.key,err_info.message))
            raise SapRfcError(excep.value)
        if self.__results is None:
            return rc
        elif self.__results==[]:
            return None
        else:
            rez=[self[p] for p in self.__results]
            if len(rez)==1:
                return rez[0]
            else:
                return [self[p] for p in self.__results]
    def __check_args(self,name,args,allowed):
        # Helper function for arguments and results setters
        if args is not None:
            if isinstance(args,(list,tuple)):
                for a in args:
                    if a.upper() not in allowed:
                        raise ValueError("unknown parameter '%s'" % a)
            else:
                raise TypeError('%s must be list or tuple' % name)
    def __get_arguments(self):
        return self.__arguments
    def __set_arguments(self,args):
        self.__check_args('arguments',args,self.imports()+self.tables())
        self.__arguments=args
    func_args=property(__get_arguments,__set_arguments)
    def __get_results(self):
        return self.__results
    def __set_results(self,results):
        self.__check_args('results',results,self.exports()+self.tables())
        self.__results=results
    func_res=property(__get_results,__set_results)
    def field(self,ky):
        """Access argument ky."""
        return self.__args.field(ky)
    def raw_value(self,ky):
        """Get raw value of argument ky."""
        return self.__args.raw_value(ky)
    def __getitem__(self,ky):
        return self.__args[ky]
    def __setitem__(self,ky,v):
        self.__args[ky]=v
    def __setstate__(self,dict):
        self.__dict__.update(dict)
        self.__handle=0 # invalidate handle
    def values(self):
        return self.__args.values()
    def items(self):
        return self.__args.items()
    def keys(self):
        return self.__args.keys()
    def args(self):
        return self.__args
    def imports(self):
        return [p.name for p in self.__args.params.values() if p.typ=='I']
    def exports(self):
        return [p.name for p in self.__args.params.values() if p.typ=='E']
    def tables(self):
        return [p.name for p in self.__args.params.values() if p.typ=='T']
    def set_active(self,ky,active=1):
        self.field(ky).active=active
    def set_all_active(self,active=1):
        """
Sets the status of all arguments to value of active (0 - inactive, 1 - active).
"""
        for arg in self.__args.values():
            arg.active=active
    def reset(self):
        """
Sets all arguments to their initial values.
"""
        self.__args.reset()
    def initialize(self):
        """
Initializes the arguments (sets them to initial values and then activates them).
"""
        self.reset()
        self.set_all_active()
    def reconnect(self,handle):
        self.__handle=handle
        
class RFC_SERV_FUNC(object):
    """
Subclass this class to implement server-side remote function (function that gets called from SAP system).
To implement function you have to:
1. set the _name_ attribute to function name
2. define at least one of _importing_, _exporting_, or _tables_ attributes
3. override the run method
4. optionally override the init_data method to initialize data
"""
    _name_=''
    _doc_=''
    def __init__(self,rel4=1):
        self.args=RFC_ARGS()
        self.connection=None
        self._rel4=rel4
    def __getitem__(self,ky):
        return self.args[ky]
    def __setitem__(self,ky,v):
        self.args[ky]=v
    def __split_def(self,data_def):
        name,typ,lng,decs=(tuple(data_def)+(0,0))[:4]
        if typ in ('I','g'): lng=c.sizeof(c.c_int)
        elif typ=='D': lng=8
        elif typ=='T': lng=6
        elif typ=='F': lng=c.sizeof(c.c_float)
        #else: lng=int(part1[1:])
        if typ!='P': decs=0
        return name,typ,lng,decs
    def __add_parameter(self,data_def,param_typ):
        if len(data_def)<2:
            raise ValueError('data definition must contain at last two items')
        if isinstance(data_def[1],str):
            name,typ,lng,decs=self.__split_def(data_def)
            value=SAP_MAP[typ](lng,decs)()
            p=RFC_PARAM(name,param_typ,typ,lng,RFC_SIMPLE_DATA,value,1)
        elif isinstance(data_def[1],(tuple,list)):
            name=data_def[0]
            value=create_struct(data_def[1])()
            p=RFC_PARAM(name,param_typ,' ',c.sizeof(value),RFC_STRUCTURE,value,1)
        else:
            raise ValueError('second item of data definition should be string or list')
        self.args.add_param(p)
       
    def __add_table(self,data_def):
        name,struc=data_def
        if isinstance(struc,(list,tuple)):
            struc=create_struct(struc)
        p=RFC_PARAM(name,'T',' ',c.sizeof(struc),RFC_TABLE,ItTable(name,struc),1)
        self.args.add_param(p)
        
    def _declare_data(self,handle):
        data_ok=0
        self.connection=Rfc_connection_serv(handle,self._rel4)
        if hasattr(self,'_interface_from_'):
            db,ky=self._interface_from_
            self.args=db[ky]
            return
        if hasattr(self,'_exporting_') and self._exporting_:
            data_ok=1
            for arg in self._exporting_:
                self.__add_parameter(arg,'E')
        if hasattr(self,'_importing_') and self._importing_:
            data_ok=1
            for arg in self._importing_:
                self.__add_parameter(arg,'I')
        if hasattr(self,'_tables_') and self._tables_:
            data_ok=1
            for arg in self._tables_:
                self.__add_table(arg)
        if data_ok==0:
            raise SyntaxError('function class must define at least one of _importing_, _exporting_, or _tables_ attributes')
        
    def init_data(self,handle):
        pass
    
    def _get_data(self,handle):
        self.stack=self.args.get_stack_srv()
        rc=librfc.RfcGetDataExt(handle,self.stack)
        if rc:
            librfc.RfcFreeParamSpace(self.stack)
            raise SapRfcError('error getting data')
        for arg in self.args.values():
            if arg.typ=='T':
                itab_handle=librfc.RfcGetTableHandle(self.stack,arg.arg_num)
                if itab_handle: arg.value.handle=itab_handle
                
    def run(self,handle):
        pass
    
    def _set_data(self,handle):
        self.args.set_stack_srv()
        rc=librfc.RfcSendDataExt(handle,self.stack)
        if rc:
            librfc.RfcFreeParamSpace(self.stack)
            raise SapRfcError('error setting data')
        
    def __get_func(self):
        def rf(handle):
            self._declare_data(handle)
            self.init_data(handle)
            try:
                self._get_data(handle)
            except SapRfcError:
                return 1
            try:
                self.run(handle)
            except SapFuncError,desc:
                rc=librfc.RfcRaise(handle,desc.value)
                librfc.RfcFreeParamSpace(self.stack)
                return 0
            try:
                self._set_data(handle)
            except SapRfcError:
                return 1
            librfc.RfcFreeParamSpace(self.stack)
            return 0
        return rf
    
    def __get_cfunc(self):
        rf=self.__get_func()
        return SAP_CALLBACK_FUNC(rf)
    
    def num_params(self):
        return len(self.args.items())
    
    f=property(__get_func)
    cf=property(__get_cfunc)

class Rfc_connection(object):
    """
This class connects to SAP system and keeps connection information. It provides methods to retrieve data
and structure descriptions from SAP system.
"""
    RFC_PARAMS_P40=create_struct((('paramclass','C',1),
                                  ('parameter','C',30),
                                  ('tabname','C',30),
                                  ('fieldname','C',30),
                                  ('exid','C',1),
                                  ('position','N',4),
                                  ('offset','N',6),
                                  ('intlength','N',6),
                                  ('decimals','N',6),
                                  ('default','C',21),
                                  ('paramtext','C',79)))
    RFC_PARAMS_P31=create_struct((('paramclass','C',1),
                                  ('parameter','C',30),
                                  ('tabname','C',10),
                                  ('fieldname','C',10),
                                  ('exid','C',1),
                                  ('position','N',4),
                                  ('offset','N',6),
                                  ('intlength','N',6),
                                  ('decimals','N',6),
                                  ('default','C',21),
                                  ('paramtext','C',79)))
    RFC_PARAMS_P=RFC_PARAMS_P40

    RFC_FIELDS_P40=create_struct((('tabname','C',30),
                                  ('fieldname','C',30),
                                  ('position','N',4),
                                  ('offset','N',6),
                                  ('intlength','N',6),
                                  ('decimals','N',6),
                                  ('exid','C',1)))
    RFC_FIELDS_P31=create_struct((('tabname','C',10),
                                  ('fieldname','C',10),
                                  ('position','N',4),
                                  ('offset','N',6),
                                  ('intlength','N',6),
                                  ('decimals','N',6),
                                  ('exid','C',1)))
    RFC_FIELDS_P=RFC_FIELDS_P40

    def __init__(self,conn_string='',conn_file='',conn_name='',rel4=1):
        """
See SAP documentation for information on the structure of connection string.
Some examples:
ASHOST=mysystem SYSNR=10 CLIENT=100 USER=hans PASSWD=geheim
ASHOST=/H/mysaprouter/H/theirsaprouter/H/theirsystem SYSNR=10 CLIENT=100 USER=hans PASSWD=geheim (if you need
sap router to connect to the SAP R/3)
You can also use an .ini file to store connection information for better
security. In that case set the conn_file to location of the .ini file and conn_name to the name of the connection
(if your .ini file supports several connections). If conn_name is not set, first connection found is used (this is
not neccesarally the first connection specied in the .ini file).
Note: conn_string and conn_file are muttally exclusive. If both are given, conn_string takes precedence and conn_file
is ignored.
rel4: 1 - the remote system is R/3 v4 or higher, 0 - remote system is R/3 v3.1, default 1.
"""
        self.conn_file=conn_file
        self.conn_name=conn_name
        if conn_string:
            self.conn_string=conn_string
        elif conn_file:
            self.conn_string=self.__read_config()
        self.__set_release(rel4)
        self.__handle=0
        self._f_table=None

    def __set_release(self,rel4):        
        self.rel4=rel4
        if rel4:
            self.RFC_PARAMS_P=self.RFC_PARAMS_P40
            self.RFC_FIELDS_P=self.RFC_FIELDS_P40
        else:
            self.RFC_PARAMS_P=self.RFC_PARAMS_P31
            self.RFC_FIELDS_P=self.RFC_FIELDS_P31
        
    def __read_config(self):
        import ConfigParser
        cfgp=ConfigParser.ConfigParser()
        cfgp.read(self.conn_file)
        if not self.conn_name:
            self.conn_name=cfgp.sections()[0]
        conn_string=''
        for o in cfgp.options(self.conn_name):
            conn_string+='%s=%s ' % (o.upper(),cfgp.get(self.conn_name,o))
        return conn_string
    
    def __get_handle(self):
        return self.__handle
    handle=property(__get_handle)            
    def open(self,conn_string='',conn_file='',conn_name='',rel4=None):
        """
Connects to the SAP system. Raises SapRfcError on connection errors. If given conn_string overrides connection
string specified in the __init__. You can also use an .ini file to store connection information for better
security. In that case set the conn_file to location of the .ini file and conn_name to the name of the connection
(if your .ini file supports several connections). If conn_name is not set, first connection found is used (this is
not neccesarally the first connection specied in the .ini file).
Note: conn_string and conn_file are muttally exclusive. If both are given, conn_string takes precedence and conn_file
is ignored.
rel4: 1 - the remote system is R/3 v4 or higher, 0 - remote system is R/3 v3.1, default 1.
"""
        if conn_string: self.conn_string=conn_string
        elif conn_file or conn_name:
            if conn_file: self.conn_file=conn_file
            self.conn_name=conn_name
            self.conn_string=self.__read_config()
        if rel4 is not None:
            self.__set_release(rel4)
        err_info=RFC_ERROR_INFO_EX()
        self.__handle=RfcOpenEx(self.conn_string,c.byref(err_info))
        if not self.__handle:
            raise SapRfcError('%d - %s\n%s' % (err_info.group,err_info.key,err_info.message))
    def get_interface(self,f_name,include_desc=1,func_args=None,func_res=None):
        """
Get the function module interface form the system. Returns a RFC_FUNC instance or raises SapRfcError.
f_name - function module name as specified by SAP
include_desc - include the description of the function interface (see fields desc and desc_obj of resulting RFC_FUNC instance)
 (see also Rfc_connection.get_interface_desc).
You can set this to False if you don't need description of the interface for small perfomance boost (untested).
"""
        if not self.handle: raise SapRfcError('Not connected')
        funcname=XCHAR(30)()
        funcname.ext_value=f_name
        params_p=ItTable('params_p',self.RFC_PARAMS_P)
        excep=XCHAR(513)()
        excep.ext_value=''
        stack=RfcAllocParamSpace(1,0,1)
        RfcAddExportParam(stack,0,'FUNCNAME',8,0,30,funcname)
        RfcAddTable(stack,0,'PARAMS_P',8,0,params_p.size,params_p.handle)
        rc=RfcCallReceiveExt(self.handle,stack,'RFC_GET_FUNCTION_INTERFACE_P',excep)
        if rc:
            err_info=RFC_ERROR_INFO_EX()
            rc=librfc.RfcLastErrorEx(c.byref(err_info))
            if err_info.key==err_info.message:
                raise SapRfcError('%d - %s') % (err_info.group,err_info.key)
            else:
                raise SapRfcError('%d - %s, %s' % (err_info.group,err_info.key,err_info.message))
        else:
            args=RFC_ARGS()
            if include_desc:
                desc_obj=self.get_interface_desc(f_name)
                desc=str(desc_obj)
            else:
                desc_obj=None
                desc=''
            ## if include_desc: desc='%-10s%-30s%3s%10s%10s %-29s\n%s\n' % ('Mode','Name','Typ','Length','Decimals','Default','Description')
            for p in params_p:
                ## if include_desc: desc+=self._interface_desc(p)+'\n'
                if p['paramclass']!='X': #exclude exception definitions
                    data_typ=RFC_SIMPLE_DATA
                    if p['tabname'] and not p['fieldname'] and p['exid'].strip() not in SAP_MAP.keys():
                        if p['paramclass']=='T':
                            gen_param=self.get_table(p['tabname'])
                            data_typ=RFC_TABLE
                        else:
                            gen_param=self.get_structure(p['tabname'])()
                            data_typ=RFC_STRUCTURE
                    else:
                        gen_param=SAP_MAP[p['exid']](p['intlength'],p['decimals'])()
                    args.add_param(RFC_PARAM(p['parameter'],p['paramclass'],p['exid'],p['intlength'],data_typ,gen_param))
            func=RFC_FUNC(self.handle,f_name,args,desc)
            func.func_args=func_args
            func.func_res=func_res
            func.desc_obj=desc_obj
        librfc.RfcFreeParamSpace(stack)
        return func
##    def _interface_desc(self,p):
##        desc='%-10s' % {'I':'Importing ','E':'Exporting ','T':'Table ','X':'Exception '}[p['paramclass']]
##        desc+='%-30s' % p['parameter']
##        if p['paramclass']!='X':
##            desc+='%(exid)3s%(intlength)10d%(decimals)10d %(default)-29s' % p
##            if p['paramtext']: desc+='\n#%s#' % p['paramtext']
##        return desc
    def get_interface_desc(self,funcname,lang=None,stext=''):
        """
Unlike Rfc_connection.get_interface this method fetches interface description only and stores it in
a description object (FuncDesc).
Usefull for documentation purposes.
funcname - name of the function,
lang - language,
stext - short text describing the function
returns description object (an instance of class FuncDesc) 
"""
        class ParamDesc:
            def __init__(self,p1):
                self.name=p1['parameter']
                self.typ=p1['paramclass']
                if p1['paramclass']!='X':
                    self.field_def=('%(tabname)s-%(fieldname)s' % p1).strip(' -')
                    self.size=p1['intlength']
                    self.decs=p1['decimals']
                    self.exid=p1['exid']
                    self.text=p1['paramtext']
                    try:
                        self.optional=p1['optional']=='X'
                    except KeyError:
                        self.optional=1==0
                    self.default=p1['default']
            def __str__(self):
                if self.typ=='X':
                    return self.name
                else:
                    if self.exid=='P':
                        txt='%s LIKE %s (%s%d.%d)' % (self.name,self.field_def,self.exid,self.size,self.decs)
                    elif self.exid in ('C','N','X'):
                        txt='%s LIKE %s (%s%d)' % (self.name,self.field_def,self.exid,self.size)
                    else:
                        txt='%s LIKE %s (%s)' % (self.name,self.field_def,self.exid)
                    if self.optional:
                        txt=txt+', optional'
                    if self.default:
                        txt=txt+', default = %s' %self.default
                    return txt
                    
        class FuncDesc:
            def __init__(self,funcname,stext):
                self.funcname=funcname
                self.text=stext
                self.imports=[]
                self.exports=[]
                self.tables=[]
                self.exceptions=[]
                self.__map={'I':self.imports,
                            'E':self.exports,
                            'T':self.tables,
                            'X':self.exceptions}
            def append(self,p1):
                paramclass=p1['paramclass']
                if self.__map.has_key(paramclass):
                    self.__map[paramclass].append(ParamDesc(p1))
            def __str__(self):
                txt='%-30s %s\n' % (self.funcname,self.text)
                map={'I':'Importing','E':'Exporting','T':'Tables','X':'Exceptions'}
                for typ in ('I','E','T','X'):
                    if self.__map[typ]:
                        txt+='\t'+map[typ]+'\n'
                        for p in self.__map[typ]:
                            txt+='\t\t%s\n' % p
                            if p.typ!='X' and p.text:
                                txt+='\t\t * %s\n' % p.text
                return txt[:-1]
            
        if not self.handle: raise SapRfcError('Not connected')
        f=self.get_interface('RFC_GET_FUNCTION_INTERFACE_P',0,func_args=['FUNCNAME','LANGUAGE'],func_res=['PARAMS_P'])
        if lang: params=f(funcname,lang)
        else: params=f(funcname)
        rez=FuncDesc(funcname,stext)
        for p in params:
            rez.append(p)
        return rez
    def make_py_func(self,funcname,include_doc=0,func_args=None,func_res=None,convert_res=0):
        f=self.get_interface(funcname,include_doc)
        if func_args is None:
            func_args=f.imports()+f.tables()
        if func_res is None:
            func_res=f.exports()+f.tables()
        f.func_args=func_args
        f.func_res=func_res
        
        def py_rfc_func(**kw):
            f.reset()
            for ky,value in kw.items():
                if ky not in f.func_args:
                    raise TypeError("%s() got an unexpected keyword argument '%s'" % (funcname,ky))
            if convert_res:
                rez=f(**kw)
                if not isinstance(rez,(list,tuple)):
                    rez=[rez]
                ret=[]
                for i in range(len(rez)):
                    ky=func_res[i]
                    dtype=f.field(ky).data_type
                    if dtype==RFC_STRUCTURE:
                        ret.append(rez[i].to_dict())
                    elif dtype==RFC_TABLE:
                        ret.append(rez[i].to_list())
                    else:
                        ret.append(rez[i])
                if len(ret)==1: ret=ret[0]
                return ret
            else:
                return f(**kw)
            
        if include_doc:
            py_rfc_func.__doc__=f.desc
        py_rfc_func.rfc_args=func_args
        py_rfc_func.rfc_res=func_res
        return py_rfc_func
    def search_functions(self,funcname,grpname='',lang=None,names_only=0):
        srch_func=self.get_interface('RFC_FUNCTION_SEARCH',0,func_args=['FUNCNAME','GROUPNAME','LANGUAGE'],func_res=['FUNCTIONS'])
        try:
            funcs=srch_func(funcname,grpname,lang)
        except SapRfcError:
            return []
        else:
            if names_only:
                return [f['funcname'] for f in funcs]
            else:
                return funcs
    def get_fieldlist(self,s_name,*flds):
        """
Returns a list of field definitions suitable to pass to the create_struct function.
s_name - name of the structure or permanent table in DDIC.
flds - if non-zero include only fields listed in flds
"""
        if not self.handle:
            raise SapRfcError('Not connected')
        structname=XCHAR(30)()
        structname.ext_value=s_name
        params_p=ItTable('fields_p',self.RFC_FIELDS_P)
        excep=XCHAR(513)()
        excep.ext_value=''
        stack=RfcAllocParamSpace(1,0,1)
        RfcAddExportParam(stack,0,'TABNAME',7,0,30,structname)
        RfcAddTable(stack,0,'FIELDS',6,0,params_p.size,params_p.handle)
        rc=RfcCallReceiveExt(self.handle,stack,'RFC_GET_STRUCTURE_DEFINITION_P',excep)
        if rc:
            err_info=RFC_ERROR_INFO_EX()
            rc=librfc.RfcLastErrorEx(c.byref(err_info))
            raise SapRfcError('%d - %s\n%s' % (err_info.group,err_info.key,err_info.message))
        else:
            fld_lst=[]
            if flds: flds=[fld.lower() for fld in flds]
            for p in params_p:
                p['fieldname']=p['fieldname'].lower()
                if not flds or p['fieldname'] in flds:
                    fld_lst.append((p['fieldname'],p['exid'],p['intlength'],p['decimals']))
            if flds:
                def fld_comp(fld1,fld2):
                    return cmp(flds.index(fld1[0]),flds.index(fld2[0]))
                fld_lst.sort(fld_comp)
        librfc.RfcFreeParamSpace(stack)
        return fld_lst
    def get_fielddict(self,s_name,*flds):
        """Similar to get_fieldlist but returns a dictionary of field_name,field_definition pairs instead of a list."""
        rez={}
        for fld in self.get_fieldlist(s_name,*flds):
            rez[fld[0]]=fld
        return rez
    def get_structure(self,s_name,*flds):
        """Similar ot get_fieldlist, this one returns an instance of STRUCT object (see source of create_structure)."""
        return create_struct(self.get_fieldlist(s_name,*flds))
    def get_table(self,t_name,inttab_name=''):
        """Creates an ItTable instance using structure data from DDIC.
tname - table name from DDIC
inttab_name - internal table name, see ItTable
"""
        if not inttab_name: inttab_name=t_name 
        return ItTable(inttab_name,self.get_structure(t_name))
    def read_table(self,t_name,options=[],fields=[],max_rows=0,from_row=0):
        """
Reads data from SAP transparent tables using RFC_READ_TABLE. Use the source of this method as an example
of how to create and use RFC_FUNC.
Method returns ItTable instance.
t_name - table name (defined in DDIC)
options - parts of WHERE clause, length of single item must be equal or less than 72
fields - list of fields
max_rows - max number of rows returned
from_row - row to start with
"""
        if self._f_table:
            f_table=self._f_table
            f_table.initialize()
        else:
            self._f_table=f_table=self.get_interface('RFC_READ_TABLE')
        table_struct=self.get_structure(t_name,*fields)
        f_table['QUERY_TABLE']=t_name
        if from_row: f_table['ROWSKIPS']=from_row
        else: f_table.set_active('ROWSKIPS',0)
        f_table.set_active('NO_DATA',0)
        if max_rows: f_table['ROWCOUNT']=max_rows
        else: f_table.set_active('ROWCOUNT',0)
        if options:
            opt_tab=f_table['OPTIONS']
            for o in options:
                opt_tab.append_from_list([o])
        else: f_table.set_active('OPTIONS',0)
        if fields:
            fld_tab=f_table['FIELDS']
            fld_lin=fld_tab.struc()
            for fld in fields:
                fld_lin['fieldname']=fld.upper()
                fld_tab.append(fld_lin)
        else: f_table.set_active('FIELDS',0)
        f_table['DELIMITER']='\t'
        rc=f_table()
        rez=ItTable(t_name,table_struct)
        for d in f_table['DATA']:
            try:
                rez.append_from_list(d['wa'].split('\t'))
            except:
                pass
        return rez
    def exec_abap(self,prog_lines,mode='F',program_name='<<RFC1>>'):
        """
Execute abap program defined in prog_lines and return its writes as ItTable instance.
Raises SapRfcError on errors.
prog_lines can be string or list of lines.
Uses RFC_ABAP_INSTALL_AND_RUN.
"""
        def wwrap(txt,lngth):
            # Helper function to split program lines if neccesary
            # Maximum line length allowed by RFC_ABAP_INSTALL_AND_RUN is 72 characters
            rez=[]
            txt=txt.split('"')[0]
            # Try to handle comment lines correctly
            first_char=txt[0]=='*' and '*' or ''
            while 1:
                if len(txt)<=lngth:
                    rez.append(txt)
                    break
                else:
                    ind=txt[:lngth].rfind(' ')
                    if ind==-1:
                        rez.append(txt[:lngth])
                        txt=first_char+txt[lngth:]
                    else:
                        rez.append(txt[:ind])
                        txt=first_char+txt[ind+1:]
            return rez
        
        if isinstance(prog_lines,(str,unicode)):
            prog_lines=prog_lines.split(os.linesep)
        f=self.get_interface('RFC_ABAP_INSTALL_AND_RUN')
        f['MODE']=mode
        f['PROGRAMNAME']=program_name
        for l in prog_lines:
            for l1 in wwrap(l,72):
                f['PROGRAM'].append_from_list([l1])
        f()
        if f['ERRORMESSAGE']:
            raise SapRfcError(f['ERRORMESSAGE'])
        return f['WRITES']
    def exec_abap_file(self,f,mode='F',program_name='<<RFC1>>'):
        """
Executes abap program from file f. f can be string or file object.
See also Rfc_connection.exec_abap
"""
        if isinstance(f,(str,unicode)):
            f=open(f)
        return self.exec_abap(f.read(),mode,program_name)
    def close(self):
        """Closes connection."""
        try:
            if self.__handle: librfc.RfcClose(self.__handle)
        except:
            pass
        self.__handle=0
    def __del__(self):
        self.close()
        
class Rfc_connection_serv(Rfc_connection):
    """
Subclass of Rfc_connection to be used by RFC_SERV_FUNC for calling RFC functions from
SAP. Do not instantiate this class directly."""
    def __init__(self,handle,rel4=1):
        self.__set_release(rel4)
        self.__handle=handle
        self._f_table=None
        
    def __set_release(self,rel4):        
        self.rel4=rel4
        if rel4:
            self.RFC_PARAMS_P=self.RFC_PARAMS_P40
            self.RFC_FIELDS_P=self.RFC_FIELDS_P40
        else:
            self.RFC_PARAMS_P=self.RFC_PARAMS_P31
            self.RFC_FIELDS_P=self.RFC_FIELDS_P31
        
    def __get_handle(self):
        return self.__handle
    
    handle=property(__get_handle)
    
    def open(self):
        # We're using an already opened connection - no additional actions needed
        pass
    
    def close(self):
        # We're not owners of the connection therefore we can't close it
        pass
        
##class RfcServer:
##    """
##SAP RFC server implementation - supports the simplest way to define remote server.
##To implement RFC server:
##1. subclass RFC_SERV_FUNC to define function(s) to be exported
##2. call the register_func method to register function with the server
##3. call the main_loop passing it sys.argv to start the server
##In SAP system use the SM59 transaction to define remote destination (TCP/IP) and register your program
##with SAP.
##This implementation is currently broken. Please use RfcServerEx instead.
##"""
##    def __init__(self,rel4=1):
##        self.__funcs={}
##        self.__rel4=rel4
##    def register_func(self,func_obj):
##        """
##Registers function produced by subclassing the RFC_SERV_FUNC with the server. Pass it a RFC_SERV_FUNC subclass
##(class itself not the instance thereof) as argument. Raises SapRfcError on errors.
##"""
##        c_doc=c.c_char_p(func_obj._doc_)
##        rfc_func=func_obj(self.__rel4)
##        RfcInstallFunction=librfc.RfcInstallFunction
##        RfcInstallFunction.restype=c.c_int
##        RfcInstallFunction.argtypes=(c.c_char_p,SAP_CALLBACK_FUNC,c.c_char_p)
##        rc=RfcInstallFunction(func_obj._name_,rfc_func.cf,c_doc)
##        if rc:
##            raise SapRfcError('error registering function %s' % func_obj._name_)
##        self.__funcs[func_obj._name_]=(rfc_func,c_doc)
##    def main_loop(self,argv):
##        """Pass sys.argv as argument to this function."""
##        import time
##        args=' '.join(argv[1:])
##        handle=librfc.RfcAcceptExt(args)
##        if handle==0:
##            raise SapRfcError('connection failed')
##        while 1:
##            rc=librfc.RfcDispatch(handle)
##            if rc:
##                break
##            time.sleep(1)
##        rc=librfc.RfcClose(handle)        

class RfcServerEx:
    """
Alternative SAP RFC server implementation - uses RfcGetName instead of RfcInstallFunction.
To implement RFC server:
1. subclass RFC_SERV_FUNC to define function(s) to be exported
2. call the register_func method to register function with the server
3. call the main_loop passing it sys.argv to start the server
In SAP system use the SM59 transaction to define remote destination (TCP/IP) and register your program
with SAP.
Note: The length of function name is limited to 30 chars (RfcGetName limitation).
"""
    def __init__(self,rel4=1):
        self.__funcs={}
        self.__rel4=rel4
    def register_func(self,func_obj):
        """
Registers function produced by subclassing the RFC_SERV_FUNC with the server. Pass it a RFC_SERV_FUNC subclass
(class itself not the instance thereof) as argument.
"""
        self.__funcs[func_obj._name_]=func_obj
    def main_loop(self,argv):
        """Pass sys.argv as argument to this function."""
        import time
        args=' '.join(argv[1:])
        handle=librfc.RfcAcceptExt(args)
        err=0
        if handle==0:
            raise SapRfcError('connection failed')
        while 1:
            c_func_name=c.c_buffer(30)
            rc=librfc.RfcGetNameEx(handle,c.byref(c_func_name))
            if rc==0: # RFC_OK
                func_name=c_func_name.value
                if self.__funcs.has_key(func_name):
                    func_obj=self.__funcs[func_name](self.__rel4)
                    func_rc=func_obj.f(handle)
                    if func_rc:
                        break
                else:
                    librfc.RfcAbort(handle,'Function %r not found' % func_name)
                    err=1
                    break
            elif rc==17: # RFC_SYSTEM_CALLED
                continue
            elif rc==6: # RFC_CLOSED
                break
            else: # Error
                raise SapRfcError('RFC server error, rc = %d' % rc)
            time.sleep(1)
        if err==0: rc=librfc.RfcClose(handle)

RfcServer=RfcServerEx        
        
class BaseSapRfcError(Exception):
    def __init__(self,value):
        self.value=value
    def __str__(self):
        return `self.value`

class SapRfcError(BaseSapRfcError):
    pass

class SapFuncError(BaseSapRfcError):
    pass

class RFC_ERROR_INFO_EX(c.Structure):
    _fields_=[('group',c.c_int),
              ('key',STRING(33)),
              ('message',STRING(513))]

class RFC_PARAM_STACK(c.Structure):
    _fields_=[('MaxNo',c.c_int),('Params',c.c_voidp)]

class RFC_PARAMETER_ADMIN(c.Structure):
    _fields_=[('Exports',RFC_PARAM_STACK),
              ('Imports',RFC_PARAM_STACK),
              ('Tables',RFC_PARAM_STACK)]

RFC_PARAM_SPACE=c.POINTER(RFC_PARAMETER_ADMIN)

RfcOpenEx=librfc.RfcOpenEx
RfcOpenEx.argtypes=[c.c_char_p,c.POINTER(RFC_ERROR_INFO_EX)]
RfcOpenEx.restype=c.c_int
RfcAllocParamSpace=librfc.RfcAllocParamSpace
RfcAllocParamSpace.argtypes=[c.c_uint,c.c_uint,c.c_uint]
RfcAllocParamSpace.restype=RFC_PARAM_SPACE
RfcAddExportParam=librfc.RfcAddExportParam
RfcAddImportParam=librfc.RfcAddImportParam
RfcAddTable=librfc.RfcAddTable
RfcCallReceiveExt=librfc.RfcCallReceiveExt
