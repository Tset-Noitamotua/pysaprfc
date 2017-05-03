import unittest
import pysap
import ctypes

def to_upper(obj,v):
    return v.upper()

class SimpleDataTestCase(unittest.TestCase):
    def test_char(self):
        val1=pysap.create_simple('C',10)
        val1.ext_value='test'
        self.failUnless(val1.ext_value=='test')
        self.failUnless(val1.int_value=='test      ')
        self.failUnless(isinstance(val1.ext_value,str))
        self.failUnless(isinstance(val1.int_value,str))
        val1=pysap.create_simple('C',1)
        self.failIf(isinstance(val1,ctypes.c_char))
        val1=pysap.create_simple('C',10)
        val1.ext_value=100
        self.failUnless(val1.int_value=='0000000100')
        val1=pysap.create_simple('C',10)
        val1.ext_value='150'
        self.failUnless(val1.int_value=='0000000150')        
    def test_numc(self):
        val1=pysap.create_simple('N',8)
        val1.ext_value=100
        self.failUnless(val1.ext_value==100)
        self.failUnless(val1.int_value=='00000100')
        self.failUnless(isinstance(val1.ext_value,int))
        self.failUnless(isinstance(val1.int_value,str))
    def test_bcd(self):
        val1=pysap.create_simple('P',8,2)
        if pysap.has_fp:
            val1.ext_value=pysap.FixedPoint(10.25)
        else:
            val1.ext_value=10.25
        if pysap.has_fp:
            self.failUnless(isinstance(val1.ext_value,pysap.FixedPoint))
            self.failUnless(val1.ext_value.p==2)
        else:
            self.failUnless(isinstance(val1.ext_value,float))
    def test_date(self):
        val1=pysap.create_simple('D')
        if pysap.has_mx:
            val1.ext_value='20.8.2002'
            self.failUnless(val1.int_value=='20020820')
        else:
            val1.ext_value='20020820'
        self.failUnless(isinstance(val1.ext_value,str))
        self.failUnless(isinstance(val1.int_value,str))
        self.failUnless(len(val1.int_value)==8)
        self.failUnless(val1)
        val1.ext_value=None
        self.failUnless(val1.ext_value=='')
        self.failUnless(val1.int_value=='00000000')
        self.failUnless(not val1)
    def test_time(self):
        val1=pysap.create_simple('T')
        if pysap.has_mx:
            val1.ext_value='12:45:50'
            self.failUnless(val1.int_value=='124550')
        else:
            val1.ext_value='124550'
        self.failUnless(isinstance(val1.ext_value,str))
        self.failUnless(isinstance(val1.int_value,str))
        self.failUnless(len(val1.int_value)==6)
    def test_binary(self):
        import random
        bdata=''.join([chr(random.randrange(256)) for i in range(49)])+'\x00'
        val1=pysap.create_simple('X',50)
        val1.ext_value=bdata
        self.failUnless(val1.ext_value==bdata)
        self.failUnless(val1.ext_value==val1.int_value)
        self.failUnless(isinstance(val1.ext_value,str))
        val1=pysap.create_simple('X',25)
        val1.ext_value=bdata
        self.failUnless(val1.ext_value==bdata[:25])
        val1=pysap.create_simple('X',100)
        val1.ext_value=bdata
        self.failUnless(val1.ext_value[:50]==bdata)
        val1.reset()
        self.failUnless(val1.ext_value=='\x00'*100)
        self.failUnless(isinstance(val1.ext_value,str))
    def test_conversion(self):
        val1=pysap.create_simple('C',4)
        val1.convert_input=to_upper
        val1.ext_value='abcd'
        self.failUnless(val1.ext_value=='ABCD')
        self.failUnless(val1.int_value=='ABCD')
        val1.convert_input=None
        val1.convert_output=to_upper
        val1.ext_value='abcd'
        self.failUnless(val1.ext_value=='ABCD')
        self.failUnless(val1.int_value=='abcd')

def get_suite():
    return unittest.makeSuite(SimpleDataTestCase)

def test(verbose=0):
    runner = unittest.TextTestRunner(verbosity=verbose)
    runner.run(get_suite())

if __name__ == '__main__':
    unittest.main()
