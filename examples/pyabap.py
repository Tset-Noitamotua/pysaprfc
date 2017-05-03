import pysap
import os

"""Support module for exec_abap. Experimental. May become part of the pysaprfc package in the future."""

def struct_to_abap(name,pysap_struct,as_string=0,is_table=0,tab_lines=0):
        lines=[]
        if is_table:
                lines.append('data: begin of %s occurs %d,' % (name,tab_lines))
        else:
                lines.append('data: begin of %s,' % name)
        for fld in pysap_struct._sfield_names_:
                typ=pysap_struct.sap_type(fld)
                if typ in ('s','b'): typ='I'
                if typ in ('I','F','D','T'):
                        lines.append('      %s type %s,' % (fld,typ))
                elif typ=='P':
                        lines.append('      %s(%d) type %s decimals %d,' % (fld,pysap_struct.sap_len(fld),typ,pysap_struct.sap_decs(fld)))
                else:
                        lines.append('      %s(%d) type %s,' % (fld,pysap_struct.sap_len(fld),typ))
        lines.append('      end of %s.' % name)
        if as_string:
                return os.linesep.join(lines)
        else:
                return lines
        
def struct_values_to_abap(name,pysap_struct,as_string=0,tabs=''):
        lines=[]
        for fld in pysap_struct._sfield_names_:
                if pysap_struct.sap_type(fld) in ('D','T'):
                        v=getattr(pysap_struct,fld).int_value
                else:
                        v=pysap_struct[fld]
                if not v:
                        v=pysap.SAP_INIT_VALUES.get(pysap_struct.sap_type(fld),('',''))[1]
                if isinstance(v,int):
                        lines.append(tabs+'%s-%s = %d.' % (name,fld,v))
                else:
                        lines.append(tabs+"%s-%s = '%s'." % (name,fld,v))
        if as_string:
                return os.linesep.join(lines)
        else:
                return lines
        
def abap_output_struct_values(name,pysap_struct,as_string=0,tabs=''):
        lines=[]
        for fld in pysap_struct._sfield_names_:
                typ=pysap_struct.sap_type(fld)
                if typ in ('I','P','F','N','s','b'):
                        msk='no-grouping'
                        out_len=''
                elif typ=='D':
                        msk='DD/MM/YYYY no-zero'
                        out_len='(10)'
                else:
                        msk=''
                        out_len=''
                lines.append(tabs+"write: / '%s-%s = ', %s%s-%s %s." % (name,fld,out_len,name,fld,msk))
        if as_string:
                return os.linesep.join(lines)
        else:
                return lines
        
def itab_values_to_abap(pysap_itab,as_string=0,tabs=''):
        lines=[]
        for wa in pysap_itab:
                lines+=struct_values_to_abap(pysap_itab.name,wa,tabs=tabs)
                lines.append(tabs+'append %s.' % pysap_itab.name)
        if as_string:
                return os.linesep.join(lines)
        else:
                return lines
        
def abap_output_itab_values(pysap_itab,as_string=0,tabs='',where_str='',from_line=None,to_line=None):
        head=(tabs+'loop at %s '+where_str) % pysap_itab.name
        if from_line:
                head+=' from %d' % from_line
        if to_line:
                head+=' to %d' % to_line
        head+='.'
        lines=[head]
        lines.append(tabs+"  write: / 'begin record'.")
        lines+=abap_output_struct_values(pysap_itab.name,pysap_itab.struc,tabs=tabs+'  ')
        lines.append(tabs+"  write: / 'end record'.")
        lines.append(tabs+'endloop.')
        if as_string:
                return os.linesep.join(lines)
        else:
                return lines
                
