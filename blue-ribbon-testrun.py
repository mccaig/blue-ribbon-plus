#!/usr/bin/python
#By Rhys McCaig @mccaig / mccaig@gmail.com

import nikeplus
import logging
import sys

#Add in your nike+ login details here
USER='your.name@your.email.com'
PASS='YourPassword'

ROW = "{aid}\t{dt}\t{di}\t{du}\t{ca}\t{g}"

#Logging
logger = logging.getLogger('nikeplus')
logger.setLevel(logging.DEBUG)
# create file handler which logs messages
fh = logging.FileHandler('./data/nikeplus-testrun.log')
fh.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)


#Lets Roll
logger.info('Starting App')

#Initialize a NikePlus Object
np = nikeplus.NikePlus()

#Authenticate using credentials
np.Authenticate(USER,PASS)
logger.info("[{i}] {f}({m})".format(i="test.py", f=str(sys._getframe().f_code.co_name), m="Retrieved token [{t}] for {u}".format(t=np.token,u=USER)))

#If you already had a nike+ auth token, you could manually set it instead of authenticating with user/pass above.
#np.token = 'f058e7f928e35dc3eeeb8c83c3c7a44a'

#Suck in Aggregate data and a list of activities
np.RetrieveAggregateData().RetrieveActivities()

print ROW.format(aid="Activity ID",dt="Date Y-m-d HH:MM",di="Distance (kms)",du="Duration (sec)",ca="Calories",g="GPS?")

#Get the details for each activity, throw them in a folder called data (which we assume already exists.....) in TCX/GPX and JSON formats
for a in np.GetActivityIds():
	npa = np.GetActivityDetails(a)
	print ROW.format(aid=npa.activity_id,dt=npa.start_datetime.strftime('%Y-%m-%d %H:%M'),di="{0:.2f}\t".format(npa.distance),du="{d}\t".format(d=(npa.duration/1000)),ca="{c}\t".format(c=npa.calories),g=npa.gps)
	#Export to JSON
	logger.info("[{i}] {f}({m})".format(i="test.py", f=str(sys._getframe().f_code.co_name), m="Writing to file ./data/{a}.json".format(a=a)))
	f = open("./data/{a}.json".format(a=a),'w')
	f.write(npa.AsJSON())
	f.close()
	#Export to TCX
	logger.info("[{i}] {f}({m})".format(i="test.py", f=str(sys._getframe().f_code.co_name), m="Writing to file ./data/{a}.tcx".format(a=a)))
	f = open("./data/{a}.tcx".format(a=a),'w')
	f.write(npa.AsTCX())
	f.close()
	#Export to GPX
	logger.info("[{i}] {f}({m})".format(i="test.py", f=str(sys._getframe().f_code.co_name), m="Writing to file ./data/{a}.gpx".format(a=a)))
	f = open("./data/{a}.gpx".format(a=a),'w')
	f.write(npa.AsGPX())
	f.close()


#And that is that
