# smarking_analysis

Jan 24 2017:

Creating metadata about files:

Directories:
    date_name: data for prediction accuracy, collected every night by running the download_prediction.sh scrip
    pyculiarity-master: twitter anomaly detection in python
    report: report for the paper
    thermometr-master: twitter anomaly detection that does not work
    website: The website for historical analysis
        cgi-bin: 
            add-garage.py: called from add-garage.html, adds garage info in spreadsheet anfd the garage_names file
            client_secret.json: needed for using google-api, can be downloaded as necessary
            data_analysis_google_doc.py: The historical data analysis script, work in progress
            data_analysis_google_doc_non_modular.py: intiial non modular implementation, may have some bugs as well
            false_positives: Not needed now, created initially to store feedback given by user, now using google spreadsheet
            garage_list: Deprecated, now the check-garages.html takes textbox instead of file
            garage_names: master list of garage_ids, name and urls
            holidays*:needs to be created for analysis to run
            real_time_checking.py: work in progress real time checking
            smarking_error_check.json: also google apli file
Files:
    data_analysis_paper.py: static data analysis on the downloaded data from santa monica real time
    download_prediction.sh: downloading prediction for measuring accuracy (will do until end of Jan every night)
    presentation.xlzx: figures etc.
    Parking_Lot_Counts.csv: Santa Monica Parking Data
    lot* csv, structure*.csv, pier_dec.csv, beach_house_lot.csv: santa monica individual garage data
    clustering.py: WIll check clustering later
    data_analysis_static.py: Old script to work with downloaded offline data, probably bugs inside
    prediction_accuracy.py: script to measure accuracy, has the metric implemented inside
    unusual.py: helper script for parsing results 

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