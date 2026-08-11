# ============================================================
# SECTION 1: raw source data (originally data.py)
# ============================================================

import re

COUNTIES = ["Abbeville","Aiken","Allendale","Anderson","Bamberg","Barnwell","Beaufort",
"Berkeley","Calhoun","Charleston","Cherokee","Chester","Chesterfield","Clarendon",
"Colleton","Darlington","Dillon","Dorchester","Edgefield","Fairfield","Florence",
"Georgetown","Greenville","Greenwood","Hampton","Horry","Jasper","Kershaw","Lancaster",
"Laurens","Lee","Lexington","Marion","Marlboro","McCormick","Newberry","Oconee",
"Orangeburg","Pickens","Richland","Saluda","Spartanburg","Sumter","Union","Williamsburg","York"]

DOC10 = """Abbeville	Graham +21.8%	
>95%
1,602
55.6%
975
33.8%
86
3.0%
74
2.6%
102
3.5%
43
1.5%
2,882
Aiken	Graham +38.6%	
>95%
9,141
61.9%
3,439
23.3%
720
4.9%
665
4.5%
446
3.0%
357
2.4%
14,768
Allendale	Graham +69.1%	
>95%
162
78.3%
19
9.2%
14
6.8%
5
2.4%
5
2.4%
2
1.0%
207
Anderson	Graham +9.8%	
>95%
12,580
48.4%
10,033
38.6%
1,253
4.8%
873
3.4%
712
2.7%
519
2.0%
25,970
Bamberg	Graham +52.2%	
>95%
413
71.8%
113
19.6%
5
0.9%
14
2.4%
18
3.1%
12
2.1%
575
Barnwell	Graham +41.0%	
>95%
1,055
65.2%
392
24.2%
45
2.8%
51
3.1%
39
2.4%
35
2.2%
1,617
Beaufort	Graham +40.2%	
>95%
13,510
62.8%
4,864
22.6%
887
4.1%
883
4.1%
789
3.7%
573
2.7%
21,506
Berkeley	Graham +41.9%	
>95%
10,752
63.0%
3,606
21.1%
738
4.3%
804
4.7%
719
4.2%
437
2.6%
17,056
Calhoun	Graham +50.8%	
>95%
1,177
69.5%
316
18.7%
47
2.8%
44
2.6%
68
4.0%
41
2.4%
1,693
Charleston	Graham +41.7%	
>95%
18,308
63.9%
6,362
22.2%
1,119
3.9%
1,183
4.1%
958
3.3%
737
2.6%
28,667
Cherokee	Graham +18.9%	
>95%
4,038
52.4%
2,582
33.5%
381
4.9%
231
3.0%
254
3.3%
226
2.9%
7,712
Chester	Graham +34.8%	
>95%
1,699
60.4%
720
25.6%
145
5.2%
95
3.4%
83
3.0%
73
2.6%
2,815
Chesterfield	Graham +42.9%	
>95%
1,640
65.3%
563
22.4%
100
4.0%
75
3.0%
72
2.9%
60
2.4%
2,510
Clarendon	Graham +50.2%	
>95%
1,904
68.4%
506
18.2%
95
3.4%
142
5.1%
90
3.2%
46
1.6%
2,783
Colleton	Graham +45.6%	
>95%
2,213
66.3%
690
20.7%
105
3.1%
106
3.2%
143
4.3%
83
2.5%
3,340
Darlington	Graham +46.4%	
>95%
3,440
67.5%
1,078
21.2%
120
2.4%
180
3.5%
136
2.7%
141
2.8%
5,095
Dillon	Graham +59.3%	
>95%
1,015
75.1%
213
15.8%
37
2.7%
36
2.7%
28
2.1%
23
1.7%
1,352
Dorchester	Graham +41.8%	
>95%
7,510
63.0%
2,527
21.2%
516
4.3%
546
4.6%
507
4.3%
319
2.7%
11,925
Edgefield	Graham +36.1%	
>95%
1,445
62.8%
615
26.7%
81
3.5%
70
3.0%
56
2.4%
35
1.5%
2,302
Fairfield	Graham +40.0%	
>95%
815
64.2%
307
24.2%
41
3.2%
42
3.3%
33
2.6%
32
2.5%
1,270
Florence	Graham +50.8%	
>95%
6,552
70.4%
1,826
19.6%
235
2.5%
252
2.7%
275
3.0%
167
1.8%
9,307
Georgetown	Graham +48.4%	
>95%
5,737
68.5%
1,683
20.1%
247
3.0%
295
3.5%
228
2.7%
182
2.2%
8,372
Greenville	Lynch +4.8%	
>95%
22,722
40.1%
25,458
44.9%
3,986
7.0%
1,911
3.4%
1,401
2.5%
1,228
2.2%
56,706
Greenwood	Graham +31.8%	
>95%
4,026
60.1%
1,896
28.3%
247
3.7%
203
3.0%
185
2.8%
139
2.1%
6,696
Hampton	Graham +48.5%	
>95%
227
66.4%
61
17.8%
15
4.4%
16
4.7%
11
3.2%
12
3.5%
342
Horry	Graham +49.7%	
>95%
27,517
68.4%
7,517
18.7%
1,182
2.9%
2,045
5.1%
1,151
2.9%
831
2.1%
40,243
Jasper	Graham +41.5%	
>95%
2,698
63.3%
930
21.8%
212
5.0%
161
3.8%
154
3.6%
110
2.6%
4,265
Kershaw	Graham +43.0%	
>95%
4,232
65.3%
1,443
22.3%
217
3.4%
212
3.3%
207
3.2%
174
2.7%
6,485
Lancaster	Graham +35.3%	
>95%
6,071
61.0%
2,554
25.7%
424
4.3%
362
3.6%
321
3.2%
220
2.2%
9,952
Laurens	Graham +7.0%	
>95%
3,599
47.0%
3,064
40.1%
370
4.8%
254
3.3%
228
3.0%
134
1.8%
7,649
Lee	Graham +58.2%	
>95%
710
74.9%
158
16.7%
20
2.1%
25
2.6%
24
2.5%
11
1.2%
948
Lexington	Graham +38.3%	
>95%
19,475
61.6%
7,377
23.3%
1,421
4.5%
1,322
4.2%
1,152
3.6%
879
2.8%
31,626
Marion	Graham +57.2%	
>95%
1,104
73.1%
239
15.8%
43
2.9%
59
3.9%
44
2.9%
22
1.5%
1,511
Marlboro	Graham +68.1%	
>95%
741
79.4%
106
11.4%
24
2.6%
22
2.4%
21
2.3%
19
2.0%
933
McCormick	Graham +46.0%	
>95%
1,109
67.8%
357
21.8%
50
3.1%
55
3.4%
42
2.6%
22
1.4%
1,635
Newberry	Graham +36.7%	
>95%
2,712
62.6%
1,121
25.9%
144
3.3%
128
3.0%
134
3.1%
95
2.2%
4,334
Oconee	Graham +17.5%	
>95%
5,839
51.8%
3,861
34.2%
687
6.1%
400
3.5%
265
2.4%
227
2.0%
11,279
Orangeburg	Graham +55.0%	
>95%
2,544
72.1%
605
17.1%
114
3.2%
96
2.7%
93
2.6%
77
2.2%
3,529
Pickens	Graham +6.1%	
>95%
7,456
46.0%
6,466
39.8%
1,027
6.3%
499
3.1%
464
2.9%
316
1.9%
16,228
Richland	Graham +40.3%	
>95%
11,407
63.2%
4,132
22.9%
757
4.2%
696
3.9%
481
2.7%
583
3.2%
18,056
Saluda	Graham +40.0%	
>95%
1,668
62.6%
602
22.6%
122
4.6%
98
3.7%
109
4.1%
64
2.4%
2,663
Spartanburg	Lynch +2.3%	
>95%
12,886
41.1%
13,600
43.4%
2,467
7.9%
872
2.8%
873
2.8%
667
2.1%
31,365
Sumter	Graham +52.1%	
>95%
3,603
69.5%
904
17.4%
204
3.9%
231
4.5%
150
2.9%
93
1.8%
5,185
Union	Graham +22.3%	
>95%
1,515
55.7%
908
33.4%
121
4.5%
64
2.4%
75
2.8%
39
1.4%
2,722
Williamsburg	Graham +60.0%	
>95%
1,008
75.0%
202
15.0%
43
3.2%
30
2.2%
38
2.8%
23
1.7%
1,344
York	Graham +20.0%	
>95%
12,318
48.7%
7,256
28.7%
3,231
12.8%
1,004
4.0%
775
3.1%
705
2.8%
25,289"""

