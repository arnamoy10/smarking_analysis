import datetime, threading
import numpy as np
import requests
import json
from datetime import datetime, timedelta

#get the garage names
garage_dict={}
with open("garage_list") as f:
    for line in f:
        (key, x, val) = line.split()
        garage_dict[int(key)] = val

time  = 0
temp_values = []

#define a tick when to calculate anomalies
tick = 4

contracts=np.ndarray((len(garage_dict), tick))
transients=np.ndarray((len(garage_dict), tick))

#also store the times when the sample was taken
contracts_time=np.ndarray((len(garage_dict), tick),dtype=object)
transients_time=np.ndarray((len(garage_dict), tick),dtype=object)

#change the authentication token accordingly
headers = {"Authorization":"Bearer vgrh8F1EuhQdVO2A1wQdCPFf38WHDHX-lXJR-2Dt"}



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
        print datetime.now(), ' time to calculate anomaies'
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
                    if ((round(contracts[ii][m],2) < round(lower,2)) or (round(contracts[ii][m],2) > round(upper, 2))):
                        #preapre for entering in spreadsheet
                        temp=[]
                        temp.append(garage_dict.keys()[ii])
                        temp.append(contracts_time[ii][m])
                        temp.append("Contract")
                        anomalies.append(temp)
                        
                        
                    #check for difference with predictions
                    #we have found a mismatch, let's see if still we are 
                    #close to prediction
                        
                    #getting the closest rounded off hour
                    current_t= datetime.now()
                    
                    temp_next_t = current_t+timedelta(hours=1)
                    temp_prev_t = current_t-timedelta(hours=1)
                    
                    
                    next_t=datetime(temp_next_t.date().year,temp_next_t.date().month,
                                    temp_next_t.date().day,temp_next_t.time().hour)
                    prev_t=datetime(temp_prev_t.date().year,temp_prev_t.date().month,
                                    temp_prev_t.date().day,temp_prev_t.time().hour)
                    delta_prev = current_t - prev_t
                    delta_next = next_t - current_t
                    if(delta_prev.seconds > delta_next.seconds):
                        pred_t = next_t.hour
                    else:
                        pred_t = prev_t.hour
                        
                    #construct the url
                    pred_url = "https://my.smarking.net/api/ds/v3/garages/"+str(garage_dict.keys()[ii])+"/future/occupancy/from/"+str(current_t.year)+"-"+str(current_t.month)+"-"+str(current_t.day)+"T"+str(pred_t)+":00:00/1/1h?gb=User+Type"
                    
                    print pred_url
                    #get the response using the url
                    pred_response = requests.get(pred_url,headers=headers)
                    pred_content = pred_response.content
            
                    #see if content was received.  If nothing  received, exit
                    if (pred_content == ""):
                        print "<p>No content received</p>"
                        continue
                    #we have collected the data
                    try:
                        pred_garage_info = json.loads(pred_content)
                    except ValueError:
                        raise ValueError("No JSON Object received, please try again.")
                    #print pred_garage_info
                    #TODO check if value is there in the dict    
                    for item in pred_garage_info["value"]:
                        group = str(item.get("group"))
                        if('Contract' in group):  
                            #print garage_dict.keys()[ii], " val", item.get("value")
                            #check if we received a value
                            if(item.get("value")[0] is not None):
                                pred_val =  float(item.get("value")[0])
                    #print 'Con ', garage_dict.keys()[ii], pred_val, round(contracts[ii][m],2)
                    if(item.get("value")[0] is not None):
                        if (round(contracts[ii][m],2) == 0):
                            if (pred_val >=20):
                                temp=[]
                                temp.append(garage_dict.keys()[ii])
                                temp.append(contracts_time[ii][m])
                                temp.append("Contract predicted "+str(pred_val)+" got 0")
                                anomalies.append(temp)
                        elif (pred_val == 0):
                            if (round(contracts[ii][m],2) >=20):
                                temp=[]
                                temp.append(garage_dict.keys()[ii])
                                temp.append(contracts_time[ii][m])
                                temp.append("Contract predicted 0 got "+str(round(contracts[ii][m],2)))
                                anomalies.append(temp)
                            
                                
                        #normalizing by the min of the two                            
                        if(pred_val >20 and round(contracts[ii][m],2) >20):
                                pred_norm = pred_val/min(round(contracts[ii][m],2),pred_val)
                                con_norm = round(contracts[ii][m],2)/min(round(contracts[ii][m],2),pred_val)
                                if(abs(pred_norm-con_norm) > 0.5):
                                    temp=[]
                                    temp.append(garage_dict.keys()[ii])
                                    temp.append(contracts_time[ii][m])
                                    temp.append("Contract predicted "+str(pred_val)+" got "
                                                + str(round(contracts[ii][m],2)))
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
                    if ((round(transients[ii][m],2) < round(lower,2)) or (round(transients[ii][m],2) > round(upper, 2))):
                        temp=[]
                        temp.append(garage_dict.keys()[ii])
                        temp.append(transients_time[ii][m])
                        temp.append("Transient")
                        anomalies.append(temp)
                        
                    #check for difference with predictions
                    #we have found a mismatch, let's see if still we are 
                    #close to prediction
                        
                    #getting the closest rounded off hour
                    current_t= datetime.now()
                    temp_next_t = current_t+timedelta(hours=1)
                    temp_prev_t = current_t-timedelta(hours=1)
                    
                    
                    next_t=datetime(temp_next_t.date().year,temp_next_t.date().month,
                                    temp_next_t.date().day,temp_next_t.time().hour)
                    prev_t=datetime(temp_prev_t.date().year,temp_prev_t.date().month,
                                    temp_prev_t.date().day,temp_prev_t.time().hour)
                    delta_prev = current_t - prev_t
                    delta_next = next_t - current_t
                    if(delta_prev.seconds > delta_next.seconds):
                        pred_t = next_t.hour
                    else:
                        pred_t = prev_t.hour
                        
                    #construct the url
                    pred_url = "https://my.smarking.net/api/ds/v3/garages/"+str(garage_dict.keys()[ii])+"/future/occupancy/from/"+str(current_t.year)+"-"+str(current_t.month)+"-"+str(current_t.day)+"T"+str(pred_t)+":00:00/1/1h?gb=User+Type"
                    
                    print pred_url
                    
                    #get the response using the url
                    pred_response = requests.get(pred_url,headers=headers)
                    pred_content = pred_response.content
            
                    #see if content was received.  If nothing  received, exit
                    if (pred_content == ""):
                        print "<p>No content received</p>"
                        continue
                    #we have collected the data
                    try:
                        pred_garage_info = json.loads(pred_content)
                    except ValueError:
                        raise ValueError("No JSON Object received, please try again.")
                        
                    #print pred_garage_info   
                    #TODO check if value is there in the dict
                    for item in pred_garage_info["value"]:
                        group = str(item.get("group"))
                        if('Transient' in group):  
                            #print garage_dict.keys()[ii], " val", item.get("value")
                            #check if we received a value
                            if(item.get("value")[0] is not None):
                                pred_val =  float(item.get("value")[0])
                    #print 'Tran ', garage_dict.keys()[ii], pred_val, round(transients[ii][m],2)
                    if(item.get("value")[0] is not None):
                        #if we get 0 transient, see how the prediction is
                        if (round(transients[ii][m],2) == 0):
                            if (pred_val >=20):
                                temp=[]
                                temp.append(garage_dict.keys()[ii])
                                temp.append(transients_time[ii][m])
                                temp.append("Transient predicted "+str(pred_val)+" got 0")
                                anomalies.append(temp)
                        elif (pred_val == 0):
                            if (round(transients[ii][m],2) >=20):
                                temp=[]
                                temp.append(garage_dict.keys()[ii])
                                temp.append(transients_time[ii][m])
                                temp.append("Transient predicted 0 got "
                                                +str(round(transients[ii][m],2)))
                                anomalies.append(temp)
                            
                        #normalizing by the min of the two 
                        if(pred_val > 20 and round(transients[ii][m],2) > 20):
                                pred_norm = pred_val/min(round(transients[ii][m],2),pred_val)
                                tran_norm = round(transients[ii][m],2)/min(round(transients[ii][m],2),pred_val)
                                #print garage_dict.keys()[ii], pred_norm, tran_norm, pred_val, round(transients[ii][m],2)
                                if(abs(pred_norm-tran_norm) > 0.5):
                                    temp=[]
                                    temp.append(garage_dict.keys()[ii])
                                    temp.append(transients_time[ii][m])
                                    temp.append("Transient predicted "+str(pred_val)+" got "
                                                + str(round(transients[ii][m],2)))
                                    anomalies.append(temp)
                        
        
        #Done analyzing anomalies, all the data is in the anomalies structure
        #print "Anomalies"
        #f.write(anomalies)
        #f = open('real_time_results', 'a+')
        
        for item in anomalies:
            print item
        #f.close()
        
        #save it to google drive
        #for ii in anomalies:
            
        #Reset anomalies
        anomalies = []
        #also reset contracts and transients
        contracts.fill(0)
        transients.fill(0)
        contracts_time.fill("")
        transients_time.fill("")
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
    
    
            #print garage_info
    
            #parse the JSON-formatted line
        
            #if value not received for some reason, add 0 to value
            if "value" not in garage_info:
                contracts.itemset((line_index, time), 0.0)
                transients.itemset((line_index, time), 0.0)
                
                #also record the times
                contracts_time.itemset((line_index, time), str(datetime.now.date())+" "+str(datetime.now.time()))
                transients_time.itemset((line_index, time), str(datetime.now.date())+" "+str(datetime.now.time()))
                
                line_index = line_index + 1
                continue
            for item in garage_info["value"]:
                group = str(item.get("group"))
                if('Contract' in group):  
                    contracts.itemset((line_index, time), float(item.get("value")))
                    
                    #also record the times
                    contracts_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))
                    
                    #print 'setting con value ', float(item.get("value")), "at ",line_index, time
                    con = 1
                if('Transient' in group):
                    transients.itemset((line_index, time), float(item.get("value")))
                    #print 'setting tran value ', float(item.get("value")), "at ",line_index, time
                    #also record the times
                    transients_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))
                    
                    tran = 1
    

            if ((con == 0) and (tran == 0)):
                garage_info_occupancy[line_index] = 3
                #print "no data for ", line_index
                contracts.itemset((line_index, time), 0.0)
                transients.itemset((line_index, time), 0.0)
                
                contracts_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))
                transients_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))
                
                line_index = line_index + 1
                continue
            if (con == 0):
                contracts.itemset((line_index, time), 0.0)
                
                #also record the times
                contracts_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))

                #print 'setting con value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 2
            if (tran == 0):
                transients.itemset((line_index, time), 0.0)
                
                #also record the times
                transients_time.itemset((line_index, time), str(datetime.now().date())+" "+str(datetime.now().time()))
              
                #print 'setting tran value 0 at ',line_index, time
                garage_info_occupancy[line_index] = 1
                
                
            line_index = line_index + 1
            
        #temp_values.append(val)
    time = time + 1
    threading.Timer(2, check_error_real_time).start()
    
check_error_real_time()