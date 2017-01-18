#!/usr/bin/python

import cgi, os
import cgitb; cgitb.enable()

import sys
    

#print "Importing libraries"
import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shutil
from datetime import datetime, timedelta
from dateutil import relativedelta


from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn import svm
from sklearn.cluster import KMeans
import requests

#twitter analysis for timeseries anomaly detection
from pyculiarity import detect_ts
from pyculiarity import detect_vec



#flags to determine whether contracts or transient was found
con = 0
tran = 0

#STAGE 1: get data

form = cgi.FieldStorage()

# Get filename here.
fileitem = form['filename']

garage_list =[]
holidays=[]

if fileitem.file:
    # It's an uploaded file; get lines
    while True:
        line = fileitem.file.readline()
        if not line: break
        garage_list.append(line)
    message = 'The file has been uploaded.'
else:
    message = 'No file was uploaded'
    
#get the garage names
garage_names=[]
with open("garage_names") as f:
    garage_names= f.readlines()
    
#get the previously reported false positives
with open("false_positives") as f:
    false_positives = [x.rstrip('\n') for x in f.readlines()]


false_positives = set(false_positives)
    
#get the number of hours, necessary to download occupancy
date_format = "%Y-%m-%d"


garages = []
start_dates = []
end_dates = []

for line in garage_list:
    string = line.split()
    garages.append(string[0])
    start_dates.append(string[1])
    end_dates.append(string[2])

#print garages
#print start_dates
#print end_dates

print """Content-Type: text/html\n
<html>

<head><meta charset="UTF-8"><title>Smarking checking</title> <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/meyer-reset/2.0/reset.min.css"><link rel='stylesheet prefetch' href='http://fonts.googleapis.com/css?family=Roboto:400,100,300,500,700,900|RobotoDraft:400,100,300,500,700,900'><link rel='stylesheet prefetch' href='http://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'><link rel="stylesheet" href="/css/style.css">
<style>
input[type=checkbox]:checked + label.strikethrough{
  text-decoration: line-through;
}
.form-module submit {
  cursor: pointer;
  background: #33b5e5;
  width: 100%;
  border: 0;
  padding: 10px 15px;
  color: #ffffff;
  -webkit-transition: 0.3s ease;
  transition: 0.3s ease;
}
.form-module submit:hover {
  background: #178ab4;
}
</style>
</head>


<body>"""

print """<div class="pen-title">
    <p><img src="/logo-s.png"><h2 style="color:darkcyan;font-size: 20px;">Here are the checking Results, please mark the false positives (if any) and commit your checks. </h2></p></div>
<form method="post" action="/cgi-bin/process_check.py">
"""
#print """</body>
#</html>"""
#sys.exit(0)


#Array to hold if there was data for occupancy present at the garage 
# 0 -> everything present
# 1 -> contract present
# 2 -> transient present
# 3 -> nothing present                  
garage_info_occupancy = [0] * len(garages)

line_index=0