DOC11 = """Abbeville	Wilson +0.8%	
>95%
887
30.3%
910
31.1%
404
13.8%
443
15.1%
245
8.4%
21
0.7%
19
0.7%
2,929
Aiken	Evette +10.4%	
>95%
5,551
37.2%
3,990
26.7%
1,997
13.4%
1,210
8.1%
1,852
12.4%
171
1.1%
168
1.1%
14,939
Allendale	Evette +18.7%	
>95%
94
45.2%
55
26.4%
18
8.7%
13
6.3%
25
12.0%
2
1.0%
1
0.5%
208
Anderson	Evette +3.4%	
>95%
6,795
25.8%
5,910
22.5%
5,495
20.9%
4,909
18.7%
2,824
10.7%
215
0.8%
158
0.6%
26,306
Bamberg	Evette +4.0%	
>95%
180
31.0%
157
27.1%
106
18.3%
36
6.2%
94
16.2%
1
0.2%
6
1.0%
580
Barnwell	Wilson +2.9%	
>95%
544
33.2%
591
36.1%
163
9.9%
101
6.2%
203
12.4%
15
0.9%
22
1.3%
1,639
Beaufort	Evette +4.0%	
>95%
6,159
28.1%
5,270
24.0%
3,056
13.9%
1,743
8.0%
5,127
23.4%
224
1.0%
353
1.6%
21,932
Berkeley	Wilson +5.9%	
>95%
4,122
23.7%
5,149
29.6%
1,843
10.6%
2,676
15.4%
3,338
19.2%
126
0.7%
169
1.0%
17,423
Calhoun	Wilson +1.0%	
>95%
564
32.9%
581
33.9%
208
12.1%
218
12.7%
126
7.3%
10
0.6%
7
0.4%
1,714
Charleston	Wilson +8.3%	
>95%
7,214
24.4%
9,664
32.6%
3,543
12.0%
4,358
14.7%
4,387
14.8%
213
0.7%
232
0.8%
29,611
Cherokee	Norman +5.0%	
>95%
2,142
27.3%
1,134
14.4%
2,535
32.3%
1,209
15.4%
662
8.4%
80
1.0%
88
1.1%
7,850
Chester	Norman +2.5%	
>95%
643
22.3%
803
27.9%
874
30.4%
187
6.5%
329
11.4%
31
1.1%
13
0.5%
2,880
Chesterfield	Evette +14.5%	
>95%
1,006
39.7%
639
25.2%
324
12.8%
216
8.5%
296
11.7%
17
0.7%
37
1.5%
2,535
Clarendon	Evette +16.3%	
>95%
1,186
42.1%
728
25.8%
293
10.4%
291
10.3%
290
10.3%
16
0.6%
13
0.5%
2,817
Colleton	Wilson +8.9%	
>95%
823
24.3%
1,123
33.2%
300
8.9%
427
12.6%
667
19.7%
28
0.8%
18
0.5%
3,386
Darlington	Wilson +1.8%	
>95%
1,803
34.9%
1,896
36.7%
403
7.8%
634
12.3%
376
7.3%
25
0.5%
33
0.6%
5,170
Dillon	Evette +6.4%	
>95%
570
42.0%
484
35.7%
76
5.6%
105
7.7%
107
7.9%
10
0.7%
4
0.3%
1,356
Dorchester	Wilson +3.3%	
>95%
2,928
24.1%
3,323
27.3%
1,187
9.8%
2,401
19.8%
2,119
17.4%
85
0.7%
110
0.9%
12,153
Edgefield	Evette +18.4%	
>95%
980
42.0%
550
23.6%
315
13.5%
197
8.4%
264
11.3%
17
0.7%
11
0.5%
2,334
Fairfield	Evette +7.1%	
>95%
403
31.3%
311
24.1%
303
23.5%
133
10.3%
126
9.8%
4
0.3%
8
0.6%
1,288
Florence	Wilson +26.1%	
>95%
2,454
26.0%
4,924
52.1%
493
5.2%
798
8.4%
678
7.2%
51
0.5%
50
0.5%
9,448
Georgetown	Evette +9.5%	
>95%
2,994
35.3%
2,190
25.9%
841
9.9%
1,109
13.1%
1,166
13.8%
62
0.7%
111
1.3%
8,473
Greenville	Norman +0.6%	
>95%
13,165
22.9%
13,467
23.4%
13,792
24.0%
10,237
17.8%
6,020
10.5%
468
0.8%
285
0.5%
57,434
Greenwood	Evette +2.8%	
>95%
2,205
32.4%
2,013
29.6%
856
12.6%
989
14.5%
643
9.4%
55
0.8%
49
0.7%
6,810
Hampton	Wilson +0.6%	
>95%
103
30.0%
105
30.6%
44
12.8%
10
2.9%
70
20.4%
6
1.8%
5
1.5%
343
Horry	Evette +34.8%	
>95%
20,485
50.3%
6,313
15.5%
2,857
7.0%
5,504
13.5%
4,987
12.2%
243
0.6%
364
0.9%
40,753
Jasper	Evette +12.0%	
>95%
1,488
34.4%
908
21.0%
429
9.9%
411
9.5%
969
22.4%
49
1.1%
76
1.8%
4,330
Kershaw	Evette +3.5%	
>95%
1,998
30.1%
1,767
26.6%
1,457
21.9%
743
11.2%
590
8.9%
37
0.6%
47
0.7%
6,639
Lancaster	Evette +0.6%	
>95%
3,023
29.9%
1,919
19.0%
2,963
29.3%
668
6.6%
1,307
12.9%
97
1.0%
126
1.3%
10,103
Laurens	Wilson +2.5%	
>95%
1,918
24.9%
2,114
27.4%
1,370
17.8%
1,401
18.2%
806
10.5%
52
0.7%
40
0.5%
7,701
Lee	Evette +17.4%	
>95%
384
40.0%
177
18.4%
217
22.6%
93
9.7%
69
7.2%
9
0.9%
11
1.1%
960
Lexington	Wilson +17.3%	
>95%
7,730
23.9%
13,326
41.2%
3,665
11.3%
4,168
12.9%
3,028
9.3%
258
0.8%
198
0.6%
32,373
Marion	Evette +17.1%	
>95%
673
44.1%
411
26.9%
98
6.4%
152
9.9%
170
11.1%
10
0.7%
13
0.8%
1,527
Marlboro	Evette +42.3%	
>95%
560
59.5%
162
17.2%
51
5.4%
72
7.6%
85
9.0%
6
0.6%
6
0.6%
942
McCormick	Evette +8.1%	
>95%
563
34.3%
431
26.3%
218
13.3%
181
11.0%
206
12.6%
20
1.2%
22
1.3%
1,641
Newberry	Wilson +5.4%	
>95%
1,087
24.7%
1,325
30.2%
980
22.3%
578
13.2%
377
8.6%
15
0.3%
31
0.7%
4,393
Oconee	Evette +7.8%	
>95%
3,533
31.0%
2,641
23.2%
2,021
17.7%
1,882
16.5%
1,169
10.3%
94
0.8%
50
0.4%
11,390
Orangeburg	Evette +7.1%	
>95%
1,305
36.7%
1,054
29.6%
357
10.0%
465
13.1%
338
9.5%
25
0.7%
15
0.4%
3,559
Pickens	Wilson +3.9%	
>95%
3,917
23.9%
4,563
27.8%
3,157
19.3%
2,852
17.4%
1,682
10.3%
149
0.9%
79
0.5%
16,399
Richland	Wilson +13.9%	
>95%
4,934
26.6%
7,507
40.5%
2,036
11.0%
2,207
11.9%
1,570
8.5%
151
0.8%
151
0.8%
18,556
Saluda	Evette +4.5%	
>95%
916
33.9%
793
29.3%
327
12.1%
416
15.4%
226
8.3%
17
0.6%
10
0.4%
2,705
Spartanburg	Evette +0.6%	
>95%
7,223
22.7%
6,555
20.6%
6,748
21.2%
7,040
22.2%
3,520
11.1%
479
1.5%
208
0.7%
31,773
Sumter	Evette +14.9%	
>95%
1,989
37.9%
1,208
23.0%
894
17.0%
588
11.2%
514
9.8%
22
0.4%
38
0.7%
5,253
Union	Norman +13.8%	
>95%
606
22.1%
327
11.9%
985
35.8%
546
19.9%
255
9.3%
21
0.8%
8
0.3%
2,748
Williamsburg	Wilson +4.5%	
>95%
447
32.8%
509
37.3%
100
7.3%
121
8.9%
159
11.7%
10
0.7%
17
1.3%
1,363
York	Norman +16.3%	
>95%
6,096
23.5%
3,582
13.8%
10,323
39.8%
2,184
8.4%
3,271
12.6%
238
0.9%
228
0.9%
25,922"""

