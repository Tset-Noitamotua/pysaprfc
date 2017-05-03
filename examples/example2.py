# This example shows how to manipulate internal tables.

# Connection to SAP R/3 system is not needed for this example.

import pysap
import random

def print_line(wa):
    # Simple function to print table row
    print '%(desc)-20s%(val1)10d%(val2)10d%(val3)15.2f' % wa

# Define structure and create table
struct3=(('desc','C',30),('val1','N',10),('val2','N',5),('val3','P',8,2))
itab=pysap.create_table('itab',struct3)

# Fill table with values ...
val_list=(10,15,45,100,200)
for i in range(20):
    wa=itab.struc()
    wa.from_list(['Test%d' % i,random.randrange(10),random.choice(val_list),random.random()*100])
    itab.append(wa)
# ... and print it
for wa in itab:
    print_line(wa)

# Now let's create new table using the same structure and fill it   
itab2=pysap.create_table('itab2',struct3)
for i in range(5):
    wa=itab.struc()
    wa.from_list(['New test%d' % i,random.randrange(10),random.choice(val_list),random.random()*100])
    itab2.append(wa)
    
# Copy itab2 to itab, start copying at row 6 of itab. Assigning values to slices acts the same
# way as with Python lists. Assigned value must be an ItTable instance. As from_structure is used
# to copy rows of source table to destination table, tables involved can have different row structures as
# long as they are binary compatible.
itab[5:10]=itab2

for wa in itab:
    print_line(wa)

# This structure is compatible to struct3
struct4=[('line','C',45),('val1','P',8,2)]

# Create new table using struct4
itab3=pysap.create_table('itab3',struct4)
for i in range(3):
    wa=itab3.struc()
    wa['line']='%-30s%010d%05d' % ('Compat test %d' % i,random.randrange(20),random.randrange(200))
    wa['val1']=random.random()*500
    itab3.append(wa)
    
# Copy itab3 to itab overriding its original contents
# (but itab row structure stays the same)
itab[:]=itab3
for wa in itab:
    print_line(wa)
