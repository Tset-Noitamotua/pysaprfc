from distutils.core import setup

setup(name='Python SAP RFC module',
      author='Klavdij Voncina',
      author_email='voncina.klavdij@siol.net',
      version='1.0.0',
      license='Python license',
      url='http://sourceforge.net/projects/pysaprfc/',
      description='Interact with SAP R/3 ERP systems via RFC',
      long_description="""
The Python SAP RFC module enables programming remote function calls from SAP ERP systems. 
It enables SAP-compatible data definitions in Python (both simple and complex datatypes like 
structures and internal tables can be defined from within Python and manipulated like normal 
Python datatypes), and features transparent value conversion from SAP to Python and vice versa. 
It needs the SAP librfc shared library. Both client and server-side RFCs are possible.""",
      platforms=['linux','windows'],
      py_modules=['pysap'])