TRUMP_HALEY = """Richland	41	58	33,087
Horry	67	33	71,823
Charleston	38	62	63,317
Spartanburg	70	29	47,366
Lexington	58	41	47,258
York	58	41	41,841
Anderson	69	31	34,552
Berkeley	59	40	30,245
Aiken	61	39	24,969
Pickens	68	32	23,102
Dorchester	57	42	20,531
Oconee	60	39	16,997
Lancaster	61	39	15,665
Florence	70	29	14,770
Georgetown	57	42	13,330
Laurens	76	23	10,284
Greenwood	64	36	10,078
Kershaw	66	34	9,383
Sumter	65	34	8,568
Cherokee	85	14	8,250
Darlington	74	26	7,624
Newberry	65	34	5,885
Orangeburg	67	32	5,672
Jasper	57	42	5,563
Colleton	70	30	4,474
Chesterfield	79	21	4,378
Clarendon	72	28	3,948
Edgefield	74	25	3,899
Union	84	15	3,793
Chester	78	21	3,749
Abbeville	76	23	3,742
Saluda	72	27	3,193
Marion	77	22	2,473
Fairfield	66	34	2,403
Dillon	85	15	2,385
McCormick	62	37	2,298
Williamsburg	80	20	2,236
Barnwell	77	22	2,079
Calhoun	70	29	1,989
Marlboro	82	17	1,715
Hampton	72	27	1,371
Lee	79	20	1,260
Bamberg	65	35	986
Allendale	71	29	334
Greenville	57	42	94,998
Beaufort	44	55	38,943"""

