import os
import json
import matplotlib.pyplot as plt
import numpy as np
import sys

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn import svm

contracts=[]
transients=[]

#flags to determine whether contracts or transient was found
con = 0
tran = 0



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
    
#contracts[] looks like this:
#[[gar1_day_1_hour1, gar1_day1_hour2, ..., gar1_day365_hour24],
# [gar2_day_1_hour1, gar2_day1_hour2, ..., gar2_day365_hour24]
#    ...
# [garn_day_1_hour1, garn_day1_hour2, ..., garn_day365_hour24]]

#STAGE 2:  Construct the peak occupancy list

#print transients
#for i in np.arange(0, len(contracts)):
#    print contracts[i]
#    print transients[i]
months_max_occ=[]
jan = []
feb = []
mar = []
apr = []
may = []
jun = []
jul = []
aug = []
sep = []
oct = []
nov = []
dec = []

#form the peak occupancy for each month for all the garages

#result
#jan = [[max1_con, max1_tran], [max2_con, max2_tran]...] for n garages
#feb = [[max1_con, max1_tran], [max2_con, max2_tran]...] for n garages

#TODO: different processing scheme for leap year.

for i in np.arange(0, len(contracts)):

    if (garage_info_occupancy[i] == 3):
    #add 0 for no data, we will skip it later anyway
        l = [0,0]
        jan.append(l); feb.append(l); mar.append(l); apr.append(l);may.append(l); jun.append(l); jul.append(l); aug.append(l); sep.append(l);oct.append(l);nov.append(l)
        continue
    l = []
    #jan
    l.append(np.amax(contracts[i][0:31*24]))
    l.append(np.amax(transients[i][0:31*24]))
    jan.append(l)
    #feb                                                                           
    l = []

    l.append(np.amax(contracts[i][31*24+1:60*24]))
    l.append(np.amax(transients[i][31*24+1:60*24]))
    feb.append(l)
    #mar                                                                        
    l = []
    l.append(np.amax(contracts[i][60*24+1:91*24]))
    l.append(np.amax(transients[i][60*24+1:91*24]))
    mar.append(l)
    #apr                                                                        
    l = []
    l.append(np.amax(contracts[i][91*24+1:121*24]))
    l.append(np.amax(transients[i][91*24+1:121*24]))
    apr.append(l)
    #may                                                                        
    l = []
    l.append(np.amax(contracts[i][121*24+1:152*24]))
    l.append(np.amax(transients[i][121*24+1:152*24]))
    may.append(l)
    #jun                
    
    l = []                                                  
    l.append(np.amax(contracts[i][152*24+1:182*24]))
    l.append(np.amax(transients[i][152*24+1:182*24]))
    jun.append(l)
    #jul                                                                        
    l = []
    l.append(np.amax(contracts[i][182*24+1:213*24]))
    l.append(np.amax(transients[i][182*24+1:213*24]))
    jul.append(l)
    #aug                                                                        
    l = []
    l.append(np.amax(contracts[i][213*24+1:244*24]))
    l.append(np.amax(transients[i][213*24+1:244*24]))
    aug.append(l)
    #sep                                                                        
    l = []
    l.append(np.amax(contracts[i][244*24+1:274*24]))
    l.append(np.amax(transients[i][244*24+1:274*24]))
    sep.append(l)
    #oct                                                                        
    l = []
    l.append(np.amax(contracts[i][274*24+1:305*24]))
    l.append(np.amax(transients[i][274*24+1:305*24]))
    oct.append(l)
    #nov                                                                        
    l = []
    l.append(np.amax(contracts[i][305*24+1:335*24]))
    l.append(np.amax(transients[i][305*24+1:335*24]))
    nov.append(l)
    #dec                                                                        
months_max_occ.append(jan)
months_max_occ.append(feb)
months_max_occ.append(mar)
months_max_occ.append(apr)
months_max_occ.append(may)
months_max_occ.append(jun)
months_max_occ.append(jul)
months_max_occ.append(aug)
months_max_occ.append(sep)
months_max_occ.append(oct)
months_max_occ.append(nov)
months_max_occ.append(dec)


#lets plot the peak occupancy just for the verification purpose
#t=[]
#months_max_occ [month_index][garage_index][transient/contract]
#for i in np.arange(0, 11):
#    t.append(months[i][0][0])
#for i in t:
#    print i   

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
    for j in np.arange(0, 11):
        t.append(months_max_occ[j][i][0])
    #normalize
    t1=map(float, t)
    #avoid dividing by zero
    if (np.amax(t1) != 0):
        training_data.append(t1/np.amax(t1))
    else:
        training_data.append(t1)
    training_garages.append(i) 

