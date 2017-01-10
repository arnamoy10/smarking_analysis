import sys

if (len(sys.argv) < 3):
    print "Usage: python data_analysis.py garage_id from_date to_date"
    print "Please provide the dates in YYYY-mm-dd format"
    sys.exit(0)
    
print "Importing libraries"
import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shutil
from datetime import datetime, timedelta
from dateutil import relativedelta


#from sklearn.cluster import DBSCAN
#from sklearn.preprocessing import StandardScaler
#from sklearn import svm
import requests


contracts=[]
transients=[]


#flags to determine whether contracts or transient was found
con = 0
tran = 0

#STAGE 1: get data
    
#get the number of hours, necessary to download occupancy
date_format = "%Y-%m-%d"

try:
    datetime.strptime(sys.argv[2], date_format)
    datetime.strptime(sys.argv[3], date_format)
except ValueError:
    raise ValueError("Incorrect data format, should be YYYY-mm-dd")
    
start_date = datetime.strptime(sys.argv[2], date_format)
end_date = datetime.strptime(sys.argv[3], date_format)

#check if the from_date is < to_date
if (start_date > end_date):
    print "From_date can't be after to_date"
    sys.exit(0)

delta= end_date - start_date

duration_hours = 0
if delta.days == 0:
    duration_hours = 24
else:
    duration_hours = (abs(delta.days)+1) * 24

#change the authentication token accordingly
headers = {"Authorization":"Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"}

#create the URL
url="https://my.smarking.net/api/ds/v3/garages/"+str(sys.argv[1])+"/past/occupancy/from/"+sys.argv[2]+"T00:00:00/"+str(duration_hours)+"/1h?gb=User+Type"

#print url

#get the response using the url
response = requests.get(url,headers=headers)
content = response.content

#print content
#see if content was received.  If nothing  received, exit
if (content == ""):
    print "No content received"
    sys.exit(0)


print "Analyzing data..."
#we have collected all the data
#each datapoint is for an hour in a given day
#get the garage names                                                           
#with open("garage_list_small") as f:
#    garage_list = f.readlines()
#with open("smarking_occupancy_small") as f:
#    content = f.readlines()

#Array to hold if there was data for occupancy present at the garage 
# 0 -> everything present
# 1 -> contract present
# 2 -> transient present
# 3 -> nothing present                  
garage_info_occupancy = [0] * 1

line_index=0

#We do one garage at a time so, just one iteration is fine
#TODO: take out the loop and fix indentation
for i in [0]:
#parse each line, each line is in json format
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
        elif('Transient' in group):
            transient = item.get("value")
            tran = 1

    if ((con == 0) and (tran == 0)):
        garage_info_occupancy[line_index] = 3
        #print "no data for ", line_index
        line_index = line_index + 1
        #continue
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
    
    #reset the values of flags
    con = 0
    tran = 0

    #print "done ",line_index
    line_index =  line_index + 1
    
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