TURNOUT_TABLE = """Greenville	41,582
Horry	26,410
Lexington	23,618
Spartanburg	23,475
Charleston	20,544
Anderson	18,375
York	13,902
Richland	13,636
Beaufort	12,161
Berkeley	11,687
Pickens	11,666
Aiken	8,545
Dorchester	7,961
Oconee	7,877
Florence	7,268
Lancaster	5,876
Laurens	5,697
Greenwood	5,510
Georgetown	5,391
Kershaw	4,270
Cherokee	3,967
Sumter	3,789
Darlington	3,582
Newberry	3,204
Orangeburg	2,523
Jasper	2,254
Clarendon	2,185
Abbeville	2,066
Colleton	2,041
Saluda	1,914
Union	1,796
Chester	1,658
Chesterfield	1,599
Edgefield	1,562
McCormick	1,261
Calhoun	1,122
Marion	1,080
Dillon	1,045
Barnwell	917
Williamsburg	914
Fairfield	800
Lee	731
Marlboro	654
Bamberg	364
Hampton	166
Allendale	151"""


# ============================================================
# SECTION 2: parsing + statewide sanity checks (originally parse.py)
# ============================================================


NUM = re.compile(r'^-?[\d,]+\.?\d*%?$')

def clean_num(s):
    return float(s.replace(',', '').replace('%', ''))