#training data looks like this:                                                 
#   [[gar1_jan_max, gar1_feb_max, ..., gar1_dec_max],                         
#    [gar2_jan_max, gar2_feb_max, ..., gar2_dec_max],
#     ....                                                                     #    [garn_jan_max, garn_feb_max, ..., garn_dec_max]]
# note that here number of garages in training data will be
# less than that in contracts, because we are only extracting
# garages with contracts

#STAGE 3.1:  Detecting "Gaps" in monthly peak occupancy:

#Algorithm (detecting possible faulty data with 0's):
#  if 0 in max(month) for a garage; REPORT -> severe gap

#Array to hold if there was an anomaly or not                                 
anomaly_present = [0] * len(training_data)

#training_data[garage_index][month_index]
for i in np.arange(0, len(training_data)):
    if 0 in training_data[i]:
        anomaly_present[i] = 1
        #print garage_list[training_garages[i]].rstrip('\n'), "is ", training_data[i]
#Algorithm (detecting non zero gaps):

# If data points fall beyond 3 IQR -> REPORT gap

for i in np.arange(0, len(training_data)):
    #if we did not find 'zero gaps'
    if ( anomaly_present[i] == 0):
        p25 = np.percentile(training_data[i], 25)
        p75 = np.percentile(training_data[i], 75)
        iqr = np.subtract(*np.percentile(training_data[i], [75, 25]))

        #1.5 was too restrictive
        lower = p25 - 3 * (p75 - p25)
        upper = p75 + 3 * (p75 - p25)
    
        for t  in training_data[i]:
            if t < lower or t > upper:
                print t, " is not between ", lower, " and ", upper
                anomaly_present[i] = 2
                break

#print the anomaly results
#  garage_list holds the ID of garages as read from the
# garage_list file
print "Anomaly category 1: Peak Occupancy for Contracts"
print "______________________________________________"

if not os.path.exists("./contracts"):
    os.makedirs("./contracts")
if not os.path.exists("./contracts/zero_gap"):
    os.makedirs("./contracts/zero_gap")
if not os.path.exists("./contracts/gap"):
    os.makedirs("./contracts/gap")