if (total_months > 6):

    months_max_occ=[]
    
    #replace the following with one list
    #needed to do total_months+2 for various date perks
    month_occupancies = [[] for i in range(total_months+2)]
    
    for i in np.arange(0,len(contracts)):
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
                if (garage_info_occupancy[i] == 3):
                    #add 0 for no data, we will skip it later anyway
                    l = [0,0]
                    month_occupancies[month_index].append(l)
                else:
                    l = []
                    #print hour_index, days, hour_index+days*24-1
                    l.append(np.amax(contracts[i][hour_index:hour_index+days*24]))
                    l.append(np.amax(transients[i][hour_index:hour_index+days*24]))
                    month_occupancies[month_index].append(l)                    
                break
            else:
                #keep looping until we have found the end date
                days = (month_end-temp_date).days + 1
                if (garage_info_occupancy[i] == 3):
                    #add 0 for no data, we will skip it later anyway
                    l = [0,0]
                    month_occupancies[month_index].append(l)
                else:
                    l = []
                    #print hour_index, days, hour_index+days*24-1
                    l.append(np.amax(contracts[i][hour_index:hour_index+days*24]))
                    l.append(np.amax(transients[i][hour_index:hour_index+days*24]))
                    month_occupancies[month_index].append(l)  
                    
                #update the hour index
                hour_index = hour_index + days*24 
                temp_date = month_end + timedelta(days=1)
            month_index = month_index + 1
            
        for i in np.arange(0, month_index+1):
            months_max_occ.append(month_occupancies[i])
        #print months_max_occ
  
    #STAGE 3:  Anomaly Detection


    #list that holds the training data
    training_data=[]        
    #list that holds indices of garages in the
    #training data from the master garage
    training_garages=[] 
                                           
    #dealing with contracts
    #forming the training data set
    for i in np.arange(0, len(contracts)):
        if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 2)):
            #print "No contract for ", garage_list[i]
            continue
        t = []                                      
        for j in np.arange(0, total_months+1):
            t.append(months_max_occ[j][i][0])
            #normalize
        t1=map(float, t)
        #avoid dividing by zero
        if (np.amax(t1) != 0):
            training_data.append(t1/np.amax(t1))
        else:
            training_data.append(t1)

    #training data looks like this:                                                 
    #   [[gar1_jan_max, gar1_feb_max, ..., gar1_dec_max]],                         

    #STAGE 3.1:  Detecting "Gaps" in monthly peak occupancy:

    #Algorithm (detecting possible faulty data with 0's):
    #  if 0 in max(month) for a garage; REPORT -> severe gap

    #Array to hold if there was an anomaly or not for a month
    #we have one flag per month
    anomaly_present = [0] * len(training_data[i])

    #training_data[garage_index][month_index]
    for i in np.arange(0, len(training_data)):
        for m in np.arange(0,len(training_data[i])):
            if (0 == training_data[i][m]):
                anomaly_present[m] = 1
        #Algorithm (detecting non zero gaps):

    # If data points fall beyond 3 IQR -> REPORT gap

    for i in np.arange(0, len(training_data)):
        p25 = np.percentile(training_data[i], 25)
        p75 = np.percentile(training_data[i], 75)
        iqr = np.subtract(*np.percentile(training_data[i], [75, 25]))

        #1.5 was too restrictive
        lower = p25 - 3 * (p75 - p25)
        upper = p75 + 3 * (p75 - p25)
    
        for m in np.arange(0,len(training_data[i])):
            if ((round(training_data[i][m],2) < round(lower,2)) or (round(training_data[i][m],2) > round(upper, 2))):
                        #print training_data[i][m], " is not between ", lower, " and ", upper
                        anomaly_present[m] = 2

    #print the anomaly results
    #  garage_list holds the ID of garages as read from the
    # garage_list file
    print "Anomaly category 1: MONTHLY Peak Occupancy"
    print "__________________________________________"
    
    dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    for i in np.arange(0,len(anomaly_present)):
        if anomaly_present[i] == 1:
            print "Zero gap Contract for",dates[i].month,dates[i].year
        if anomaly_present[i] == 2:
            print "Gap Contract for ",dates[i].month,dates[i].year
            

    #Do the same thing for Transients
    training_data=[]        
    training_garages=[]           
                                           
    #dealing with transients
    #forming the training data set
    #make sure to normalize against the mean
    for i in np.arange(0, len(transients)):
        if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 1)):
            continue
        t = []                                      
        for j in np.arange(0, total_months+1):
            t.append(months_max_occ[j][i][1])
        #normalize            
        t1=map(float, t)
    
        #avoid dividing by zero
        if (np.amax(t1) != 0):
            training_data.append(t1/np.amax(t1))
        else:
            training_data.append(t1)
        training_garages.append(i)                                                   
                                
    
    
    anomaly_present = [0] * len(training_data[i])

    #training_data[garage_index][month_index]
    for i in np.arange(0, len(training_data)):
        for m in np.arange(0,len(training_data[i])):
            if (0 == training_data[i][m]):
                anomaly_present[m] = 1
        #Algorithm (detecting non zero gaps):

    # If data points fall beyond 3 IQR -> REPORT gap

    for i in np.arange(0, len(training_data)):
        p25 = np.percentile(training_data[i], 25)
        p75 = np.percentile(training_data[i], 75)
        iqr = np.subtract(*np.percentile(training_data[i], [75, 25]))

        #1.5 was too restrictive
        lower = p25 - 3 * (p75 - p25)
        upper = p75 + 3 * (p75 - p25)
    
        for m in np.arange(0,len(training_data[i])):
            if ((round(training_data[i][m],2) < round(lower,2)) or (round(training_data[i][m],2) > round(upper, 2))):
                        #print training_data[i][m], " is not between ", lower, " and ", upper
                        anomaly_present[m] = 2

    #print the anomaly results
    #  garage_list holds the ID of garages as read from the
    # garage_list file
    
    dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    for i in np.arange(0,len(anomaly_present)):
        if anomaly_present[i] == 1:
            print "Zero gap Transient for ",dates[i].month,dates[i].year
        if anomaly_present[i] == 2:
            print "Gap Transient for ",dates[i].month,dates[i].year