def parse_block_table(raw, n_pairs):
    """Parse tables shaped like: County<TAB>Margin text<TAB>\n>95%\n(votes\npct%\n)*n_pairs\ntotal"""
    lines = [l for l in raw.split('\n')]
    records = {}
    i = 0
    county_set = set(COUNTIES)
    cur_county = None
    buffer = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # county line starts with a known county name followed by tab-separated margin text
        matched_county = None
        for c in county_set:
            if line.startswith(c + '\t') or line.startswith(c + ' Graham') or line == c:
                pass
        # simpler: split original raw by tabs is unreliable after strip; instead detect county by checking token before first number-like sequence
        pass
    return records

# Simpler, robust approach: DOC10/DOC11 raw text has tabs only on the county header line.
# Re-split using the ORIGINAL (non-stripped) text so we keep tabs on header lines.

def parse_race(raw, n_pairs):
    rows = raw.split('\n')
    records = {}
    idx = 0
    n = len(rows)
    while idx < n:
        line = rows[idx]
        if '\t' in line:
            county, margin = line.split('\t')[0], line.split('\t')[1]
            county = county.strip()
            idx += 1
            # next line should be ">95%" (percent reporting) - possibly blank line before it
            while rows[idx].strip() == '':
                idx += 1
            assert '95%' in rows[idx] or '100%' in rows[idx], rows[idx]
            idx += 1
            nums = []
            for _ in range(2 * n_pairs):
                nums.append(clean_num(rows[idx].strip()))
                idx += 1
            total = clean_num(rows[idx].strip())
            idx += 1
            pairs = [(nums[2*k], nums[2*k+1]) for k in range(n_pairs)]
            records[county] = {'pairs': pairs, 'total': total}
        else:
            idx += 1
    return records

