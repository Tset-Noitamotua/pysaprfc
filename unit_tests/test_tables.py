import unittest
import pysap

test_data1=[['test 1',50],
           ['test 2',100],
           ['test 3',150],
           ['test 4',220],
           ['test 5',275]]

def create_test_table():
    struct1=[('desc','C',30),('value','N',10)]
    itab=pysap.create_table('itab',struct1)
    for l in test_data1:
        wa=itab.struc()
        wa.from_list(l)
        itab.append(wa)
    return itab

class TablesTestCase(unittest.TestCase):
    def test_indexing(self):
        from operator import getitem
        itab=create_test_table()
        wa=itab.get_line(1)
        self.failUnless(wa['value']==itab[1]['value'])
        wa=itab.copy_line(3)
        self.failUnless(wa['value']==itab[3]['value'])
        self.failUnless(len(itab)==5)
        self.assertRaises(IndexError,getitem,itab,10)
        self.assertRaises(IndexError,getitem,itab,-10)
            
    def test_references(self):
        itab=create_test_table()
        wa=itab[1]
        wa['value']=450
        self.failUnless(wa['value']==itab[1]['value'])
        wa=itab.copy_line(2)
        wa['value']+=10
        self.failUnless(wa['value']!=itab[2]['value'])

    def test_slices(self):
        from operator import setslice
        itab=create_test_table()
        itab2=create_test_table()
        self.failUnless(len(itab[1:4])==3)
        self.failUnless(len(itab[::2])==3)
        self.assertRaises(TypeError,setslice,itab,1,3,'test')


def get_suite():
    return unittest.makeSuite(TablesTestCase)

def test(verbose=0):
    runner = unittest.TextTestRunner(verbosity=verbose)
    runner.run(get_suite())

if __name__ == '__main__':
    unittest.main()
        
        