class SelRange(object):
        def __init__(self,conn,name,struct_name,fld_name):
                self.__conn=conn
                self.name=name
                self.struct_name=struct_name
                self.fld_name=fld_name
                fld_def=conn.get_fieldlist(struct_name,fld_name)[0][1:]
                struct=pysap.create_struct([('sign','C',1),('option','C',2),('low',)+fld_def,('high',)+fld_def])
                self.__itab=pysap.ItTable(name,struct)
        def append_cond(self,sign,option,low,high=None):
                if sign.upper() not in ('I','E'):
                        raise ValueError("sign must be either 'I' or 'E'")
                option={'<':'LT','<=':'LE','=<':'LE','=':'EQ','==':'EQ','<>':'NE','><':'NE','!=':'NE',
                        '>':'GT','>=':'GE','=>':'GE'}.get(option,option)
                self.__itab.append_from_list((sign,option,low,high))
        def header(self,as_string=0,tabs=''):
                v=tabs+'ranges %s for %s-%s.' % (self.name,self.struct_name,self.fld_name)
                if as_string: return v
                else: return [v]
        def table_def(self,as_string=0,tab_lines=0):
                return struct_to_abap(self.name,self.__itab.struc,as_string,is_table=1,tab_lines=tab_lines)
        def body(self,as_string=0,tabs=''):
                return itab_values_to_abap(self.__itab,as_string,tabs)
        def reset(self):
                self.__itab.refresh()
        def __get_itab(self):
                return self.__itab
        cond_table=property(__get_itab)
        
class Select(object):
        def __init__(self,conn,table_name,pysap_itab,sel_fields=[],sort_fields=[],from_line=None,to_line=None):
                self.__conn=conn
                self.table_name=table_name
                self.__itab=pysap_itab
                self.sel_ranges={}
                self.sort_fields=sort_fields
                self.from_line,self.to_line=from_line,to_line
                i=0
                for fld in sel_fields:
                        self.sel_ranges[fld]=SelRange(conn,'range%03d' % i,table_name,fld)
                        i+=1
        def append_cond(self,fld,sign,option,low,high=None):
                self.sel_ranges[fld].append_cond(sign,option,low,high)
        def get_abap(self,as_string=0,tabs=''):
                lines=[]
                lines+=struct_to_abap(self.__itab.name,self.__itab.struc,is_table=1)
                lines.append('')
                for v in self.sel_ranges.values():
                        lines+=v.header(tabs=tabs)
                lines.append('')
                for v in self.sel_ranges.values():
                        lines+=v.body()
                        lines.append('')
                lines.append(tabs+'select * into corresponding fields of table %s from %s' % (self.__itab.name,self.table_name))
                where_cl=[]
                for v in self.sel_ranges.values():
                        where_cl.append('%s in %s' % (v.fld_name,v.name))
                is_first=1
                for l in where_cl:
                        if is_first:
                                lines.append(tabs+'  where '+l)
                                is_first=0
                        else: lines.append(tabs+'  and '+l)
                if self.sort_fields:
                        lines.append(tabs+'  order by')
                        for fld in self.sort_fields:
                                lines.append(tabs+'    '+fld)
                lines.append(tabs+'.')
                lines.append('')
                lines.append("set country 'US'.")
                lines.append('')
                lines+=abap_output_itab_values(self.__itab,tabs=tabs,from_line=self.from_line,to_line=self.to_line)
                if as_string:
                        return os.linesep.join(lines)
                else:
                        return lines
        def __call__(self,append=0):
                rez=self.__conn.exec_abap(['report zpysel.','']+self.get_abap())
                if not append: self.__itab.refresh()
                fld_dict={}
                for wa in rez:
                        l=wa['zeile']
                        if l=='begin record':
                                fld_dict={}
                        elif l=='end record':
                                self.__itab.append_from_dict(fld_dict)
                        else:
                                try:
                                        fld,v=l.split(' =')
                                        fld=fld.split('-')[1]
                                        fld_dict[fld]=v.strip()
                                except:
                                        print 'Error: %s!' % l
                return self.__itab
        def reset_conds(self):
                for v in self.sel_ranges.values():
                        v.reset()
        def __get_itab(self):
                return self.__itab
        itab=property(__get_itab)