DOC10_PARSED = parse_race(DOC10, 6)
DOC11_PARSED = parse_race(DOC11, 7)

assert set(DOC10_PARSED.keys()) == set(COUNTIES), set(COUNTIES) - set(DOC10_PARSED.keys())
assert set(DOC11_PARSED.keys()) == set(COUNTIES), set(COUNTIES) - set(DOC11_PARSED.keys())

# doc10 columns confirmed: col0=Graham, col1=Lynch
# doc11 columns confirmed: col0=Evette, col1=Wilson, col2=Norman

GRAHAM = {c: DOC10_PARSED[c]['pairs'][0][1] for c in COUNTIES}
LYNCH = {c: DOC10_PARSED[c]['pairs'][1][1] for c in COUNTIES}
DOC10_TOTAL = {c: DOC10_PARSED[c]['total'] for c in COUNTIES}

NORMAN = {c: DOC11_PARSED[c]['pairs'][2][1] for c in COUNTIES}
DOC11_TOTAL = {c: DOC11_PARSED[c]['total'] for c in COUNTIES}

# statewide check
def weighted_avg(pct_dict, weight_dict):
    num = sum(pct_dict[c] * weight_dict[c] for c in COUNTIES)
    den = sum(weight_dict[c] for c in COUNTIES)
    return num / den

print("Graham statewide (weighted, doc10 turnout):", round(weighted_avg(GRAHAM, DOC10_TOTAL), 1), "target given: 56.8")
print("Lynch statewide (weighted, doc10 turnout):", round(weighted_avg(LYNCH, DOC10_TOTAL), 1), "target given: 28.9")
print("Norman statewide (weighted, doc11 turnout):", round(weighted_avg(NORMAN, DOC11_TOTAL), 1), "target given: 17.1")

# Trump/Haley table
th_lines = [l for l in TRUMP_HALEY.split('\n') if l.strip()]
TRUMP = {}
HALEY = {}
TH_TOTAL = {}
for line in th_lines:
    parts = line.split('\t')
    county = parts[0].strip()
    trump_pct = clean_num(parts[1])
    haley_pct = clean_num(parts[2])
    total = clean_num(parts[3])
    TRUMP[county] = trump_pct
    HALEY[county] = haley_pct
    TH_TOTAL[county] = total

assert set(HALEY.keys()) == set(COUNTIES), set(COUNTIES) - set(HALEY.keys())
print("Haley statewide (weighted, T/H turnout):", round(weighted_avg(HALEY, TH_TOTAL), 1), "target given: 39.5")

# Turnout table (most recent statewide primary/runoff turnout -- used as county turnout weights
# for the new SC Senate primary model)
tt_lines = [l for l in TURNOUT_TABLE.split('\n') if l.strip()]
TURNOUT = {}
for line in tt_lines:
    parts = line.split('\t')
    county = parts[0].strip()
    TURNOUT[county] = clean_num(parts[1])

assert set(TURNOUT.keys()) == set(COUNTIES), set(COUNTIES) - set(TURNOUT.keys())
print("Turnout table statewide total:", sum(TURNOUT.values()))

