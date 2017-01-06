# smarking_analysis

Jan 5 2017:  

data_analysis.py :  Main file to do the data analysis

Currently I am doing historical analysis.  In the future, I may move to a more streaming analysis.

Currently I have the simple outlier detection running well.  Based on presence of 0 in the data or values outside +-3 IQR, it detects outliers.  For each outlier detected, it creates a chart showing the actual data.

So far I have worked with the most coarse grain data (monthly peak occupancy) and detecting anomalies within.  So for "transient" and "contract" parking, it creates two folders.  The folders has plots in them under the following hierarchy.

transient:
   gap
   zero_gap
contract
   gap
   zero_gap


The script also outputs the garage IDs and the kind of anomaly they have.