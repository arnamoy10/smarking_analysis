import sys
    
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
    
print "Analyzing data..."
#we have collected all the data in a file, total 8040 datapoints per garage
#each datapoint is for an hour in a given day
#get the garage names                                                           
with open("garage_list_small") as f:
    garage_list = f.readlines()
with open("smarking_occupancy_small") as f:
    content = f.readlines()

#Array to hold if there was data for occupancy present at the garage 
# 0 -> everything present
# 1 -> contract present
# 2 -> transient present
# 3 -> nothing present                  
garage_info_occupancy = [0] * len(content)

line_index=0

for line in content:
#parse each line, each line is in json format
    #print line
    garage_info = json.loads(line)
    
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
date_format = "%Y-%m-%d"

start_date = datetime.strptime('2016-01-01', date_format)
end_date = datetime.strptime('2016-10-30', date_format)


delta= relativedelta.relativedelta(start_date, end_date)
months = delta.months
years = delta.years


total_months = abs(years)*12+abs(months)


if (total_months > 6):

    all_max_occupancy=[]
    
    
    for i in np.arange(0,len(contracts)):
        
        #replace the following with one list
        #needed to do total_months+2 for various date perks
        month_occupancies = [[] for k in range(total_months+1)]
        
        months_max_occ=[]

        #print "for", i
        temp_date = start_date
        month_end =  start_date
        
        #index to extract data from the master datastructures
        #e.g contracts and transients
        hour_index = 0
        month_index = 0
        
        #TODO:  Check the following algo, somehow missing the last month
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
        
        #print "Done, month index is", month_index
        for j in np.arange(0, month_index+1):
            months_max_occ.append(month_occupancies[j])
            
        all_max_occupancy.append(months_max_occ)
    
    #print all_max_occupancy
    #all_max_occupancy[garage_id][month_id][0][contract/transient]
    
    
    #CONTRACTS
    #form the training vector after normalizing
    #x = [[gar1_first_month, gar1_second_month,..gar1_last_month],
    #     [gar2_first_month, gar2_second_month,..gar2_last_month] etc.]
    training_garages=[]
    x=[]
    for i in np.arange(0, len(contracts)):
        #temp array to hold peak for all months
        temp=[]
        if (garage_info_occupancy[i] == 3 or garage_info_occupancy[i] == 2):
            continue
        for j in np.arange(0,len(all_max_occupancy[i])):
            temp.append(all_max_occupancy[i][j][0][0])
        temp1=map(float, temp)
        temp = temp1/np.amax(temp1)
        x.append(temp)
        training_garages.append(i)
    
    db = DBSCAN(eps=0.3, min_samples=1).fit(x)
    core_samples = db.core_sample_indices_
    labels = db.labels_
    print labels
    #print training_garages
    
    