#STAGE 3.2:  
#Find anomalies in 1 year of peak occupancy with 1 day view 
# skipping weekends for now

#populate the data for "contracts"

delta= end_date - start_date
ndays = abs(delta.days)+1

#print ndays

#data_structure to hold daily peak occupancy of all garages
contracts_daily_peak=[]
#go through each garage
#line_index = 0

training_garages=[]

for i in np.arange(0, len(contracts)):
    
    if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 2)):
        #print "No contract for ", garage_list[i]
        continue
    #data_structure for a single garage
    temp_daily_peak = []
    
    #get day index of the week Sunday -> 0, Monday -> 1 etc.
    day_index = start_date.weekday()
    
    for j in np.arange(0, ndays):
        day_index = day_index +1
        

        if(day_index == 7):
            day_index = 0
            continue
        if(day_index == 6):
            continue
        else:
            #we are at the other 5 days of the week, calculate the peak for a day and add
            lower = j*24
            upper = lower+23
            
            #print len(contracts[i])
            #print lower, upper
            temp_daily_peak.append(np.amax(contracts[i][lower:upper]))
            
    
    #add the daily peak for the garage of the whole year to 
    #the master list
    contracts_daily_peak.append(temp_daily_peak)
    training_garages.append(i)
    #print "done ", line_index
    #line_index = line_index + 1
    
#print contracts_daily_peak
    
#Anomaly Detection part

#har coded for dealing with just one garage
anomaly_present = [0] * len(contracts_daily_peak[0])

#Algorithm 1:  If there are 0 in weekdays, there may be
# something wrong
for i in np.arange(0,len(contracts_daily_peak)):
    for j in np.arange(0,len(contracts_daily_peak[i])):
        if(contracts_daily_peak[i][j] == 0):
            anomaly_present[j] = 1
        
#Algorithm 2:  Check for non zero gaps, like previous.

#TODO:  Did not handle garages where there was no data,
#but we created synthetic data (added, but double check later)

#TODO: Probably there will be lot of non-zero gaps,
#try to see if there is a pattern, eg the distance between the
#the outliers is more or less same or not

#First, normalize the dataset
#TODO: This can be merged with the previous loop

contracts_daily_peak_normalized=[]
for i in contracts_daily_peak:
        t=map(float,i)
        contracts_daily_peak_normalized.append(t/np.amax(t))
for i in np.arange(0,len(contracts_daily_peak_normalized)):
    #if ( anomaly_present[i] == 0):
    p25 = np.percentile(contracts_daily_peak_normalized[i], 25)
    p75 = np.percentile(contracts_daily_peak_normalized[i], 75)
    iqr = np.subtract(*np.percentile(contracts_daily_peak_normalized[i], [75, 25]))

        #1.5 was too restrictive
    lower = p25 - 3 * (p75 - p25)
    upper = p75 + 3 * (p75 - p25)
    
    for m in np.arange(0,len(contracts_daily_peak_normalized[i])):
        if ((round(contracts_daily_peak_normalized[i][m],2) < round(lower,2)) or (round(contracts_daily_peak_normalized[i][m],2) > round(upper, 2))):        
                anomaly_present[m] = 2
                

