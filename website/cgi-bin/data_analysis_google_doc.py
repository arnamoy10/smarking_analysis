#!/usr/bin/python



import sys

print """Content-Type: text/html\n
<html>

<head><meta charset="UTF-8"><title>Smarking checking</title> <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/meyer-reset/2.0/reset.min.css"><link rel='stylesheet prefetch' href='http://fonts.googleapis.com/css?family=Roboto:400,100,300,500,700,900|RobotoDraft:400,100,300,500,700,900'><link rel='stylesheet prefetch' href='http://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'><link rel="stylesheet" href="/css/style.css">
</head>

"""

print """
<body>
<div class="pen-title">
    <p><img src="/logo-s.png"><h2 style="color:darkcyan;font-size: 20px;">Please hang on while we run our analysis. </h2></p></div>
"""
sys.stdout.flush()
    

#print "Importing libraries"
import cgi, os
import cgitb; cgitb.enable()
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

#STAGE 1: Perform some preprocessing before running main()

form = cgi.FieldStorage()

# Get the garage_name, start and end dates
garage_id = str(form.getfirst('garage_id'))
start_date_supplied = form.getfirst('start_date')
end_date_supplied = form.getfirst('end_date')

    
#get the garage names
garage_name_dict={}
garage_url_dict={}

#check if the master garage_name file exists
if(os.path.isfile('garage_names') != True):
    print "<pstyle='color:darkcyan;font-size: 16px;'>  The garage names list was not found.  Make sure to create one using the add garage link.  </p>"
    sys.exit(0)

with open("garage_names") as f:
    for line in f:
        (key, url, name) = line.split(",")
        garage_name_dict[int(key)] = name
        garage_url_dict[int(key)] = url
        
#check if the supplied garage exits in the master list or not
if int(garage_id.rstrip('\n')) not in garage_name_dict.keys():
    print "<pstyle='color:darkcyan;font-size: 20px;'>  The garage has not been added yet.  Make sure to add it  using the add garage link.  </p>"
    sys.exit(0)
    
    
#data structure for holidays
holidays = []





#get the number of hours, necessary to download occupancy
date_format = "%Y-%m-%d"

    
#get the garage_names for the IDs TODOO
#required for worksheet search and
#creating urls in the spreadsheet
garage_name=garage_name_dict[int(garage_id)]
garage_url=garage_url_dict[int(garage_id)]

    
#Array to hold if there was data for occupancy present at the garage 
# 0 -> everything present
# 1 -> contract present
# 2 -> transient present
# 3 -> nothing present                  
garage_info_occupancy = 0
garage_info_duration = 0

line_index=0

#objects to store the parsed result
contract_occupancy = []
transient_occupancy = []

contract_duration = []
transient_duration = []

#data structure to filter out overnight anomalies
#from daily peak anomalies
daily_peak_anomalies_con = []
daily_peak_anomalies_tran= []

#GOOGLE DOC datastructure
anomalies_for_google_docs=[]

#the supplied start and end date
start_date=datetime.now()
end_date=datetime.now()

#change the authentication token accordingly
headers = {"Authorization":"Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"}


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