for i in np.arange(0, len(training_data)):
    #if (anomaly_present[i] == 0):
    #    print i, "OK"
    if (anomaly_present[i] == 1):
        #print garage_list[i].rstrip('\n'), " has 'zero gap' anomaly"
        print garage_list[training_garages[i]].rstrip('\n'), " 'zero gap'"
        
        #extract from original dataset for plotting
        k=[]
        for m in np.arange(0,11):
            k.append(months_max_occ[m][training_garages[i]][0])
        plt.ylim(0,np.amax(k))

        plt.plot(k)
        
        #plot
        filename = "./contracts/zero_gap/"+str(garage_list[training_garages[i]].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

    if (anomaly_present[i] == 2):
        print garage_list[training_garages[i]].rstrip('\n'), "'gap'"
        
        #extract from original dataset for plotting
        k=[]
        for m in np.arange(0,11):
            k.append(months_max_occ[m][training_garages[i]][0])
        plt.ylim(0,np.amax(k))

        plt.plot(k)
        
        filename = "./contracts/gap/"+str(garage_list[training_garages[i]].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

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
    for j in np.arange(0, 11):
        t.append(months_max_occ[j][i][1])
    #normalize
    t1=map(float, t)
    
    #avoid dividing by zero
    if (np.amax(t1) != 0):
        training_data.append(t1/np.amax(t1))
    else:
        training_data.append(t1)
    training_garages.append(i)                                                   
                                
anomaly_present = [0] * len(training_data)

for i in np.arange(0, len(training_data)):
    if 0 in training_data[i]:
        anomaly_present[i] = 1

# If data points fall beyond 3 IQR -> REPORT gap

for i in np.arange(0, len(training_data)):
    #if we did not find 'zero gaps'
    if ( anomaly_present[i] == 0):
        p25 = np.percentile(training_data[i], 25)
        p75 = np.percentile(training_data[i], 75)
        iqr = np.subtract(*np.percentile(training_data[i], [75, 25]))

        #1.5 was too restrictive
        lower = p25 - 3 * (p75 - p25)
        upper = p75 + 3 * (p75 - p25)
    
        for t  in training_data[i]:
            if t < lower or t > upper:
                #print t, " is not between ", lower, " and ", upper
                anomaly_present[i] = 2
                break

#print the anomaly results
print "Anomaly category 2: Peak Occupancy for Transients"
print "______________________________________________"

if not os.path.exists("./transients"):
    os.makedirs("./transients")
if not os.path.exists("./transients/zero_gap"):
    os.makedirs("./transients/zero_gap")
if not os.path.exists("./transients/gap"):
    os.makedirs("./transients/gap")
for i in np.arange(0, len(training_data)):
    if (anomaly_present[i] == 1):
        #print garage_list[i].rstrip('\n'), " has 'zero gap' anomaly"
        print garage_list[training_garages[i]].rstrip('\n'), " 'zero gap'"
        #extract from original dataset for plotting
        k=[]
        for m in np.arange(0,11):
            k.append(months_max_occ[m][training_garages[i]][1])
        plt.ylim(0,np.amax(k))

        plt.plot(k)
        
        filename = "./transients/zero_gap/"+str(garage_list[training_garages[i]].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

    if (anomaly_present[i] == 2):
        #print garage_list[i].rstrip('\n'), " has 'gap' anomaly"
        print garage_list[training_garages[i]].rstrip('\n'), "'gap'"
        #extract from original dataset for plotting
        k=[]
        for m in np.arange(0,11):
            k.append(months_max_occ[m][training_garages[i]][1])
        plt.ylim(0,np.amax(k))

        plt.plot(k)
        
        filename = "./transients/gap/"+str(garage_list[training_garages[i]].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

        
#STAGE 3.2:  
#Find anomalies in 1 year of peak occupancy with 1 day view 
# skipping weekends for now

#populate the data for "contracts"
#TODO: make the next variable as an argument
ndays = 335

#data_structure to hold daily peak occupancy of all garages
contracts_daily_peak=[]
#go through each garage
#line_index = 0
for i in np.arange(0, len(contracts)):
    #data_structure for a single garage
    temp_daily_peak = []
    
    if (garage_info_occupancy[i] == 3):
        #for empty garage, it will be all zeros
        zeros = [0] * ndays
        temp_daily_peak.append(zeros)
        continue
    #TODO: determine first day when you start counting from,
    # Jan 1, 2016 was Friday
    day_index = 4
    for j in np.arange(0, 335):
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
    #print "done ", line_index
    #line_index = line_index + 1
    
#print "total garages: ",len(contracts_daily_peak)
#for i in contracts_daily_peak:
#    print len(i)
#print "Garage ", garage_list[1]

#Anomaly Detection part

anomaly_present = [0] * len(contracts_daily_peak)

#Algorithm 1:  If there are 0 in weekdays, there may be
# something wrong
for i in np.arange(0,len(contracts_daily_peak)):
    if 0 in contracts_daily_peak[i]:
        anomaly_present[i] = 1
        
#Algorithm 2:  Check for non zero gaps, like previous.

#TODO:  Did not handle garages where there was no data,
#but we created synthetic data

#TODO: Probably there will be lot of non-zero gaps,
#try to see if there is a pattern, eg the distance between the
#the outliers is more or less same or not

#First, normalize the dataset
#TODO: This can be merged with the previous loop

#TODO: create range of dates for x-axis python
contracts_daily_peak_normalized=[]
for i in contracts_daily_peak:
        t=map(float,i)
        contracts_daily_peak_normalized.append(t/np.amax(t))
for i in np.arange(0,len(contracts_daily_peak_normalized)):
    if ( anomaly_present[i] == 0):
        p25 = np.percentile(contracts_daily_peak_normalized[i], 25)
        p75 = np.percentile(contracts_daily_peak_normalized[i], 75)
        iqr = np.subtract(*np.percentile(contracts_daily_peak_normalized[i], [75, 25]))

        #1.5 was too restrictive
        lower = p25 - 3 * (p75 - p25)
        upper = p75 + 3 * (p75 - p25)
    
        for t  in contracts_daily_peak_normalized[i]:
            if t < lower or t > upper:
                #print t, " is not between ", lower, " and ", upper
                anomaly_present[i] = 2
                break
                
#print the results
print "Anomaly category 3: DAILY Peak Occupancy for Contracts"
print "______________________________________________"

if not os.path.exists("./contracts_daily"):
    os.makedirs("./contracts_daily")
if not os.path.exists("./contracts_daily/zero_gap"):
    os.makedirs("./contracts_daily/zero_gap")
if not os.path.exists("./contracts_daily/gap"):
    os.makedirs("./contracts_daily/gap")
for i in np.arange(0, len(contracts_daily_peak_normalized)):
    if (anomaly_present[i] == 1):
        #print garage_list[i].rstrip('\n'), " has 'zero gap' anomaly"
        print garage_list[i].rstrip('\n'), " 'zero gap'"

        plt.ylim(0,np.amax(contracts_daily_peak[i]))

        plt.plot(contracts_daily_peak[i])
        
        filename = "./contracts_daily/zero_gap/"+str(garage_list[i].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

    if (anomaly_present[i] == 2):
        #print garage_list[i].rstrip('\n'), " has 'gap' anomaly"
        print garage_list[i].rstrip('\n'), "'gap'"

        plt.ylim(0,np.amax(contracts_daily_peak[i]))

        plt.plot(contracts_daily_peak[i])
        
        filename = "./contracts_daily/gap/"+str(garage_list[i].rstrip('\n'))+".png"
        plt.savefig(filename)
        plt.clf()

'''
#STAGE 3.3:  Apply Clustering
#months[month_index][garage_index][transient/contract]

#first algorithm: DBSCAN (automatically detects number of clusters)

training_data=[]

for i in np.arange(0, len(contracts)):
    t = []
    for j in np.arange(0, 11):                                                         t.append(months[j][i][0])
    training_data.append(t)

#training data looks like this:
#   [[gar1_jan_max, gar1_feb_max, ..., gar1_dec_max],
#    [gar2_jan_max, gar2_feb_max, ..., gar2_dec_max],
#     ....
#    [garn_jan_max, garn_feb_max, ..., garn_dec_max]]

#print dim(training_data)
data = np.array(training_data)

#print data
stscaler = StandardScaler().fit(data)
data = stscaler.transform(data)

#print data
db = DBSCAN(eps=0.3, min_samples=1).fit(data)
core_samples = db.core_sample_indices_
labels = db.labels_
print labels
n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
print n_clusters_


#second algorithm: one class SVM (used in text processing for outlier detection)
clf = svm.OneClassSVM(nu=0.95 * 0.25 + 0.05, kernel="rbf", gamma=0.1)
clf.fit(data)
y_pred = clf.predict(data)

print y_pred

#third algorithm:  IsolationForest (same as before)
#what is contamination?

rng = np.random.RandomState(42)

clf = IsolationForest( contamination=0.25, random_state=rng)
clf.fit(data)
y_pred = clf.predict(data)

print y_pred

'''

'''
#STAGE 1:  Getting all the data 
#______________________________

#get hourly data for garages and plot it

#ren, BAFC, Three Allen Center, 500 Jefferson, Jacksonville
garage_ids = [917572, 780376, 118941, 579742, 440959]

#get hourly occupancy starting from Feb 3 2015 to Nov 30 2016
start_date = ["2015-02-03T00:00:00"]
hours_needed = [16008]

#objects to store the results
contracts = []
transients = []

for id in garage_ids:
    for date in start_date:
        for hour in hours_needed:
            #print id
            #creating the curl link for OCCUPANCY
            url = "https://my.smarking.net/api/ds/v3/garages/"
            url = url + str(id)
            url = url + "/past/occupancy/from/"+date+"/"+str(hour)+"/1h?gb=User+Type"
            #print url
            url = 'curl "' + url+ '" -H "Authorization:Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"'
            print url 
            result = os.popen(url).read()
            #print result

            #parse the json file
            garage_info = json.loads(result)

            #objects to store the parsed result
            contract = []
            transient = []
            for item in garage_info["value"]:
                group = str(item.get("group"))
                if('Contract' in group):    
                    contract = item.get("value")
                else:
                    transient = item.get("value")
            
            #add the parsed result to the master list
            contracts.append(contract)
            transients.append(transient)
            #print "contract",contract
            #print "transient",transient
            #plot them
            #x = np.arange(0, len(contract))
            #print x
            #print contract
            #fig = plt.figure()
            #ax = plt.axes()
            #ax.plot(x, contract)
            #ax.plot(x, transient)

            #plt.show()

'''
