import datetime, threading
import numpy as np
import requests
import json
from datetime import datetime

#get the garage names
garage_dict={}
with open("garage_names") as f:
    for line in f:
        (key, val) = line.split()
        garage_dict[int(key)] = val

time  = 0
temp_values = []

#define a tick when to calculate anomalies
tick = 5

contracts=np.ndarray((len(garage_dict), tick))
transients=np.ndarray((len(garage_dict), tick))



garage_info_occupancy=[0]*len(garage_dict)
anomalies=[]

def check_error_real_time():
    global time
    global garage_info_occupancy
    global contracts
    global transients
    global anomalies
    
    
    if (time == tick):
        #calculate anomalies
        #print 'time to calculate anomaies'
        #print "contracts ",contracts
        #print "transients ",transients
        
        for ii in np.arange(0, len(garage_dict)):
            if (garage_info_occupancy[ii] == 3):
                #print "No data for ", garage_dict.keys()[ii]
                continue
            if ((garage_info_occupancy[ii] == 0) or (garage_info_occupancy[ii] == 1)):
                #analyze contracts
                #print "Analyzing contracts for ", garage_dict.keys()[ii]
                p25 = np.percentile(contracts[ii], 25)
                p75 = np.percentile(contracts[ii], 75)
                iqr = np.subtract(*np.percentile(contracts[ii], [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                for m in np.arange(0,len(contracts[ii])):
                    #print "comparing ",round(transients[ii][m],2), " with ", round(lower,2), " and ", round(upper,2)
                    if ((round(contracts[ii][m],2) >= round(lower,2)) or (round(contracts[ii][m],2) <= round(upper, 2))):
                        temp=[]
                        temp.append(garage_dict.keys()[ii])
                        temp.append(str(datetime.now().date()))
                        temp.append(str(datetime.now().time()))
                        temp.append(str(datetime.now().time().hour))
                        temp.append("Contract")
                        anomalies.append(temp)
            if ((garage_info_occupancy[ii] == 0) or (garage_info_occupancy[ii] == 2)):
                #analyze transients
                #print "Analyzing transients for ", garage_dict.keys()[ii]
                p25 = np.percentile(transients[ii], 25)
                p75 = np.percentile(transients[ii], 75)
                iqr = np.subtract(*np.percentile(transients[ii], [75, 25]))

                #1.5 was too restrictive
                lower = p25 - 3 * (p75 - p25)
                upper = p75 + 3 * (p75 - p25)
    
                for m in np.arange(0,len(transients[ii])):
                    #print "comparing ",round(transients[ii][m],2), " with ", round(lower,2), " and ", round(upper,2)
                    if ((round(transients[ii][m],2) >= round(lower,2)) or (round(transients[ii][m],2) <= round(upper, 2))):
                        temp=[]
                        temp.append(garage_dict.keys()[ii])
                        temp.append(str(datetime.now().time()))
                        temp.append(str(datetime.now().time().hour))
                        temp.append("Transient")
                        anomalies.append(temp)
                        
        
        #Done analyzing anomalies, all the data is in the anomalies structure
        print "Anomalies"
        print anomalies
        
        #save it to google drive
        #for ii in anomalies:
            
        #Reset anomalies
        anomalies = []
        #reset timer
        time = 0

    else:
        #keep adding the values
        line_index = 0
        for i in garage_dict:
            #print i
            con = 0
            tran = 0
            url="https://my.smarking.net/api/ds/v3/garages/"+str(i)+"/current/occupancy?gb=User+Type"
            #print url
            #change the authentication token accordingly
            headers = {"Authorization":"Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"}

            #get the response using the url
            response = requests.get(url,headers=headers)
            content = response.content
            
            #see if content was received.  If nothing  received, exit
            if (content == ""):
                print "<p>No content received</p>"
                continue

            #we have collected all the data
            #each datapoint is for an hour in a given day
            try:
                garage_info = json.loads(content)
            except ValueError:
                raise ValueError("No JSON Object received, please try again.")
    
    
            #print i,garage_info
    
            #parse the JSON-formatted line
            for item in garage_info["value"]:
                group = str(item.get("group"))
                if('Contract' in group):  
                    contracts.itemset((line_index, time), float(item.get("value")))
                    #print 'setting con value ', float(item.get("value")), "at ",line_index, time
                    con = 1
                if('Transient' in group):
                    transients.itemset((line_index, time), float(item.get("value")))
                    #print 'setting tran value ', float(item.get("value")), "at ",line_index, time
                    tran = 1
    

            if ((con == 0) and (tran == 0)):
                garage_info_occupancy[line_index] = 3
                #print "no data for ", line_index
                line_index = line_index + 1
                continue
            if (con == 0):
                contracts.itemset((line_index, time), 0.0)
                #print 'setting con value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 2
            if (tran == 0):
                transients.itemset((line_index, time), 0.0)
                #print 'setting tran value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 1
                
                
            line_index = line_index + 1
            
        #temp_values.append(val)
    time = time + 1
    threading.Timer(5, check_error_real_time).start()

check_error_real_time()