#We do one garage at a time so, just one iteration is fine
#TODO: take out the loop and fix indentation
for i in np.arange(0,len(garages)):
    #print "processing ",garages[i]
    print '<h1 style="color:darkcyan;font-size: 30px;">Garage ID: %s</h1><p></p><p></p>' % str(garages[i])
    contracts=[]
    transients=[]
    try:
        datetime.strptime(start_dates[i], date_format)
        datetime.strptime(end_dates[i], date_format)
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-mm-dd")
    
    start_date = datetime.strptime(start_dates[i], date_format)
    end_date = datetime.strptime(end_dates[i], date_format)

    #check if the from_date is < to_date
    if (start_date > end_date):
        print "<p>From_date can't be after to_date</p>"
        continue

    delta= end_date - start_date

    duration_hours = 0
    if delta.days == 0:
        duration_hours = 24
    else:
        duration_hours = (abs(delta.days)+1) * 24


    
    #change the authentication token accordingly
    headers = {"Authorization":"Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"}
    #create the URL 
    url="https://my.smarking.net/api/ds/v3/garages/"+str(garages[i])+"/past/occupancy/from/"+start_dates[i]+"T00:00:00/"+str(duration_hours)+"/1h?gb=User+Type"


    #get the response using the url
    response = requests.get(url,headers=headers)
    content = response.content

    #print content
    #see if content was received.  If nothing  received, exit
    if (content == ""):
        print "<p>No content received</p>"
        continue


    #print url
    #we have collected all the data
    #each datapoint is for an hour in a given day
    
    garage_info = json.loads(content)
    
    #objects to store the parsed result
    contract = []
    transient = []
    
    
    #parse the JSON-formatted line
    for item in garage_info["value"]:
        group = str(item.get("group"))
        if('Contract' in group):    
            contract = item.get("value")
            con = 1
        if('Transient' in group):
            transient = item.get("value")
            tran = 1
    

    if ((con == 0) and (tran == 0)):
        garage_info_occupancy[line_index] = 3
        #print "no data for ", line_index
        line_index = line_index + 1
        continue
    if (con == 0):
        l = len(transient)
        contract = [0] * l
        garage_info_occupancy[line_index] = 2
    if (tran == 0):
        l = len(contract)
        transient = [0] * l
        garage_info_occupancy[line_index] = 1
    
    #add the parsed result to the master list                           
    contracts.append(contract)                                          
    transients.append(transient)
    
    #print garages[i], garage_info_occupancy[i]
    
    #reset the values of flags
    con = 0
    tran = 0


    
    #contracts[] and transients[] looks like this:
    #[[gar1_day_1_hour1, gar1_day1_hour2, ..., gar1_day365_hour24],
    # [gar2_day_1_hour1, gar2_day1_hour2, ..., gar2_day365_hour24]
    #    ...
    # [garn_day_1_hour1, garn_day1_hour2, ..., garn_day365_hour24]]

    #STAGE 2:  Construct the MONTHLY peak occupancy list

    #if at least not two full months, skip the monthly analysis
    delta= relativedelta.relativedelta(start_date, end_date)
    months = delta.months
    years = delta.years


    total_months = abs(years)*12+abs(months)

    delta= end_date - start_date
    ndays = abs(delta.days)+1
    
    
    if (total_months > 6):
        
        print '<h2 style="color:darkcyan;font-size: 20px;">Monthly Peak Anomalies</h2>'

        months_max_occ=[]
    
        #replace the following with one list
        #needed to do total_months+2 for various date perks
        month_occupancies = [[] for ii in range(total_months+2)]
    
        for ii in np.arange(0,len(contracts)):
            #print "for", i
            temp_date = start_date
            month_end =  start_date
        
            #index to extract data from the master datastructures
            #e.g contracts and transients
            hour_index = 0
            month_index = 0
            while True:
                #calculate the month end date, so that we can extract data
                month_end = temp_date + relativedelta.relativedelta(day=31)
            
                if(month_end >= end_date):
                    #we are going over, get the rest
                    days = (end_date-temp_date).days + 1
                    if (garage_info_occupancy[ii] == 3):
                        #add 0 for no data, we will skip it later anyway
                        l = [0,0]
                        month_occupancies[month_index].append(l)
                    else:
                        l = []
                        #print hour_index, days, hour_index+days*24-1
                        l.append(np.amax(contracts[ii][hour_index:hour_index+days*24]))
                        l.append(np.amax(transients[ii][hour_index:hour_index+days*24]))
                        month_occupancies[month_index].append(l)                    
                    break
                else:
                    #keep looping until we have found the end date
                    days = (month_end-temp_date).days + 1
                    if (garage_info_occupancy[ii] == 3):
                        #add 0 for no data, we will skip it later anyway
                        l = [0,0]
                        month_occupancies[month_index].append(l)
                    else:
                        l = []
                        #print hour_index, days, hour_index+days*24-1
                        l.append(np.amax(contracts[ii][hour_index:hour_index+days*24]))
                        l.append(np.amax(transients[ii][hour_index:hour_index+days*24]))
                        month_occupancies[month_index].append(l)  
                    
                    #update the hour index
                    hour_index = hour_index + days*24 
                    temp_date = month_end + timedelta(days=1)
                month_index = month_index + 1
            
            for jj in np.arange(0, month_index+1):
                months_max_occ.append(month_occupancies[jj])
  
    #STAGE 3:  Anomaly Detection


        training_data=[]        
    #list that holds indices of garages in the
    #training data from the master garage
        training_garages=[] 
                                           
    #dealing with contracts
    #forming the training data set
        for ii in np.arange(0, len(contracts)):
            if((garage_info_occupancy[ii] == 3) or (garage_info_occupancy[ii] == 2)):
            #print "No contract for ", garage_list[i]
                continue
            t = []                                      
            for jj in np.arange(0, total_months+1):
                t.append(months_max_occ[jj][ii][0])
                #normalize
            t1=map(float, t)
        #avoid dividing by zero
            #if (np.amax(t1) != 0):
            #    training_data.append(t1/np.amax(t1))
            #else:
            #    training_data.append(t1)
            training_data.append(t1)
    #Array to hold if there was an anomaly or not for a month
    #we have one flag per month
        anomaly_present = [0] * len(training_data[ii])

        #training_data[garage_index][month_index]
        for ii in np.arange(0, len(training_data)):
            for m in np.arange(0,len(training_data[ii])):
                if (0 == training_data[ii][m]):
                    anomaly_present[m] = 1
            #Algorithm (detecting non zero gaps):

    # If data points fall beyond 3 IQR -> REPORT gap

        for ii in np.arange(0, len(training_data)):
            p25 = np.percentile(training_data[ii], 25)
            p75 = np.percentile(training_data[ii], 75)
            iqr = np.subtract(*np.percentile(training_data[ii], [75, 25]))

            #1.5 was too restrictive
            lower = p25 - 3 * (p75 - p25)
            upper = p75 + 3 * (p75 - p25)
    
            for m in np.arange(0,len(training_data[ii])):
                if ((round(training_data[ii][m],2) < round(lower,2)) or (round(training_data[ii][m],2) > round(upper, 2))):
                    #print training_data[i][m], " is not between ", lower, " and ", upper
                    anomaly_present[m] = 2

    #print the anomaly results
        
    
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 1)):
            print '<h3 style="font-weight: bold;">Contracts</h3>'
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    #create the value for the checkbox so that it can be stored for
                    #future
                    val = "con-"+str(garages[i])+"-"+str(dates[ii].month)+str(dates[ii].year)
                    
                    #check if it was previously reported as false positive
                    if val in false_positives:
                        continue
                        
                    print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Zero gap for %s-%s </label>' % (val,dates[ii].month,dates[ii].year)
                if anomaly_present[ii] == 2:
                    val = "con-"+str(garages[i])+"-"+str(dates[ii].month)+str(dates[ii].year)
                    
                    #check if it was previously reported as false positive
                    if val in false_positives:
                        continue
                        
                    print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Gap for %s-%s </label> ' % (val,dates[ii].month,dates[ii].year)
                if ((anomaly_present[ii] == 1) or (anomaly_present[ii] == 2)):
                    #generate url
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    #print url
                    print '<a href =%s target="_blank">verify</a></p>' % url
            
        
    


        #Do the same thing for Transients
        training_data=[]        
        training_garages=[]           
                                           
    #dealing with transients
    #forming the training data set
    #make sure to normalize against the mean
        for ii in np.arange(0, len(transients)):
            if((garage_info_occupancy[ii] == 3) or (garage_info_occupancy[ii] == 1)):
                continue
            t = []                                      
            for jj in np.arange(0, total_months+1):
                t.append(months_max_occ[jj][ii][1])
            #normalize            
            t1=map(float, t)
    
            #avoid dividing by zero
            #if (np.amax(t1) != 0):
            #    training_data.append(t1/np.amax(t1))
            #else:
            #    training_data.append(t1)
            training_data.append(t1)
            training_garages.append(ii)                                                   
                                
    
    
        anomaly_present = [0] * len(training_data[ii])

        #training_data[garage_index][month_index]
        for ii in np.arange(0, len(training_data)):
            for m in np.arange(0,len(training_data[ii])):
                if (0 == training_data[ii][m]):
                    anomaly_present[m] = 1
            #Algorithm (detecting non zero gaps):

        # If data points fall beyond 3 IQR -> REPORT gap

        for ii in np.arange(0, len(training_data)):
            p25 = np.percentile(training_data[ii], 25)
            p75 = np.percentile(training_data[ii], 75)
            iqr = np.subtract(*np.percentile(training_data[ii], [75, 25]))
  
            #1.5 was too restrictive
            lower = p25 - 3 * (p75 - p25)
            upper = p75 + 3 * (p75 - p25)
    
            for m in np.arange(0,len(training_data[ii])):
                if ((round(training_data[ii][m],2) < round(lower,2)) or (round(training_data[ii][m],2) > round(upper, 2))):
                        #print training_data[i][m], " is not between ", lower, " and ", upper
                    anomaly_present[m] = 2

    #print the anomaly results
        
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 2)):
            print '<h3 style="font-weight: bold;">Transients</h3>'
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    val = "tran-"+str(garages[i])+"-"+str(dates[ii].month)+str(dates[ii].year)
                    
                    #check if it was previously reported as false positive
                    if val in false_positives:
                        continue
                        
                    print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Zero gap for %s-%s </label> ' % (val,dates[ii].month,dates[ii].year)
                if anomaly_present[ii] == 2:
                    val = "tran-"+str(garages[i])+"-"+str(dates[ii].month)+str(dates[ii].year)
                    
                    #check if it was previously reported as false positive
                    if val in false_positives:
                        continue
                        
                    print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Gap for %s-%s </label>' % (val,dates[ii].month,dates[ii].year)
                if ((anomaly_present[ii] == 1) or (anomaly_present[ii] == 2)):
                    #generate url
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    #print url
                    print '<a href =%s target="_blank">verify</a></p>' % url
                    
   
    #######################################
    #Daily PEAK Occupancy                      #
    #######################################
    
    if (ndays > 20):
    
        print '<h2 style="color:darkcyan;font-size: 20px;">Daily Peak Anomalies</h2>'
        #data_structure to hold daily peak occupancy of all garages
        contracts_daily_peak=[]
        #go through each garage
        #line_index = 0

        training_garages=[]

        for ii in np.arange(0, len(contracts)):
    
            if((garage_info_occupancy[ii] == 3) or (garage_info_occupancy[ii] == 2)):
                #print "No contract for ", garage_list[i]
                continue
            #data_structure for a single garage
            temp_daily_peak = []
    
            #get day index of the week Sunday -> 0, Monday -> 1 etc.
            day_index = start_date.weekday()
    
            for jj in np.arange(0, ndays):
                day_index = day_index +1
        

                if(day_index == 7):
                    day_index = 0
                    continue
                if(day_index == 6):
                    continue
                else:
                    #we are at the other 5 days of the week, calculate the peak for a day and add
                    lower = jj*24
                    upper = lower+23
            
                    temp_daily_peak.append(np.amax(contracts[ii][lower:upper]))
            
    
            #add the daily peak for the garage of the whole year to 
            #the master list
            contracts_daily_peak.append(temp_daily_peak)
            training_garages.append(ii)
    
        #Anomaly Detection part
        #If contracts are present
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 1)): 

            #hard coded for dealing with just one garage
            anomaly_present = [0] * len(contracts_daily_peak[0])

            #Algorithm 1:  If there are 0 in weekdays, there may be
            # something wrong
            for ii in np.arange(0,len(contracts_daily_peak)):
                for jj in np.arange(0,len(contracts_daily_peak[ii])):
                    if(contracts_daily_peak[ii][jj] == 0):
                        anomaly_present[jj] = 1
        
            #Algorithm 2:  Check for non zero gaps, like previous.
        
            #First, normalize the dataset

            contracts_daily_peak_normalized=[]
            for ii in contracts_daily_peak:
                t=map(float,ii)
                contracts_daily_peak_normalized.append(t/np.amax(t))
            for ii in np.arange(0,len(contracts_daily_peak_normalized)):
                #if ( anomaly_present[i] == 0):
                p25 = np.percentile(contracts_daily_peak_normalized[ii], 25)
                p75 = np.percentile(contracts_daily_peak_normalized[ii], 75)
                iqr = np.subtract(*np.percentile(contracts_daily_peak_normalized[ii], [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                for m in np.arange(0,len(contracts_daily_peak_normalized[ii])):
                    if ((round(contracts_daily_peak_normalized[ii][m],2) < round(lower,2)) or (round(contracts_daily_peak_normalized[ii][m],2) > round(upper, 2))):        
                        anomaly_present[m] = 2
                

            dates = pd.bdate_range(start_date, periods=ndays)
            
            print '<h3 style="font-weight: bold;">Contracts</h3>'
            
            #get the holidays to skip
            years_t=[]
            start_year = start_date.year
            end_year = end_date.year
            
            if (start_year == end_year):
                years_t.append(start_year)
            else:
                years_t.append(start_year)
                years_t.append(end_year)
            for year_t in years_t:
                #filename
                f_name = "holidays"+str(year_t)
                with open(f_name) as f:
                    hdays= f.readlines()
                for mmm in hdays:
                    dt = datetime.strptime(mmm.rstrip('\n'), date_format)
                    holidays.append(str(dt.year)+str(dt.month)+str(dt.day))
            #print holidays    
                
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        val = "con-"+str(garages[i])+"-"+str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Zero gap for %s-%s-%s </label>' % (val, dates[ii].year,dates[ii].month,dates[ii].day)
                if anomaly_present[ii] == 2:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        val = "con-"+str(garages[i])+"-"+str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough"> Gap for %s-%s-%s </label>' % (val, dates[ii].year,dates[ii].month,dates[ii].day)
                if ((anomaly_present[ii] == 1) or (anomaly_present[ii] == 2)):
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        #print url
                        print '<a href =%s target="_blank">verify</a></p>' % url
                


        #Do the same thing for "transients"

        #data_structure to hold daily peak occupancy of all garages
        transients_daily_peak=[]

        #go through each garage

        training_garages=[]

        for ii in np.arange(0, len(transients)):
    
            if((garage_info_occupancy[ii] == 3) or (garage_info_occupancy[ii] == 1)):
                #print "No contract for ", garage_list[i]
                continue
            #data_structure for a single garage
            temp_daily_peak = []
    
            #get day index of the week Sunday -> 0, Monday -> 1 etc.
            day_index = start_date.weekday()
    
            for jj in np.arange(0, ndays):
                day_index = day_index +1
        

                if(day_index == 7):
                    day_index = 0
                    continue
                if(day_index == 6):
                    continue
                else:
                     #we are at the other 5 days of the week, calculate the peak for a day and add
                    lower = jj*24
                    upper = lower+23
  
                    temp_daily_peak.append(np.amax(transients[ii][lower:upper+1]))
            
    
            #add the daily peak for the garage of the whole year to 
            #the master list
            transients_daily_peak.append(temp_daily_peak)
            training_garages.append(ii)
    
    
        #Anomaly Detection part
        #If transients are present
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 2)): 

            #hard coded for dealing with just one garage
            anomaly_present = [0] * len(transients_daily_peak[0])

            #Algorithm 1:  If there are 0 in weekdays, there may be
            # something wrong
            for ii in np.arange(0,len(transients_daily_peak)):
                for jj in np.arange(0,len(transients_daily_peak[ii])):
                    if(transients_daily_peak[ii][jj] == 0):
                        anomaly_present[jj] = 1
        
            #Algorithm 2:  Check for non zero gaps, like previous.


            transients_daily_peak_normalized=[]
            for ii in transients_daily_peak:
                    t=map(float,ii)
                    transients_daily_peak_normalized.append(t/np.amax(t))
            for ii in np.arange(0,len(transients_daily_peak_normalized)):
                 #if ( anomaly_present[i] == 0):
                p25 = np.percentile(transients_daily_peak_normalized[ii], 25)
                p75 = np.percentile(transients_daily_peak_normalized[ii], 75)
                iqr = np.subtract(*np.percentile(transients_daily_peak_normalized[ii], [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                for m in np.arange(0,len(transients_daily_peak_normalized[ii])):
                    if ((round(transients_daily_peak_normalized[ii][m],2) < round(lower,2)) or (round(transients_daily_peak_normalized[ii][m],2) > round(upper, 2))):        
                        anomaly_present[m] = 2
          
        
                dates = pd.bdate_range(start_date, periods=ndays)

            print '<h3 style="font-weight: bold;">Transients</h3>'
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        val = "tran-"+str(garages[i])+"-"+str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Zero gap for %s-%s-%s </label>' % (val, dates[ii].year,dates[ii].month,dates[ii].day)
                if anomaly_present[ii] == 2:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        val = "tran-"+str(garages[i])+"-"+str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">Gap for %s-%s-%s </label>' % (val, dates[ii].year,dates[ii].month,dates[ii].day)
                if ((anomaly_present[ii] == 1) or (anomaly_present[ii] == 2)):
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        #print url
                        print '<a href =%s target="_blank">verify</a></p>' % url
                     
    
    #######################################
    #Daily Occupancy                      #
    #######################################
    

    
########Twitter old begin
    if (ndays > 1):
    
        print '<h2 style="color:darkcyan;font-size: 20px;">Daily Hourly Anomalies</h2>'
        #data structure to hold the hourly data for the given days for
        #the garages
        contracts_daily = []
        transients_daily = []
    
        training_garages_contracts = []
        training_garages_transients = []
    
        #get day index of the week Sunday -> 0, Monday -> 1 etc.
        day_index = start_date.weekday()
    
        #only populate data for the weekdays
        for mm in np.arange(0, len(contracts)):
            if((garage_info_occupancy[mm] == 3) or (garage_info_occupancy[mm] == 2)):
                #print "No contract for ", garage_list[i]
                break
            #data_structure for a single garage
            temp_daily = []
        
            for nn in np.arange(0, ndays):
                day_index = day_index +1
        

                if(day_index == 7):
                    day_index = 0
                    continue
                if(day_index == 6):
                    continue
                else:
                    #we are at the other 5 days of the week, calculate the occupancy for a day and add
                    lower = nn*24
                    upper = lower+23
            
                    temp_daily.append(contracts[mm][lower:upper+1])
        
            contracts_daily.append(temp_daily)
            training_garages_contracts.append(mm)
    
    
        #for transients
        day_index = start_date.weekday()
    
        for kk in np.arange(0, len(transients)):
            if((garage_info_occupancy[kk] == 3) or (garage_info_occupancy[kk] == 1)):
                #print "No contract for ", garage_list[i]
                break
            #data_structure for a single garage
            temp_daily = []
        
            for ll in np.arange(0, ndays):
                day_index = day_index +1
        

                if(day_index == 7):
                    day_index = 0
                    continue
                if(day_index == 6):
                    continue
                else:
                    #we are at the other 5 days of the week, calculate the peak for a day and add
                    lower = ll*24
                    upper = lower+23
            
                    temp_daily.append(transients[kk][lower:upper+1])
        
            transients_daily.append(temp_daily)
            training_garages_transients.append(kk)
    
        #contracts/transients_daily[garage_index][day_index][hour_index]

        #detect anomalies
        #Algorithm: 
    #Treat each data point for a day as a 24-dimensional vector for 24 hours
    #Used SVDD to see which one are outliers
    
#####################
   #twitter detection
    #if contract is present
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 1)):  
        
            for ss in np.arange(0, len(contracts_daily)):

                #contracts_daily[garage_index][day_index][hour_index]
                #get the dates
                dates = pd.bdate_range(start_date, periods=len(contracts_daily[0]))
                #print dates
                data=[]
                hours=[]
 
                index = 0
    
                #hard coding for one garage, sorry
                #ww is a day
                for ww in contracts_daily[0]:
                   
                    #create the hours for that day
                    temp_hours= pd.bdate_range(dates[index], periods=len(ww),freq='H')
                    m=0
                    #ww is a day
                    #for each hour
                    for hr in ww:
                        hours.append(temp_hours[m])
                        data.append(hr)
                        m=m+1
                        #data.append(temp)
                    index = index+1
                    
                print '<h3 style="font-weight: bold;">Contracts</h3>'
                #print len(contracts_daily)
                #print len(contracts_daily[0])
                #print len(contracts_daily[0][0])
                #print len(data)
                #print len(hours)
                #print len(contracts_daily[0])
                #print len(contracts_daily[0][0])
                
                df1 = pd.Series( (v for v in data) )
                results = detect_vec(df1, period = 120,
                            max_anoms=0.02,
                            direction='both')
                temp= results['anoms']

                indices=[]
                for index, row in temp.iterrows():
                    indices.append(row['timestamp'])
                    
                #now indices has all the indices of anomalies in the data.  
                #get the dates now
                result_dates=[]
                for ii in indices:
                    result_dates.append(hours[int(ii)].date())
                    
                #print result_dates
                
                df = pd.DataFrame({'date': result_dates})
                df1=df.drop_duplicates('date')
                
                for row in df1.iterrows():
                    if ((str(row[1].date.year)+str(row[1].date.month)+str(row[1].date.day)) not in holidays):
                        val = "con-"+str(garages[i])+"-"+str(row[1].date.year)+str(row[1].date.month)+str(row[1].date.day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">%s</label>' % (val, str(row[1].date))
                        start_d = str(row[1].date - timedelta(days=40))
                        end_d = str(row[1].date + timedelta(days=40))
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                        #print url
                        print '<a href =%s target="_blank">verify</a></p>' % url
            
                
                
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 2)):  
    
            for ss in np.arange(0, len(transients_daily)):

                #transients_daily[garage_index][day_index][hour_index]
                #get the dates
                dates = pd.bdate_range(start_date, periods=len(transients_daily[0]))
                #print dates
                data=[]
                hours=[]
 
                index = 0
    
                #hard coding for one garage, sorry
                #ww is a day
                for ww in transients_daily[0]:
                   
                    #create the hours for that day
                    temp_hours= pd.bdate_range(dates[index], periods=len(ww),freq='H')
                    m=0
                    #ww is a day
                    #for each hour
                    for hr in ww:
                        hours.append(temp_hours[m])
                        data.append(hr)
                        m=m+1
                        #data.append(temp)
                    index = index+1
                    
                print '<h3 style="font-weight: bold;">Transients</h3>'
                
                df1 = pd.Series( (v for v in data) )
                results = detect_vec(df1, period = 120,
                            max_anoms=0.02,
                            direction='both')
                temp= results['anoms']

                indices=[]
                for index, row in temp.iterrows():
                    indices.append(row['timestamp'])
                    
                #now indices has all the indices of anomalies in the data.  
                #get the dates now
                result_dates=[]
                for ii in indices:
                    result_dates.append(hours[int(ii)].date())
                    
                #print result_dates
                
                df = pd.DataFrame({'date': result_dates})
                df1=df.drop_duplicates('date')
                
                for row in df1.iterrows():
                    if ((str(row[1].date.year)+str(row[1].date.month)+str(row[1].date.day)) not in holidays):
                        val = "tran-"+str(garages[i])+"-"+str(row[1].date.year)+str(row[1].date.month)+str(row[1].date.day)
                        
                        #check if it was previously reported as false positive
                        if val in false_positives:
                            continue
                        print '<p><input type="checkbox" name="color" value="%s"><label class="strikethrough">%s</label>' % (val, str(row[1].date))
                        
                        start_d = str(row[1].date - timedelta(days=40))
                        end_d = str(row[1].date + timedelta(days=40))
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                        #print url
                        print '<a href =%s target="_blank">verify</a></p>' % url            
                
##########Twitter old end
    line_index = line_index + 1

    
print """
<input type="submit" value="Commit Checks" /> 
</form></body>
</html>"""