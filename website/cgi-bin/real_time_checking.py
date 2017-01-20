import datetime, threading
import numpy as np
import requests
import json

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

def check_error_real_time():
    global time
    global garage_info_occupancy
    global contracts
    global transients
    
    
    if (time == tick):
        #calculate anomalies
        print 'time to calculate anomaies'
        print "contracts ",contracts
        print "transients ",transients
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
                    print 'setting con value ', float(item.get("value")), "at ",line_index, time
                    con = 1
                if('Transient' in group):
                    transients.itemset((line_index, time), float(item.get("value")))
                    print 'setting tran value ', float(item.get("value")), "at ",line_index, time
                    tran = 1
    

            if ((con == 0) and (tran == 0)):
                garage_info_occupancy[line_index] = 3
                print "no data for ", line_index
                line_index = line_index + 1
                continue
            if (con == 0):
                contracts.itemset((line_index, time), 0.0)
                print 'setting con value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 2
            if (tran == 0):
                transients.itemset((line_index, time), 0.0)
                print 'setting tran value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 1
                
                
            line_index = line_index + 1
            
        #temp_values.append(val)
    time = time + 1
    threading.Timer(5, check_error_real_time).start()

check_error_real_time()