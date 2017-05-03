import unittest
import pysap
import ctypes

def create_struct1():
    flds=[('desc','C',20),('val1','N',10),('val2','N',5)]
    return pysap.create_struct(flds)
def create_struct2():
    return pysap.create_struct([('line','C',35)])
def create_struct3():
    flds=[('desc','C',25),('val2','N',5),('val3','N',10)]
    return pysap.create_struct(flds)
def to_upper(obj,v):
    return v.upper()

class StructureTestCase(unittest.TestCase):
    def test_creation(self):
        S1=create_struct1()
        s1=S1()
        self.failUnless(ctypes.sizeof(s1)==35)
        self.failUnless(isinstance(s1['desc'],str))
        self.failUnless(isinstance(s1['val1'],int))
        self.failUnless(s1.sap_def('desc')=='C20')
        self.failUnless(s1.sap_def('val1')=='N10')
        self.failUnless(s1.sap_def('val2')=='N5')
    def test_from_list(self):
        s1=create_struct1()()
        s1.from_list(['test 1',500,15])
        self.failUnless(s1['desc']=='test 1')
        self.failUnless(s1['val1']==500)
        self.failUnless(s1['val2']==15)
    def test_from_struct(self):
        s1=create_struct1()()
        s2=create_struct2()()
        s2['line']='%-20s%010d%05d' % ('Test 2',800,20)
        s1.from_structure(s2)
        self.failUnless(s1['desc']=='Test 2')
        self.failUnless(s1['val1']==800)
        self.failUnless(s1['val2']==20)
    def test_from_dict(self):
        s1=create_struct1()()
        s1.from_dict({'val1':500,'val2':10,'desc':'Test 3'})
        self.failUnless(s1['desc']=='Test 3')
        self.failUnless(s1['val1']==500)
        self.failUnless(s1['val2']==10)
    def test_copy_corresp(self):
        s1=create_struct1()()
        s3=create_struct3()()
        s3['desc']='0123456789012345678901234'
        s3['val2']=100
        s3['val3']=50
        s1['desc']='test'
        s1['val1']=500
        s1['val2']=250
        s1.copy_corresp_from(s3)
        self.failUnless(s1['desc']=='01234567890123456789')
        self.failUnless(s1['val1']==500)
        self.failUnless(s1['val2']==100)
        s1['desc']='test'
        s1['val1']=500
        s1['val2']=250
        s1.copy_corresp_from(s3,'desc')
        self.failUnless(s1['desc']=='01234567890123456789')
        self.failUnless(s1['val1']==500)
        self.failUnless(s1['val2']==250)
    def test_equal(self):
        from operator import __eq__
        s1=create_struct1()()
        s2=create_struct2()()
        s2['line']='%-20s%010d%05d' % ('Test 2',800,20)
        s1.from_structure(s2)
        self.failUnless(s1==s2)
        self.failUnless(s1.is_equal(s2))
        s1['desc']='Test 3'
        self.failUnless(s1!=s2)
        self.assertRaises(TypeError,__eq__,s1,s2['line'])
        s3=create_struct1()()
        s3.from_list(('Test',800,20))
        self.failUnless(s1.is_equal(s3,'val1','val2'))
        self.failUnless(s1.is_equal(s3,'val1'))
    def test_string(self):
        s1=create_struct1()()
        line='%-20s%010d%05d' % ('Test 2',800,20)
        s1.from_string(line)
        self.failUnless(s1['desc']=='Test 2')
        self.failUnless(s1['val1']==800)
        test_str=s1.to_string(4)
        self.failUnless(test_str=='Test')
        test_str=s1.to_string(8)
        self.failUnless(test_str[4:]==' 2  ')
    def test_size(self):
        s1=create_struct1()()
        self.failUnless(len(s1)==35)
    def test_conversion(self):
        S1=create_struct1()
        s1=S1()
        s1.set_conversion('desc',to_upper)
        s1['desc']='abcd'
        self.failUnless(s1['desc']=='ABCD')
        self.failUnless(s1.desc.int_value[:4]=='ABCD')
        self.failUnless('desc' in S1._sfield_convs_)
        s1.set_conversion('desc',None,to_upper)
        s1['desc']='abcd'
        self.failUnless(s1['desc']=='ABCD')
        self.failUnless(s1.desc.int_value[:4]=='abcd')        
        self.failUnless('desc' in S1._sfield_convs_)
        s1.set_conversion('desc',out_conv=None)
        s1['desc']='wxyz'
        self.failUnless(s1['desc']=='wxyz')
        self.failUnless(s1.desc.int_value[:4]=='wxyz')        
        self.failUnless(S1._sfield_convs_=={})


def get_suite():
    return unittest.makeSuite(StructureTestCase)

def test(verbose=0):
    runner = unittest.TextTestRunner(verbosity=verbose)
    runner.run(get_suite())

if __name__ == '__main__':
    unittest.main()
