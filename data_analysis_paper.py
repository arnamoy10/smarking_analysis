import numpy as np
import pandas as pd
import shutil
from datetime import datetime, timedelta
from dateutil import relativedelta
import sys

from sklearn.cluster import DBSCAN

'''
avail_dict = {}
with open(sys.argv[1]) as f:
    for line in f:
        (time,lot,desc,add,zipc,lat,longt,avail,mapx, mapy) = line.split(",")
        avail_dict[pd.to_datetime(time)] = float(avail)
        
    
#file_dates=set(file_dates)

dates = pd.date_range("11/06/2014", periods=365)

final_data_points=[]
for date in dates:
    hours = pd.date_range(date, periods=288,freq='5min')
    
    for hour in hours:
        #print hour
        if hour not in avail_dict.keys():
            final_data_points.append(0)
        else:
            final_data_points.append(avail_dict[hour])
            
f = open("output", "w+")
for d in final_data_points:
    f.write(d)
f.close()
        
#for i in [1,2,3,4,5]:
#    print file_dates[i]
'''

#2nd method
#a lot of misaligned date points
dates = []
avails= []
master_dataset=[]

with open(sys.argv[1]) as f:
    for line in f:
        (time,lot,desc,add,zipc,lat,longt,avail,mapx, mapy) = line.split(",")
        temp = []
        temp.append(pd.to_datetime(time))
        temp.append(float(avail))
        master_dataset.append(temp)

sorted_list = sorted(master_dataset,key=lambda l:l[0])


dates = pd.date_range("01/01/2015", periods=731)
dates_count=[0]*len(dates)

index = 0
for date in dates:
    start = 0
    for item in sorted_list:
        if(item[0].date() == date.date()):
            #print item[0], date
            #found start
            start = 1
            dates_count[index] = dates_count[index]+1
        else:
            if(start == 1):
                break
            else:
                continue
    index = index + 1
    
                
#find the dates that did not have enough data points
p25 = np.percentile(dates_count, 25)
p75 = np.percentile(dates_count, 75)
iqr = np.subtract(*np.percentile(dates_count, [75, 25]))

#1.5 was too restrictive
lower = p25 - 5 * (p75 - p25)
upper = p75 + 5 * (p75 - p25)

#filter out the outlier dates and get the workable dates
workable_dates = []    
for m in np.arange(0,len(dates_count)):
    if ((round(dates_count[m],2) < round(lower,2)) or (round(dates_count[m],2) > round(upper, 2))):
        #we have found an outlier, continue
        continue
    #not outlier, add to working dates
    workable_dates.append(dates[m].date())

#construct the data structure for the dates
training_data = []

for w_d in workable_dates:
    temp=[]
    start = 0
    for item in sorted_list:
        if(item[0].date() == w_d):
            #print item[0], date
            #found start
            start = 1
            temp.append(item[1])
        else:
            if(start == 1):
                break
            else:
                continue 
    training_data.append(temp)

#training date looks like the following
#training_data[] = [day_index][minute_index]

print (len(training_data))
#for item in training_data:
#    print len(item)
    
'''
f = open("output", "w+")
for d in sorted_list:
    f.write(str(d[0])+","+str(d[1])+"\n")
f.close()
'''        


    