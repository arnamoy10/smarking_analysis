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

#Google doc stuff
import httplib2

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart' #you can modify it in the 
#API Url

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
garage_dict={}
with open("garage_names") as f:
    for line in f:
        (key, val) = line.split()
        garage_dict[int(key)] = val
    
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
    
#get the garage_names for the IDs
garage_names=[]
for g in garages:
    garage_names.append(garage_dict[int(g)])
    

#print garages
#print start_dates
#print end_dates

print """Content-Type: text/html\n
<html>

<head><meta charset="UTF-8"><title>Smarking checking</title> <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/meyer-reset/2.0/reset.min.css"><link rel='stylesheet prefetch' href='http://fonts.googleapis.com/css?family=Roboto:400,100,300,500,700,900|RobotoDraft:400,100,300,500,700,900'><link rel='stylesheet prefetch' href='http://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'><link rel="stylesheet" href="/css/style.css">
</head>

"""

print """
<body>
<div class="pen-title">
    <p><img src="/logo-s.png"><h2 style="color:darkcyan;font-size: 20px;">Thank you, the error checking results has been saved <a href="https://docs.google.com/spreadsheets/d/1zZ0XS0yDKLK9YkWeimEgv41u-7EP6_YzsyHPp_o-MBs/edit?usp=sharing">here</a> </h2></p></div>
"""

#</html>"""
#sys.exit(0)

#print garage_names
#print garages

#Array to hold if there was data for occupancy present at the garage 
# 0 -> everything present
# 1 -> contract present
# 2 -> transient present
# 3 -> nothing present                  
garage_info_occupancy = [0] * len(garages)

