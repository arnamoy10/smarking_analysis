import os
import json
import matplotlib.pyplot as plt
import numpy as np


#STAGE 1:  Getting all the data 
#______________________________

#get hourly data for garages and plot it

#ren, BAFC, Three Allen Center, 500 Jefferson, Jacksonville, Calhoun (faulty)
#
garage_ids = [917572, 780376, 118941, 579742, 440959, 777367]

#get hourly occupancy starting from Feb 3 2015 to Nov 30 2016
start_date = ["2015-02-03T00:00:00"]
hours_needed = [16008]

#objects to store the results
contracts = []
transients = []
peak_occupancy = []

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
            #print url 
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