def write_to_google_doc(garage_name):
    """writes to the spreadsheet
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1zZ0XS0yDKLK9YkWeimEgv41u-7EP6_YzsyHPp_o-MBs'
    rangeName = garage_name +'!A2:E'
    #print rangeName
    #sys.stdout.flush()
    #result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range=rangeName).execute()
    #values = result.get('values', [])

    #get the already present number of rows
    #num_rows = 0
    #if not values:
        #print('No data found.')
        #placeholder
        #xaaa = 0
    #else:
        #print('Name, Major:')
        #for row in values:
            #num_rows = num_rows + 1
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

 
def get_occupancy_data():
    global headers, contract_occupancy, transient_occupancy, garage_info_occupancy
    
    #get the duration for the supplied date range so that we can create the URL

    start_date = datetime.strptime(start_date_supplied, date_format)
    end_date = datetime.strptime(end_date_supplied, date_format)

    delta= end_date - start_date

    duration_hours = 0
    if delta.days == 0:
        duration_hours = 24
    else:
        duration_hours = (abs(delta.days)+1) * 24
    
    url="https://my.smarking.net/api/ds/v3/garages/"+str(garage_id)+"/past/occupancy/from/"+start_date_supplied+"T00:00:00/"+str(duration_hours)+"/1h?gb=User+Type"

    
    con = 0
    tran = 0

    #get the response using the url
    response = requests.get(url,headers=headers)
    content = response.content

    #see if content was received.  If nothing  received, exit
    if (content == ""):
        print "<br><br><p style='color:darkcyan;font-size: 20px;'>No content received</p>"
        sys.exit(0)


    #we have collected all the data
    #each datapoint is for an hour in a given day
    try:
        garage_info = json.loads(content)
    except ValueError:
        print "<br><br><p style='color:darkcyan;font-size: 20px;'>No JSON Object received for occupancy, please try again.</p>"
        sys.exit(0)
    
    
    #parse the JSON-formatted line
    for item in garage_info["value"]:
        #check if value contains anything
 
        group = str(item.get("group"))
        if('Contract' in group):    
            contract_occupancy = item.get("value")
            con = 1
        if('Transient' in group):
            transient_occupancy = item.get("value")
            tran = 1
    

    if ((con == 0) and (tran == 0)):
        garage_info_occupancy = 3
        print "<br><br><p style='color:darkcyan;font-size: 20px;'>No Occupancy data present for this garage for the given time</p>"
        sys.exit(0)
    if (con == 0):
        l = len(transient_occupancy)
        contract_occupancy = [0] * l
        garage_info_occupancy = 2
    if (tran == 0):
        l = len(contract_occupancy)
        transient_occupancy = [0] * l
        garage_info_occupancy = 1
        

def get_duration_data():
    
    global headers, contract_duration, transient_duration, garage_info_duration, garage_id
    
    #had to add 1 with the end _date because the midnight of the supplied end date goes to
    #end_date + 1
    url = "https://my.smarking.net/api/ds/v3/garages/"+garage_id+"/past/duration/between/"+start_date_supplied+"T00:00:00/"+str((pd.to_datetime(end_date_supplied)+timedelta(1)).date())+"T00:00:00?bucketNumber=25&bucketInSeconds=600&gb=User+Type"

    #get the response using the url
    response = requests.get(url,headers=headers)
    content = response.content

    #see if content was received.  If nothing  received, exit
    if (content == ""):
        print "<p>No content received</p>"
        sys.exit(0)


    #print url
    #we have collected the duration info
    try:
        garage_info = json.loads(content)
    except ValueError:
        print "<br><br><p style='color:darkcyan;font-size: 20px;'>No JSON Object received for duration, please try again.</p>"
        sys.exit(0)
    
    
    con_dur = 0
    tran_dur = 0
    
    #parse the JSON-formatted line
    for item in garage_info["value"]:
        group = str(item.get("group"))
        if('Contract' in group):    
            contract_duration = item.get("value")
            con_dur = 1
        if('Transient' in group):
            transient_duration = item.get("value")
            tran_dur = 1
    

    if ((con_dur == 0) and (tran_dur == 0)):
        garage_info_duration = 3
        print "<p>No duration data for this garage</p>"
        sys.exit(0)
    if (con_dur == 0):
        l = len(transient_duration)
        contract_duration = [0] * l
        garage_info_duration = 2
    if (tran_dur == 0):
        l = len(contract_duration)
        transient_duration = [0] * l
        garage_info_duration = 1        
    

    
def calculate_monthly_peak_anomaly(total_months):
        
        # contracts_occupancy[] and transients_occupancy[] looks like this:
        # [day_1_hour1, day1_hour2, ..., day365_hour24]
        
        #TODO take out the garage_index by removing the loop
        #months_max_occ[month_index][garage_index][contract/transient]
        months_max_occ=[]
    
        #replace the following with one list
        #needed to do total_months+2 for various date perks
        month_occupancies = [[] for ii in range(total_months+2)]
    
        #TODO take out the loop
        for ii in np.arange(0,1):
            #print "for", i
            temp_date = pd.to_datetime(start_date_supplied)
            month_end = pd.to_datetime(start_date)
        
            #index to extract data from the master datastructures
            #e.g contracts and transients
            hour_index = 0
            month_index = 0
            while True:
                #calculate the month end date, so that we can extract data
                month_end = temp_date + relativedelta.relativedelta(day=31)
            
                if(month_end >= end_date):
                    #we are spilling over, get the rest
                    days = (end_date-temp_date).days + 1
                    #TODO take out the following check
                    if (garage_info_occupancy == 3):
                        return
                    else:
                        l = []
                        #print hour_index, days, hour_index+days*24-1
                        l.append(np.amax(contract_occupancy[hour_index:hour_index+days*24]))
                        l.append(np.amax(transient_occupancy[hour_index:hour_index+days*24]))
                        month_occupancies[month_index].append(l)                    
                    break
                else:
                    #keep looping until we have found the end date
                    days = (month_end-temp_date).days + 1
                    #TODO take out the following check
                    if (garage_info_occupancy == 3):
                        return
                    else:
                        l = []
                        #print hour_index, days, hour_index+days*24-1
                        l.append(np.amax(contract_occupancy[hour_index:hour_index+days*24]))
                        l.append(np.amax(transient_occupancy[hour_index:hour_index+days*24]))
                        month_occupancies[month_index].append(l)  
                    
                    #update the hour index
                    hour_index = hour_index + days*24 
                    temp_date = month_end + timedelta(days=1)
                month_index = month_index + 1
            
            for jj in np.arange(0, month_index+1):
                months_max_occ.append(month_occupancies[jj])
                
        #STAGE 3:  Anomaly Detection


        training_data=[]        
                                           
        #dealing with contracts
        if((garage_info_occupancy == 0) or (garage_info_occupancy == 1)):
            #forming the training data set
            #TODO take out the loop
            for ii in np.arange(0, 1):
                #TODO take this condition to the beginning of function
                if((garage_info_occupancy == 3) or (garage_info_occupancy == 2)):
                    #no contract present
                    break
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
            #a value of 1 means zero anomaly and a value of 2 means unusual anomaly
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
                
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    #create the anomaly and add to master list
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "contract-zero-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_urls[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
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
                    url = "https://my.smarking.net/rt/"+garage_urls[i].rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_dates[i]+"&toDateStr="+end_dates[i]
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
                    
        
        
        
        #Do the same thing for Transients
        #TODO Further granularize
        training_data=[]                
                                           
        if((garage_info_occupancy == 0) or (garage_info_occupancy == 2)):
            #forming the training data set
            #make sure to normalize against the mean
            #TODO take out the loop
            for ii in np.arange(0, 1):

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
                        anomaly_present[m] = 2
        
            dates = pd.date_range(start_date, periods=total_months+1, freq='M')
    
    
            for ii in np.arange(0,len(anomaly_present)):
                if anomaly_present[ii] == 1:
                    temp_anomaly=[]
                    mon = str(dates[ii].year)+"-"+str(dates[ii].month)
                    anom_type = "transient-zero-monthly-peak"
                    url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
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
                    url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Monthly&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
                    temp_anomaly.append(mon)
                    temp_anomaly.append(anom_type)
                    temp_anomaly.append(url)
                    temp_anomaly.append("No")
                    temp_anomaly.append("No")
                    anomalies_for_google_docs.append(temp_anomaly)
    
def calculate_daily_peak_anomaly(ndays):
       #data_structure to hold daily peak occupancy of all garages
        contracts_daily_peak=[]

        training_garages=[]
        
        start_date = pd.to_datetime(start_date_supplied)
        end_date = pd.to_datetime(end_date_supplied)

        #TODO take out the following loop
        for ii in np.arange(0, 1):
            if((garage_info_occupancy == 0) or (garage_info_occupancy == 1)):
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
            
                        temp_daily_peak.append(np.amax(contract_occupancy[lower:upper]))
            
    
                #add the daily peak for the garage of the date range to 
                #the master list
                contracts_daily_peak.append(temp_daily_peak)
    
                #Anomaly Detection part

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
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
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
                    
                            #TODO Check, probably we did not use these variables
                            start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                            end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                            #generate url
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
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

        for ii in np.arange(0, 1):
    
            if((garage_info_occupancy == 0) or (garage_info_occupancy == 2)):
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
  
                        temp_daily_peak.append(np.amax(transient_occupancy[lower:upper+1]))
            
    
                #add the daily peak for the garage of the date range to 
                #the master list
                transients_daily_peak.append(temp_daily_peak)

    
    
                #Anomaly Detection part

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

                for ii in np.arange(0,len(anomaly_present)):
                    if anomaly_present[ii] == 1:
                        if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                            temp_anomaly=[]
                            mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                            anom_type = "transients-zero-daily-peak"
                            t_start_d = dates[ii] - timedelta(days=60)
                            t_end_d = dates[ii] + timedelta(days=60)
                        
                            #TODO: check, probably did not use this
                            start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                            end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                            #generate url
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly)
                        
                            #also add the date to the data structure
                            daily_peak_anomalies_tran.append(dates[ii].date())
                            
                    if anomaly_present[ii] == 2:
                        if ((str(dates[ii].year)+str(dates[ii].month)+str(dates[ii].day)) not in holidays):
                            temp_anomaly=[]
                            mon = str(dates[ii].year)+"-"+str(dates[ii].month)+"-"+str(dates[ii].day)
                            anom_type = "transients-unusual-daily-peak"
                            t_start_d = dates[ii] - timedelta(days=60)
                            t_end_d = dates[ii] + timedelta(days=60)
                    
                            start_d = str(t_start_d.year)+"-"+str(t_start_d.month)+"-"+str(t_start_d.day)
                            end_d = str(t_end_d.year)+"-"+str(t_end_d.month)+"-"+str(t_end_d.day)
                    
                            #generate url
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?granularity=Daily&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly)
                        
                        
                            #also add the date to the data structure
                            daily_peak_anomalies_tran.append(dates[ii].date())
    
def calculate_daily_anomaly(ndays):
        #data structure to hold the hourly data for the given days for
        #the garages
        contracts_daily = []
        transients_daily = []

        #TODO make start_date global
        start_date = pd.to_datetime(start_date_supplied)
        end_date = pd.to_datetime(end_date_supplied)
        
        #get day index of the week Sunday -> 0, Monday -> 1 etc.
        day_index = start_date.weekday()
    
        #only populate data for the weekdays
        #TODO take out the next loop
        if((garage_info_occupancy == 0) or (garage_info_occupancy == 1)):
            for mm in np.arange(0, 1):
                #TODO take out the next check
            
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
            
                        temp_daily.append(contract_occupancy[lower:upper+1])
        
                contracts_daily.append(temp_daily)  
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
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly)            
    
        #for transients
        day_index = start_date.weekday()
    
        for kk in np.arange(0, 1):
            if((garage_info_occupancy == 0) or (garage_info_occupancy == 2)):  

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
            
                        temp_daily.append(transient_occupancy[lower:upper+1])
        
                transients_daily.append(temp_daily)
    
                #contracts/transients_daily[garage_index][day_index][hour_index]

                #detect anomalies
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
                            url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                            temp_anomaly.append(mon)
                            temp_anomaly.append(anom_type)
                            temp_anomaly.append(url)
                            temp_anomaly.append("No")
                            temp_anomaly.append("No")
                            anomalies_for_google_docs.append(temp_anomaly) 
    

def calculate_overnight_anomaly(ndays):
       #data structure to hold the hourly data for the given days for
        #the garages
        contracts_daily = []
        transients_daily = []
        
        start_date = pd.to_datetime(start_date_supplied)
        end_date = pd.to_datetime(end_date_supplied)
    
        #get day index of the week Sunday -> 0, Monday -> 1 etc.
        day_index = start_date.weekday()
    
        #only populate data for the weekdays
        #TODO take out the following loop
        for mm in np.arange(0, 1):
            if((garage_info_occupancy == 0) or (garage_info_occupancy == 1)):
                
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
                    
                        sum_n = np.sum(contract_occupancy[lower_n:upper_n+1])
                        sum_all = np.sum(contract_occupancy[lower:upper+1])  
            
                        temp_daily.append(sum_n/float(sum_all))
        
                contracts_daily.append(temp_daily)    
 
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
                                url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                                temp_anomaly.append(mon)
                                temp_anomaly.append(anom_type)
                                temp_anomaly.append(url)
                                temp_anomaly.append("No")
                                temp_anomaly.append("No")
                                anomalies_for_google_docs.append(temp_anomaly)


        #for transients
        day_index = start_date.weekday()
    
        #TODO: take out the following loop
        for kk in np.arange(0, 1):
            if((garage_info_occupancy == 0) or (garage_info_occupancy == 2)):

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
                    
                        sum_n = np.sum(transient_occupancy[lower_n:upper_n+1])
                        sum_all = np.sum(transient_occupancy[lower:upper+1])  
            
                        temp_daily.append(sum_n/float(sum_all))
        
                transients_daily.append(temp_daily)
            
    
                #contracts/transients_daily[garage_index][day_index][hour_index]
                #twitter detection
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
                                url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"/occupancy?occupancyType=regular&fromDateStr="+start_d+"&toDateStr="+end_d
                    
                                temp_anomaly.append(mon)
                                temp_anomaly.append(anom_type)
                                temp_anomaly.append(url)
                                temp_anomaly.append("No")
                                temp_anomaly.append("No")
                                anomalies_for_google_docs.append(temp_anomaly)   

def calculate_duration_anomalies():
    
    if (garage_info_duration == 3):
        return
    #Heuristic:  We calculate the percentage of the number of parkers
    #present during the time 12AM-5AM
    #if there is a high spike in that, we have an anomaly
    #There can be two reasons for this
    #   1.  The whole day is flat so nighttime will be a high percentage (FP)
    #   2.  The whole day is not flat but still a spike in night occupancy
    #TODO:  Eliminate the days where peak daily occupancy is already reported.
    
    if (garage_info_duration == 0):
        sum_t=np.sum(contract_duration)+np.sum(transient_duration)
    
        sum_one_hour = 0
        for iii in np.arange(0,6):
            sum_one_hour = sum_one_hour + contract_duration[iii] + transient_duration[iii]
        
        sum_ten_minutes = contract_duration[0] + transient_duration[0]
    elif (garage_info_duration == 1):
        sum_t=np.sum(contract_duration)
    
        sum_one_hour = 0
        for iii in np.arange(0,6):
            sum_one_hour = sum_one_hour + contract_duration[iii] 
        
        sum_ten_minutes = contract_duration[0] 
    else:
        sum_t=np.sum(transient_duration)
    
        sum_one_hour = 0
        for iii in np.arange(0,6):
            sum_one_hour = sum_one_hour + transient_duration[iii]
        
        sum_ten_minutes = transient_duration[0]
    
    
    percent_one_hour = (sum_one_hour/float(sum_t))*100
    percent_ten_minute = (sum_ten_minutes/float(sum_t))*100
     
    if (percent_one_hour > 60.0):
        temp_anomaly=[]
        mon = str(start_date_supplied)+" "+str(end_date_supplied)
        anom_type = str(percent_one_hour)+" % one hour parkers"

        #generate url
        url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"duration-distribution?bucketInMinutes=10&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
                    
        temp_anomaly.append(mon)
        temp_anomaly.append(anom_type)
        temp_anomaly.append(url)
        temp_anomaly.append("No")
        temp_anomaly.append("No")
        anomalies_for_google_docs.append(temp_anomaly)  
    if (percent_ten_minute > 5.0):
        temp_anomaly=[]
        mon = str(start_date_supplied)+" "+str(end_date_supplied)
        anom_type = str(percent_ten_minute)+" % ten minute parkers"

        #generate url
        url = "https://my.smarking.net/rt/"+garage_url.rstrip('\n')+"duration-distribution?bucketInMinutes=10&fromDateStr="+start_date_supplied+"&toDateStr="+end_date_supplied
                    
        temp_anomaly.append(mon)
        temp_anomaly.append(anom_type)
        temp_anomaly.append(url)
        temp_anomaly.append("No")
        temp_anomaly.append("No")
        anomalies_for_google_docs.append(temp_anomaly)
def main():    
    
    #globals we are using
    global garage_id, garage_info_occupancy, anomalies_for_google_docs, start_date, end_date
    
        
    print "<p style='color:darkcyan;font-size: 22px;'>    Processing Garage", garage_id,"</p>"
    sys.stdout.flush()    
    
    try:
        start_date = datetime.strptime(start_date_supplied, date_format)
        end_date = datetime.strptime(end_date_supplied, date_format)
    except ValueError:
        print "<p style='color:darkcyan;font-size: 20px;'>Incorrect data format, should be YYYY-mm-dd</p>"
        sys.exit(0)

    #check if the from_date is < to_date
    if (start_date > end_date):
        print "<br><br><p style='color:darkcyan;font-size: 20px;'>From_date can't be after to_date</p>"
        sys.exit(0)
        
    #get the holidays
        
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
        if(os.path.isfile(f_name) != True):
            print "<p>%s file not present, needed for analysis</p>"%f_name
            sys.exit(0)
        with open(f_name) as f:
            hdays= f.readlines()
        for mmm in hdays:
            dt = datetime.strptime(mmm.rstrip('\n'), date_format)
            holidays.append(str(dt.year)+str(dt.month)+str(dt.day))  


    
    #STAGE 2: Getting the date
    get_occupancy_data()
    get_duration_data()
    
    
    #if at least not two full months, skip the monthly analysis
    delta= relativedelta.relativedelta(start_date, end_date)
    months = delta.months
    years = delta.years


    total_months = abs(years)*12+abs(months)

    delta= end_date - start_date
    ndays = abs(delta.days)+1
    
    if (total_months > 6):
        calculate_monthly_peak_anomaly(total_months)
                            
    #######################################
    #Daily PEAK Occupancy                      #
    #######################################
    
    if (ndays > 20):
        calculate_daily_peak_anomaly(ndays)
                     
    
    #######################################
    #Daily Occupancy                      #
    #######################################
    #we choose 8 because we need at least 
    #some data points to get signal properties
    if (ndays > 18):
        calculate_daily_anomaly(ndays)
    
    ############################
    #   Overnight Occupancy    #
    ############################
    #we choose 8 because we need at least 
    #some data points to get signal properties
    
    if (ndays > 18):
        calculate_overnight_anomaly(ndays)
    
    #####################
    #duration anomalies #
    #####################    
         
    calculate_duration_anomalies()
    
    argument=str(garage_name.rstrip("\n"))+"_"+str(garage_id.rstrip("\n"))

    write_to_google_doc(argument)



if __name__ == "__main__":   
    main()
    print """
<br><br><h2 style="color:darkcyan;font-size: 20px;">The analysis results can be found <a href="https://docs.google.com/spreadsheets/d/1zZ0XS0yDKLK9YkWeimEgv41u-7EP6_YzsyHPp_o-MBs/edit?usp=sharing" target = _blank>here</a></h2><br><br>
<p><a href = "../index.html">Go back to home page</a></p>
</body>
</html>"""