dates = pd.bdate_range(start_date, periods=ndays)

print "Anomaly category 2: DAILY Peak Occupancy"
print "______________________________________________"
    
for i in np.arange(0,len(anomaly_present)):
    if anomaly_present[i] == 1:
        print "Zero gap Contract for ",dates[i].day, dates[i].month,dates[i].year
    if anomaly_present[i] == 2:
        print "Gap Contract for ",dates[i].day, dates[i].month,dates[i].year
                


#Do the same thing for "transients"

#data_structure to hold daily peak occupancy of all garages
transients_daily_peak=[]

#go through each garage

training_garages=[]

for i in np.arange(0, len(transients)):
    
    if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 2)):
        #print "No contract for ", garage_list[i]
        continue
    #data_structure for a single garage
    temp_daily_peak = []
    
    #get day index of the week Sunday -> 0, Monday -> 1 etc.
    day_index = start_date.weekday()
    
    for j in np.arange(0, ndays):
        day_index = day_index +1
        

        if(day_index == 7):
            day_index = 0
            continue
        if(day_index == 6):
            continue
        else:
            #we are at the other 5 days of the week, calculate the peak for a day and add
            lower = j*24
            upper = lower+23
            
            #print len(contracts[i])
            #print lower, upper
            temp_daily_peak.append(np.amax(transients[i][lower:upper]))
            
    
    #add the daily peak for the garage of the whole year to 
    #the master list
    transients_daily_peak.append(temp_daily_peak)
    training_garages.append(i)
    
    
#Anomaly Detection part

#har coded for dealing with just one garage
anomaly_present = [0] * len(transients_daily_peak[0])

#Algorithm 1:  If there are 0 in weekdays, there may be
# something wrong
for i in np.arange(0,len(transients_daily_peak)):
    for j in np.arange(0,len(transients_daily_peak[i])):
        if(transients_daily_peak[i][j] == 0):
            anomaly_present[j] = 1
        
#Algorithm 2:  Check for non zero gaps, like previous.

#TODO:  Did not handle garages where there was no data,
#but we created synthetic data (added, but double check later)

#TODO: Probably there will be lot of non-zero gaps,
#try to see if there is a pattern, eg the distance between the
#the outliers is more or less same or not

#First, normalize the dataset
#TODO: This can be merged with the previous loop

transients_daily_peak_normalized=[]
for i in transients_daily_peak:
        t=map(float,i)
        transients_daily_peak_normalized.append(t/np.amax(t))
for i in np.arange(0,len(transients_daily_peak_normalized)):
    #if ( anomaly_present[i] == 0):
    p25 = np.percentile(transients_daily_peak_normalized[i], 25)
    p75 = np.percentile(transients_daily_peak_normalized[i], 75)
    iqr = np.subtract(*np.percentile(transients_daily_peak_normalized[i], [75, 25]))

        #1.5 was too restrictive
    lower = p25 - 3 * (p75 - p25)
    upper = p75 + 3 * (p75 - p25)
    
    for m in np.arange(0,len(transients_daily_peak_normalized[i])):
        if ((round(transients_daily_peak_normalized[i][m],2) < round(lower,2)) or (round(transients_daily_peak_normalized[i][m],2) > round(upper, 2))):        
                anomaly_present[m] = 2
                

dates = pd.bdate_range(start_date, periods=ndays)


for i in np.arange(0,len(anomaly_present)):
    if anomaly_present[i] == 1:
        print "Zero gap Transient for ",dates[i].day, dates[i].month,dates[i].year
    if anomaly_present[i] == 2:
        print "Gap Transient for ",dates[i].day, dates[i].month,dates[i].year