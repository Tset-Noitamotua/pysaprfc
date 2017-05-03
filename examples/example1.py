# This example shows how to manipulate SAP structures and internal tables from Python.

# Connection to SAP R/3 system is not needed for this example.

import pysap

# Create field descriptions for the create_struct function
struct1=(('desc','C',32),('val1','N',8),('val2','N',8),('time','T'))
struct2=(('desc','C',40),('val2','N',8),('val3','N',5),('flag','C',1))
# Create both structures
S1=pysap.create_struct(struct1)
S2=pysap.create_struct(struct2)
# Instantiate S1
s1=S1()
# Print definition of 'val1' - should print N8
print s1.sap_def('val1')
# Fill in data
s1['desc']='Test values'
s1['val1']=100
s1['val2']=450
s1['time']='8:45:35' # Use this if you have mxDateTime installed
# s1['time']='84535' # Else use this
# Print it
print s1
# Create an instance of S2 and fill it with values
s2=S2()
s2['desc']='New long value (almost 40 characters)'
s2['val2']=1200
s2['val3']=150
s2['flag']='X'
print s2
# Now, let's copy corresponding fields of s2 to s1
# All fields having the same name in both structures will be copied
# Field 'desc' will be trimmed as its length exceeds defined length (32) for S1
s1.copy_corresp_from(s2)
# Print both structures
print s1
print s2
# Create new instance of S1 ...
s11=S1()
# ... and fill it using its from_list method
s11.from_list(['From the list','400','2650'])
# Print it
print s11
# Increase its val1 field by 320 ...
s11['val1']+=320
# ... and print it again
print s11

import random

# These are callback functions for table event handling
# fh - ItTableFieldHandler instance
# wa - current line
def new_val2(fh,wa):
    #This function is every time val2 changes
    print 'New value of val2: %d' % wa['val2']
def endof_val2(fh,wa):
    #This function is called before val2 changes
    print 'End of %d' % wa['val2']
def new_val1(fh,wa):
    #This function is every time val2 changes
    #Append sum to fh. sum will be used to sum val3 values.
    fh.sum=0.0
    print '*'*80
def every_val1(fh,wa):
    #This function gets called for every line
    #Increase the sum
    fh.sum+=wa['val3']
def endof_val1(fh,wa):
    print 'Sum of val3 for %5d%5d: %.2f' % (wa['val1'],wa['val2'],fh.sum)
    print '-'*80

# Define fields for the table
struct3=(('desc','C',30),('val1','N',10),('val2','N',5),('val3','P',8,2))
# Create new table from struct3
itab=pysap.create_table('itab',struct3)
# Fill it
val_list=(10,15,45,100,200)
for i in range(100):
    wa=itab.struc()
    wa.from_list(['Test%d' % i,random.randrange(10),random.choice(val_list),random.random()*100])
    itab.append(wa)

# Create the sort function and sort the table. Tables must be sorted for event-handling
# to function properly (same as in ABAP).
sort_func=pysap.create_sort_func(('val2','',0),('val1','',1))
itab.sort(sort_func)

# Create new handler for field 'val2'
fh=itab.add_field_handler('val2')
# Add on_new and on_endof callbacks
# on_new is fired when field value changes
# on_endof gets called before field value changes (same as ABAP AT ENDOF event)
# on_every is called on each pass
fh.on_new=new_val2
fh.on_endof=endof_val2
# Add field handler for combination of 'val1' and 'val2'
fh=itab.add_field_handler(('val1','val2'))
# Add callbacks
# These callbacks are summing values of 'val3' for each distinct value combination of 'val1' and 'val2'
# and print them before 'val1' changes
# (See their definitons above.)
fh.on_new=new_val1
fh.on_every=every_val1
fh.on_endof=endof_val1
# Field handlers are performed in same order they were defined except
# for on_endof handlers which are performed in reverse order.

# Print itab
# Field handling is performed during looping
for wa in itab:
    print '%(desc)-20s%(val1)10d%(val2)10d%(val3)15.2f' % wa

# Remove all event handlers from itab
itab.remove_all_handlers()
# Sort itab by 'desc'
sort_func=pysap.create_sort_func(('desc','',0))
itab.sort(sort_func)

# Create new row for itab
wa=itab.struc()
wa.from_list(['New line',50,150,25.0])
# And insert it as fifth line of itab
itab.insert(4,wa)

# Print rows 2 to 11 using slicing
# No field handling is perfomed (the field handlers were removed)
for wa in itab[1:11]:
    print '%(desc)-20s%(val1)10d%(val2)10d%(val3)15.2f' % wa

# Print even rows of itab using slicing
for wa in itab[::2]:
    print '%(desc)-20s%(val1)10d%(val2)10d%(val3)15.2f' % wa

# Print some info about itab structure using its first line
for fld_name in itab[0]._sfield_names_:
    print fld_name,itab[0].sap_def(fld_name)