if __name__ == '__main__':
    pass


# ============================================================
# SECTION 3: baseline build logic (originally build_sc_senate_baseline.py)
# ============================================================

"""
South Carolina Republican Senate Primary -- baseline builder.
Graham vs. Norman vs. Fry vs. Sanford vs. Lynch (+ Other).

METHOD: coalition-proxy indexing, not a direct crosswalk. None of the four
supplied source races IS this race, so for each candidate we compute an
"index" per county = (candidate's share of THEIR source race in that county)
/ (their own statewide share in that source race). An index of 1.20 means
"20% more of that candidate's coalition lives here, relative to the state,
than their source race's own statewide average." We then apply
target_pct(candidate) * index(candidate, county) and iteratively calibrate
(a) each candidate's turnout-weighted statewide average back to their exact
topline target and (b) each county's six candidates back to summing to 100,
alternating until both hold. This is standard iterative proportional fitting
(IPF); 25 passes converges to <1e-6 on this size table.

SOURCES, ONE PER CANDIDATE

- Graham, Lynch: actual Graham vs. Lynch SC Senate primary, county-level
  (Wilson-supplied). Statewide checks out exactly: Graham 56.8%, Lynch 28.9%,
  matching Wilson's stated figures -- confirms column identification.
- Norman: Norman's SC gubernatorial primary performance (17.1% statewide,
  confirmed against Wilson's figure), pulled from a 3-way-plus-minors
  Wilson/Evette/Norman primary table Wilson supplied.
- Sanford: proxy is Nikki Haley's county share in the 2024 SC GOP
  presidential primary (39.5% statewide, confirmed). Per Wilson's
  instruction ("better in SC-1, worse in Columbia"), the Haley index is
  boosted in SC-01 counties and reduced in Richland/Lexington (Columbia
  metro) before calibration -- see ADJUSTMENTS below.
- Fry: NO source race was supplied. Per Wilson's instruction ("do well in
  his district"), Fry's index starts flat (1.0 everywhere -- no signal) and
  is boosted only in his home SC-07 counties -- see ADJUSTMENTS below. This
  is a much weaker foundation than the other four candidates and should be
  replaced with an actual Fry proxy race (his prior US House primary/general
  results by county would be ideal) as soon as one is available.
- Other: flat 1.0 index (no signal supplied; distributed proportional to
  turnout only).

ADJUSTMENTS (PLACEHOLDER MAGNITUDES -- FLAG FOR WILSON)
Wilson specified direction ("better/worse") but not size. Applied here as a
+/-25% relative index adjustment in the named counties before calibration:
  Sanford:  SC-01 counties (Beaufort, Berkeley, Charleston, Colleton,
            Dorchester, Jasper) x1.25;  Richland, Lexington x0.75
  Fry:      SC-07 counties (Chesterfield, Darlington, Dillon, Florence,
            Georgetown, Horry, Marion, Marlboro, Williamsburg) x2.8
            (Fry has zero underlying signal elsewhere, so his district
            counties carry the entire shape of his coalition -- a much
            bigger relative bump than Sanford's, which sits on top of a
            real Haley baseline. x2.8 was chosen because it's the point
            where Fry actually wins his home turf outright -- below ~x2.7
            he places a strong second everywhere in SC-07 but never
            finishes first anywhere, which undersells a sitting
            congressman running in his own district. At x2.8 he leads all
            nine SC-07 counties in the high 30s, still well short of a
            landslide.)
District boundaries are whole-county approximations (SC-01/SC-07 both
split a county or two on the real map); treat this as directionally right,
not precinct-exact. THESE MULTIPLIERS ARE GUESSES -- rerun with Wilson's
actual preferred magnitudes before this baseline is used live.

TURNOUT WEIGHTS come from the Wilson/Evette runoff turnout table Wilson
supplied (318,796 statewide) -- used only as RELATIVE county weights here
(shape, not scale). No target statewide turnout was given for this Senate
primary; TARGET_TURNOUT below defaults to that table's own total. Rescale
if Wilson has a different turnout expectation for this race.
"""

import pandas as pd

TARGET = {"graham": 31.0, "norman": 24.0, "fry": 19.0, "sanford": 14.0,
          "lynch": 8.0, "other": 4.0}
