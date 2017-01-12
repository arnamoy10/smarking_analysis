# smarking_analysis

Jan 11 2017:

I have made two scripts:

data_analysis.py - takes garage ID and a start date and end date as argument and produces analysis results depending on how many days given.

		 e.g ->  for more than 6 months, it will do a monthly peak occupancy analysis, for 1-6 months, it will do a daily peak analysis, and for less than that, it will do an hourly analysis.

For monthly and daily peak occupancy, I am using IQR emthod still and it works well so far.

For hourly analysis per day (daily analysis), I have used SVDD, k means with 2 clusters and twitterd ESD based anomaly detection.  The Pycularity library works well for the twitter ESD analysis, but the thermometr library does not.  But the Pycularity library requires you to have R installed in your system.



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