line_index=0


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    credential_dir = os.getcwd()
    credential_path = os.path.join(credential_dir,
                                   'smarking_error_check.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def write_to_google_doc(garage_id):
    """writes to the spreadsheet
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1zZ0XS0yDKLK9YkWeimEgv41u-7EP6_YzsyHPp_o-MBs'
    rangeName = garage_id +'!A2:E'
    #print rangeName
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])

    #get the already present number of rows
    num_rows = 0
    if not values:
        #print('No data found.')
        #placeholder
        xaaa = 0
    else:
        #print('Name, Major:')
        for row in values:
            num_rows = num_rows + 1
            # Print columns
            #print('%s, %s, %s' % (row[0], row[1], row[2]))
    
    #print (num_rows)
    #testing writing
    
    body = {
        'values': anomalies_for_google_docs
    }
    
    result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheetId, range=rangeName,
            valueInputOption='USER_ENTERED', body=body).execute()

#We do one garage at a time so, just one iteration is fine
#TODO: take out the loop and fix indentation

for i in np.arange(0,len(garages)):
    #print "processing ",garages[i]
    #print '<h1 style="color:darkcyan;font-size: 30px;">Garage ID: %s</h1><p></p><p></p>' % str(garages[i])
    contracts=[]
    transients=[]
    
    contracts_duration=[]
    transients_duration=[]
    
    #data structure to filter out overnight anomalies
    #from daily peak anomalies
    daily_peak_anomalies_con = []
    daily_peak_anomalies_tran= []
    
    #GOOGLE DOC datastructure
    anomalies_for_google_docs=[]
    
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
    try:
        garage_info = json.loads(content)
    except ValueError:
        raise ValueError("No JSON Object received, please try again.")
    
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
    
    
    #*************get the duration info***************
    url = "https://my.smarking.net/api/ds/v3/garages/"+str(garages[i])+"/past/duration/between/"+start_dates[i]+"T00:00:00/"+end_dates[i]+"T00:00:00?bucketNumber=25&bucketInSeconds=600&gb=User+Type"
    
    #print url


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
    #print contract
    #print transient
    
    contracts_duration.append(contract)                                          
    transients_duration.append(transient)
    
    
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
        
        #print '<h2 style="color:darkcyan;font-size: 20px;">Monthly Peak Anomalies</h2>'

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
            #print '<h3 style="font-weight: bold;">Contracts</h3>'
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    #create the anomaly and add to master list
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "contract-zero-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
                    
                if anomaly_present[ii] == 2:
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "contract-unusual-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
                    
            
        
    


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
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "transient-zero-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
                    
                if anomaly_present[ii] == 2:
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "transient-unusual-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
                    
   
    #######################################
    #Daily PEAK Occupancy                      #
    #######################################
    
    if (ndays > 20):
    
        #print '<h2 style="color:darkcyan;font-size: 20px;">Daily Peak Anomalies</h2>'
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
            
                #Zero Gap anomaly
                if anomaly_present[ii] == 1:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        temp_anomaly=[]
                        mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                        anom_type = "contracts-zero-daily-peak"
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)
                        
                        #also add the date to the data structure
                        daily_peak_anomalies_con.append(dates[ii].date())
                        
                #Gap anomaly        
                if anomaly_present[ii] == 2:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        temp_anomaly=[]
                        mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                        anom_type = "contracts-unusual-daily-peak"
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)
                        
                        #also add the date to the data structure
                        daily_peak_anomalies_con.append(dates[ii].date())
                


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

            #print '<h3 style="font-weight: bold;">Transients</h3>'
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        temp_anomaly=[]
                        mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                        anom_type = "transients-zero-daily-peak"
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)
                        
                        #also add the date to the data structure
                        daily_peak_anomalies_con.append(dates[ii].date())
                        
                        #also add the date to the data structure
                        daily_peak_anomalies_tran.append(dates[ii].date())
                        
                if anomaly_present[ii] == 2:
                    if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                        temp_anomaly=[]
                        mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                        anom_type = "transients-usual-daily-peak"
                        t_start_d = dates[ii] - timedelta(days=60)
                        t_end_d = dates[ii] + timedelta(days=60)
                    
                        start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                        end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)
                        
                        
                        #also add the date to the data structure
                        daily_peak_anomalies_tran.append(dates[ii].date())
                     
    
    #######################################
    #Daily Occupancy                      #
    #######################################
    

    
########Twitter old begin
    if (ndays > 1):
    
        #print '<h2 style="color:darkcyan;font-size: 20px;">Daily Hourly Anomalies</h2>'
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
                    
                #print '<h3 style="font-weight: bold;">Contracts</h3>'
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
                        temp_anomaly=[]
                        mon = str(row[1].date.year)+"-"+str(row[1].date.month)+"-"+str(row[1].date.day)
                        anom_type = "contracts-unusual-daily"
                        start_d = str(row[1].date - timedelta(days=40))
                        end_d = str(row[1].date + timedelta(days=40))
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)
                        
                        
                        
            
                
                
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
                    
                #print '<h3 style="font-weight: bold;">Transients</h3>'
                
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
                        temp_anomaly=[]
                        mon = str(row[1].date.year)+"-"+str(row[1].date.month)+"-"+str(row[1].date.day)
                        anom_type = "transients-unusual-daily"
                        start_d = str(row[1].date - timedelta(days=40))
                        end_d = str(row[1].date + timedelta(days=40))
                        #generate url
                        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                        temp_anomaly.append(mon)
                        temp_anomaly.append(anom_type)
                        temp_anomaly.append(url)
                        temp_anomaly.append("No")
                        temp_anomaly.append("No")
                        anomalies_for_google_docs.append(temp_anomaly)           
                
##########Twitter old end
    
    ############################
    #   Overnight Occupancy    #
    ############################
    
    #Heuristic:  We calculate the percentage of the number of parkers
    #present during the time 12AM-5AM
    #if there is a high spike in that, we have an anomaly
    #There can be two reasons for this
    #   1.  The whole day is flat so nighttime will be a high percentage (FP)
    #   2.  The whole day is not flat but still a spike in night occupancy
    #TODO:  Eliminate the days where peak daily occupancy is already reported.
    
    if (ndays > 1):
    
        #print '<h2 style="color:darkcyan;font-size: 20px;">Daily Overnight Anomalies</h2>'
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
                    #we are at the other 5 days of the week, calculate the night occupancy 
                    #as percentage of the whole day
                    lower_n = nn*24
                    upper_n = lower_n+5
                    
                    lower = nn*24
                    upper = lower + 23
                    
                    sum_n = np.sum(contracts[mm][lower_n:upper_n+1])
                    sum_all = np.sum(contracts[mm][lower:upper+1])  
            
                    temp_daily.append(sum_n/float(sum_all))
        
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
                    #we are at the other 5 days of the week, calculate the night occupancy 
                    #as percentage of the whole day
                    lower_n = ll*24
                    upper_n = lower_n+5
                    
                    lower = ll*24
                    upper = lower + 23
                    
                    sum_n = np.sum(transients[kk][lower_n:upper_n+1])
                    sum_all = np.sum(transients[kk][lower:upper+1])  
            
                    temp_daily.append(sum_n/float(sum_all))
        
            transients_daily.append(temp_daily)
            training_garages_transients.append(kk)
            
    
        #contracts/transients_daily[garage_index][day_index][hour_index]
#twitter detection
    #if contract is present
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 1)):  
        
            for ss in np.arange(0, len(contracts_daily)):

                #contracts_daily[garage_index][day_index][hour_index]
                #get the dates
                #print dates
                data=[]
                hours=[]
 
                index = 0
    
                #hard coding for one garage, sorry
                #ww is a day
                for ww in contracts_daily[0]:
                   
                    #create the hours for that day
                    #temp_hours= pd.bdate_range(dates[index], periods=len(ww),freq='H')
                    data.append(ww)
                    
                #for lala in data:    
                #    print lala
                    
                #print '<h3 style="font-weight: bold;">Contracts</h3>'
                p25 = np.percentile(data, 25)
                p75 = np.percentile(data, 75)
                iqr = np.subtract(*np.percentile(data, [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                indices = []
                for m in np.arange(0,len(data)):
                    if ((round(data[m],2) < round(lower,2)) or (round(data[m],2) > round(upper, 2))): 
                        indices.append(m)
                        
                #print
                dates = pd.bdate_range(start_date, periods=len(data))
                
                #print indices  
                #print dates[indices]
                for row in dates[indices]:
                    if ((str(row.date().year)+str(row.date().month)+str(row.date().day)) not in holidays):
                        if(row.date() not in daily_peak_anomalies_con):
                            temp_anomaly=[]
                            mon = str(row.date().year)+"-"+str(row.date().month)+"-"+str(row.date().day)
                            anom_type = "contracts-unusual-overnight"
                            start_d = str(row.date() - timedelta(days=3))
                            end_d = str(row.date() + timedelta(days=3))
                            #generate url
                            url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly)
                   
            
                
                
        if((garage_info_occupancy[i] == 0) or (garage_info_occupancy[i] == 2)):  
    
            for ss in np.arange(0, len(transients_daily)):

                #contracts_daily[garage_index][day_index][hour_index]
                #print dates
                data=[]
                hours=[]
 
                index = 0
    
                #hard coding for one garage, sorry
                #ww is a day
                for ww in transients_daily[0]:
                   
                    #create the hours for that day
                    #temp_hours= pd.bdate_range(dates[index], periods=len(ww),freq='H')
                    data.append(ww)
                    
                #for lala in data:    
                #    print lala
                    
                #print '<h3 style="font-weight: bold;">Transients</h3>'
                p25 = np.percentile(data, 25)
                p75 = np.percentile(data, 75)
                iqr = np.subtract(*np.percentile(data, [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                indices = []
                for m in np.arange(0,len(data)):
                    if ((round(data[m],2) < round(lower,2)) or (round(data[m],2) > round(upper, 2))): 
                        indices.append(m)
                        
                #print
                dates = pd.bdate_range(start_date, periods=len(data))
                
                #print indices  
                for row in dates[indices]:
                    if ((str(row.date().year)+str(row.date().month)+str(row.date().day)) not in holidays):
                        if(row.date() not in daily_peak_anomalies_tran):
                            temp_anomaly=[]
                            mon = str(row.date().year)+"-"+str(row.date().month)+"-"+str(row.date().day)
                            anom_type = "transients-unusual-overnight"
                            start_d = str(row.date() - timedelta(days=3))
                            end_d = str(row.date() + timedelta(days=3))
                            #generate url
                            url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly)                    
                
    
    #####################
    #duration anomalies #
    #####################    
         
    sum_t=np.sum(contracts_duration[0])+np.sum(transients_duration[0])
    
    sum_one_hour = 0
    for iii in np.arange(0,6):
        sum_one_hour = sum_one_hour + contracts_duration[0][iii] + transients_duration[0][iii]
        
    sum_ten_minutes = contracts_duration[0][0] + transients_duration[0][0]
    
    percent_one_hour = (sum_one_hour/float(sum_t))*100
    percent_ten_minute = (sum_ten_minutes/float(sum_t))*100
    
    if (percent_one_hour > 60.0):
        temp_anomaly=[]
        mon = str(start_dates[i])+str(end_dates[i])
        anom_type = str(percent_one_hour)+" % one hour parkers"
        start_d = str(start_dates[i])
        end_d = str(row.date() + timedelta(days=3))
        #generate url
        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"duration-distribution?bucketInMinutes=10&fromDateStr="+start_d+"&toDateStr="+end_d
                    
        temp_anomaly.append(mon)
        temp_anomaly.append(anom_type)
        temp_anomaly.append(url)
        temp_anomaly.append("No")
        temp_anomaly.append("No")
        anomalies_for_google_docs.append(temp_anomaly)  
    if (percent_ten_minute > 5.0):
        temp_anomaly=[]
        mon = str(start_dates[i])+str(end_dates[i])
        anom_type = str(percent_ten_minute)+" % ten minute parkers"
        start_d = str(start_dates[i])
        end_d = str(row.date() + timedelta(days=3))
        #generate url
        url = "https://my.smarking.net/rt/"+garage_names[i].rstrip('\n')+"duration-distribution?bucketInMinutes=10&fromDateStr="+start_d+"&toDateStr="+end_d
                    
        temp_anomaly.append(mon)
        temp_anomaly.append(anom_type)
        temp_anomaly.append(url)
        temp_anomaly.append("No")
        temp_anomaly.append("No")
        anomalies_for_google_docs.append(temp_anomaly)
        
    
    
    line_index = line_index + 1

    write_to_google_doc(garages[i])
    #print anomalies_for_google_docs

print """
<p><a href = "../index.html">Go back to home page</a></p>
</body>
</html>"""

