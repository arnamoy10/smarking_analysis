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


from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn import svm
from sklearn.cluster import KMeans
import requests

#twitter analysis for timeseries anomaly detection
from pyculiarity import detect_ts


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
            
        for j in np.arange(0, month_index+1):
            months_max_occ.append(month_occupancies[j])
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
#Find anomalies in 1 year of peak occupancy with DAILY view 
# skipping weekends for now

#populate the data for "contracts"



delta= end_date - start_date
ndays = abs(delta.days)+1

if (ndays > 20):
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
            
                temp_daily_peak.append(np.amax(contracts[i][lower:upper]))
            
    
        #add the daily peak for the garage of the whole year to 
        #the master list
        contracts_daily_peak.append(temp_daily_peak)
        training_garages.append(i)
    
    #Anomaly Detection part

    #hard coded for dealing with just one garage
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
    print "________________________________________"
    
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
    
        if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 1)):
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

                temp_daily_peak.append(np.amax(transients[i][lower:upper+1]))
            
    
        #add the daily peak for the garage of the whole year to 
        #the master list
        transients_daily_peak.append(temp_daily_peak)
        training_garages.append(i)
    
    
    #Anomaly Detection part

    #hard coded for dealing with just one garage
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
            
            
#if the number of days is greater than one, do an hourly analysis.

#here, apply clustering to detect anomalies.
if (ndays > 1):
    #print "# days between 1 and 20"
    
    #data structure to hold the hourly data for the given days for
    #the garages
    contracts_daily = []
    transients_daily = []
    
    training_garages_contracts = []
    training_garages_transients = []
    
    #get day index of the week Sunday -> 0, Monday -> 1 etc.
    day_index = start_date.weekday()
    
    #only populate data for the weekdays
    for i in np.arange(0, len(contracts)):
        if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 2)):
            #print "No contract for ", garage_list[i]
            continue
        #data_structure for a single garage
        temp_daily = []
        
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
            
                temp_daily.append(contracts[i][lower:upper+1])
        
        contracts_daily.append(temp_daily)
        training_garages_contracts.append(i)
    
    #print contracts_daily
    
    #for transients
    day_index = start_date.weekday()
    
    for i in np.arange(0, len(transients)):
        if((garage_info_occupancy[i] == 3) or (garage_info_occupancy[i] == 1)):
            #print "No contract for ", garage_list[i]
            continue
        #data_structure for a single garage
        temp_daily = []
        
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
            
                temp_daily.append(transients[i][lower:upper+1])
        
        transients_daily.append(temp_daily)
        training_garages_transients.append(i)
    
    #contracts/transients_daily[garage_index][day_index][hour_index]

    #detect anomalies
    #Algorithm: 
    #Treat each data point for a day as a 24-dimensional vector for 24 hours
    #Used SVDD to see which one are outliers
    
    #print transients_daily
    #print transients
    
    contracts_daily_normalized=[]
    transients_daily_normalized=[]

        
    for i in np.arange(0, len(contracts_daily)):
        for j in contracts_daily[i]:
            t=map(float,j)
            contracts_daily_normalized.append(t/np.amax(t))
        #print contracts_daily_normalized
        
        
        #one class svm (placeholder, as twitter's algo works best)
        clf = svm.OneClassSVM(nu=0.95 * 0.25 + 0.05, kernel="rbf", gamma=0.05)
        clf.fit(contracts_daily_normalized)
        y_pred_svdd = clf.predict(contracts_daily_normalized)
        
        
        #kmeans (placeholder, as twitter's algo works best)
        km = KMeans(n_clusters = 2)
        km.fit(contracts_daily_normalized)
        y_pred_km = km.predict(contracts_daily_normalized)
        
        #print y_pred_km

        #print y_pred.count(1)
        #print y_pred.count(-1)
        '''
        #see which class has more members, that one is dominant and
        #the other is outlier.
        #TODO:  I may be wrong here, simply -1 may mean outlier in y_pred
        ones =  np.count_nonzero(y_pred_km == 1) 
        neg_ones = np.count_nonzero(y_pred_km == 0) 
        
        #create a date range for printing the anomaly results
        dates = pd.bdate_range(start_date, periods=ndays)
        print "Anomaly category 3: DAILY Occupancy"
        print "________________________________________"
        
        print "Contracts:"
        
        if(ones > neg_ones):
            #get the indices of outliers
            indices = np.where(y_pred_km == 0)[0]
            #print the dates where there are anomalies
            for i in indices:
                print dates[i].year, dates[i].month, dates[i].day
        else:
            #get the indices of outliers
            indices = np.where(y_pred_km == 1)[0]
            #print the dates where there are anomalies
            for i in indices:
                print dates[i].year, dates[i].month, dates[i].day
        '''
