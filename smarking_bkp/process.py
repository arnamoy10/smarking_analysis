import datetime
import time

#read the file line by line
with open("AM_request") as f:
    content = f.readlines()
    
for line in content:
    contents = line.split(",")
    #print contents[1]
    #print contents[2]
    from_time = time.strptime(contents[1],"%Y-%m-%d")
    to_time = time.strptime(contents[2],"%Y-%m-%d")
    
    from_t = datetime.datetime(*from_time[:3])
    to_t = datetime.datetime(*to_time[:3])
    
    d = to_t - from_t
    
    duration = 0
    if d.days == 0:
        duration = 24
    else:
        duration = d.days * 24
        
    #get the starting postion e.g how far is the from date
    #from the beginning of time (3rd Feb)
    
    start = datetime.datetime(2015, 2, 3)
    
    d = from_t - start
    
    starting_index = 0
    if d.days == 0:
        starting_index = 24
    else:
        starting_index = d.days * 24
    
    
    print "starting index ", starting_index, duration
    