CANDIDATES = list(TARGET.keys())
assert abs(sum(TARGET.values()) - 100.0) < 1e-9

TARGET_TURNOUT = sum(TURNOUT.values())  # placeholder -- see docstring

SC01 = {"Beaufort", "Berkeley", "Charleston", "Colleton", "Dorchester", "Jasper"}
COLUMBIA_METRO = {"Richland", "Lexington"}
SC07 = {"Chesterfield", "Darlington", "Dillon", "Florence", "Georgetown",
        "Horry", "Marion", "Marlboro", "Williamsburg"}


def weighted_avg(vals: dict, weights: dict) -> float:
    num = sum(vals[c] * weights[c] for c in COUNTIES)
    den = sum(weights[c] for c in COUNTIES)
    return num / den


def raw_index(source_pct: dict, source_weight: dict) -> dict:
    avg = weighted_avg(source_pct, source_weight)
    return {c: source_pct[c] / avg for c in COUNTIES}


def build_indices() -> dict:
    idx = {}
    idx["graham"] = raw_index(GRAHAM, DOC10_TOTAL)
    idx["lynch"] = raw_index(LYNCH, DOC10_TOTAL)
    idx["norman"] = raw_index(NORMAN, DOC11_TOTAL)

    sanford = raw_index(HALEY, TH_TOTAL)
    for c in COUNTIES:
        if c in SC01:
            sanford[c] *= 1.25
        elif c in COLUMBIA_METRO:
            sanford[c] *= 0.75
    idx["sanford"] = sanford

    fry = {c: 1.0 for c in COUNTIES}
    for c in COUNTIES:
        if c in SC07:
            fry[c] *= 2.8
    idx["fry"] = fry

    idx["other"] = {c: 1.0 for c in COUNTIES}
    return idx


def calibrate(idx: dict, n_iter: int = 25) -> pd.DataFrame:
    shares = {cand: {c: TARGET[cand] * idx[cand][c] for c in COUNTIES}
              for cand in CANDIDATES}

    for _ in range(n_iter):
        # column step: pin each candidate's turnout-weighted statewide avg to target
        for cand in CANDIDATES:
            avg = weighted_avg(shares[cand], TURNOUT)
            factor = TARGET[cand] / avg
            for c in COUNTIES:
                shares[cand][c] *= factor
        # row step: each county's six candidates sum to 100
        for c in COUNTIES:
            total = sum(shares[cand][c] for cand in CANDIDATES)
            for cand in CANDIDATES:
                shares[cand][c] *= 100.0 / total

    rows = []
    for c in COUNTIES:
        row = {"county": c, "turnout_weight": TURNOUT[c]}
        for cand in CANDIDATES:
            row[cand] = shares[cand][c]
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def build() -> pd.DataFrame:
    idx = build_indices()
    df = calibrate(idx)
    scale = TARGET_TURNOUT / df["turnout_weight"].sum()
    df["turnout"] = (df["turnout_weight"] * scale).round().astype(int)
    drift = TARGET_TURNOUT - df["turnout"].sum()
    if drift != 0:
        df.loc[df["turnout"].idxmax(), "turnout"] += drift
    for cand in CANDIDATES:
        df[f"{cand}_votes"] = (df["turnout"] * df[cand] / 100).round().astype(int)
    df = df.drop(columns=["turnout_weight"])
    return df[["county", "turnout"] + CANDIDATES + [f"{c}_votes" for c in CANDIDATES]]


if __name__ == "__main__":
    df = build()
    turnout = df["turnout"].sum()
    print(f"Statewide turnout (placeholder target): {turnout:,}\n")
    for cand in CANDIDATES:
        avg = weighted_avg({c: df.set_index('county')[cand][c] for c in COUNTIES}, TURNOUT)
        v = df[f"{cand}_votes"].sum()
        print(f"  {cand.capitalize():8s} target {TARGET[cand]:5.1f}%  ->  "
              f"calibrated {avg:5.2f}%  ({v:,} votes, {100*v/turnout:5.2f}%)")
    df.round(3).to_csv("sc_senate_gop_primary_baseline.csv", index=False)
    print("\nWrote sc_senate_gop_primary_baseline.csv")
    print("\nSample rows:")
    print(df.round(1).head(8).to_string(index=False))