#####################
   #twitter detection
                
        dates = pd.bdate_range(start_date, periods=len(contracts_daily_normalized))
        data=[]
 
        index = 0
        for i in contracts_daily_normalized:
            temp_hours= pd.bdate_range(dates[index], periods=len(contracts_daily_normalized[0]),freq='H')
            m=0
            
            for t in i:
                temp=[]
                temp.append(temp_hours[m])
                temp.append(t)
                m=m+1
                data.append(temp)
            index = index+1
            
            
        #print data
        twitter_example_data = pd.DataFrame(data)
        #print twitter_example_data
        #twitter_example_data = pd.read_csv('temp_data')
        
        #print twitter_example_data
        
        results = detect_ts(twitter_example_data,
                    max_anoms=0.02,
                    direction='both')
        #print results
        
        temp= results['anoms']
        print 'from twitter, contracts'
        
        #get all the dates so that wnique dates can be extracted
        dates=[]
        for index, row in temp.iterrows():
            dates.append(row['timestamp'].date())
                
    
    #transients
    for i in np.arange(0, len(transients_daily)):
        for j in transients_daily[i]:
            t=map(float,j)
            transients_daily_normalized.append(t/np.amax(t))
        
        #create a date range for printing the anomaly results
        #print "Now"
        #print len(transients_daily_normalized), len(transients_daily_normalized[0])
        dates = pd.bdate_range(start_date, periods=len(transients_daily_normalized))
        #print len(dates)
        index = 0
        for i in transients_daily_normalized:
            hours= pd.bdate_range(dates[index], periods=len(transients_daily_normalized[0]),freq='H')
            m=0
            for t in i:
                #print str(hours[m])+","+str(t)
                m=m+1
            index = index+1
        '''
        #one class svm, gamma did not have an effect on results (placeholder, as twitter's algo works best)
        #clf = svm.OneClassSVM(nu=0.95 * 0.25 + 0.05, kernel="rbf", gamma=0.05)
        #clf.fit(contracts_daily_normalized)
        #y_pred_svdd = clf.predict(contracts_daily_normalized)
        
        
        #kmeans (less # false positives than SVDD, but still a lot) (placeholder, as twitter's algo works best)
        #tol does not have an effect
        km = KMeans(n_clusters = 2)
        km.fit(transients_daily_normalized)
        y_pred_km = km.predict(transients_daily_normalized)
        
        
        #see which class has more members, that one is dominant and
        #the other is outlier.
        #TODO:  I may be wrong here, simply 0 may mean outlier in y_pred
        ones =  np.count_nonzero(y_pred_km == 1) 
        neg_ones = np.count_nonzero(y_pred_km == 0) 
        
        #create a date range for printing the anomaly results
        dates = pd.bdate_range(start_date, periods=ndays)
        
        print "Transients:"
        
        if(ones > neg_ones):
            #get the indices of outliers
            indices = np.where(y_pred_km == 0)[0]
            #print the dates where there are anomalies
            for i in indices:
                print dates[i].year, dates[i].month, dates[i].day
        else:
            #get the indices of outliers
            indices = np.where(y_pred_km == 1)[0]
            #print the dates where there are anomalies
            for i in indices:
                print dates[i].year, dates[i].month, dates[i].day
        '''        
        #twitter detection
                
        dates = pd.bdate_range(start_date, periods=len(transients_daily_normalized))
        data=[]
 
        index = 0
        for i in transients_daily_normalized:
            temp_hours= pd.bdate_range(dates[index], periods=len(transients_daily_normalized[0]),freq='H')
            m=0
            
            for t in i:
                temp=[]
                temp.append(temp_hours[m])
                temp.append(t)
                m=m+1
                data.append(temp)
            index = index+1
            
            
        #print data
        twitter_example_data = pd.DataFrame(data)
        #print twitter_example_data
        #twitter_example_data = pd.read_csv('temp_data')
        
        #print twitter_example_data
        
        results = detect_ts(twitter_example_data,
                    max_anoms=0.02,
                    direction='both')
        #print results
        
        temp= results['anoms']
        print 'from twitter, transients'
        
        #get all the dates so that wnique dates can be extracted
        dates=[]
        for index, row in temp.iterrows():
            dates.append(row['timestamp'].date())
            
        df = pd.DataFrame({'date': dates})
        df1=df.drop_duplicates('date')
        
        for row in df1.iterrows():
            print row['date']
