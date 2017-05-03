REPORT ZTEST1 .

* This ABAP program shows how to invoke remote function defined
* in test_remote.py.
* SET THE REMOTE DESTINATION ZTEST1 USING SM59 BEFORE RUNNING THIS
* PROGRAM!

data: in type I,
      out type I,
      date type D,
      date2 type D.

data: begin of itab occurs 0,
        name(30) type C,
        val1(8) type N,
        val2(8) type N,
        val3(8) type P decimals 2,
        val4 type D,
      end of itab,

      begin of test_struct,
        name(40) type C,
        val1(10) type N,
        date type D,
      end of test_struct,

      begin of test_struct2,
        name(40) type C,
        val1(10) type N,
        date type D,
      end of test_struct2.

in = 50.
itab-name = 'Test'.
itab-val1 = 1.
itab-val2 = 5.
itab-val3 = '10.99'.
itab-val4 = '20030527'.
append itab.
itab-name = 'Test 2'.
itab-val1 = 1.
itab-val2 = 5.
itab-val3 = '12.5'.
itab-val4 = '20030602'.
append itab.
test_struct2-name = 'Test 1'.
test_struct2-val1 = 120.
test_struct2-date = '20030604'.
date = '20030520'.

call function 'Z_TEST1' destination 'ZTEST1'
  exporting
    in_value = in
    in_value2 = 10
    in_value3 = date
  importing
    out_value = out
    out_date = date2
    out_struct = test_struct
  tables
    itab = itab
  exceptions
    not_null = 1
    others = 2.
if sy-subrc eq 1.
  write: / 'not_null error caught'.
elseif sy-subrc eq 2.
  write: / 'rfc error - this should not happen'.
else.
  write: / in, out.
endif.
loop at itab.
  write: / itab-name,
           itab-val1,
           itab-val2,
           itab-val3,
           itab-val4 dd/mm/yyyy.
endloop.
write: / test_struct-name, test_struct-val1,
         test_struct-date dd/mm/yyyy.
write: / test_struct2-name, test_struct2-val1, test_struct2-date.
write: / date2.

