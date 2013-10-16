#!/usr/bin/python
#By Rhys McCaig @mccaig / mccaig@gmail.com

import sys
import json
import logging
import re
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

import numpy
import requests

class NikePlus:
	"""Class for working with the Nike+ API"""
	#Nike+ Settings

	#You might need to adjust these three below in the future to match your developer credentials. These work fine as of August 2013.
	nikeplus_app_id = 'ONEPLUSSDKSAMPLE'
	nikeplus_client_id = 'c002b5e3fd045be3bf357c8534edb38b'
	nikeplus_client_secret =  'd7c94a86a6a389c4'
	
	#Probably shouldnt touch anything below here, unless something drastically changes
	nikeplus_base_url = 'https://api.nike.com'
	
	nikeplus_headers = {	'Appid' : nikeplus_app_id,
				'Accept' : 'application/json'}
	
	nikeplus_authentication_parameters = {'app' : nikeplus_app_id,
				'client_id' : nikeplus_client_id,
				'client_secret' : nikeplus_client_secret}
	
	nikeplus_endpoints = {	'aggregate_sports_data' : 	nikeplus_base_url+'/me/sport',
				'list_activities' : 	  	nikeplus_base_url+'/me/sport/activities',
				'activity_detail' :		nikeplus_base_url+'/me/sport/activities/%(activity_id)s',
				'gps_data' : 			nikeplus_base_url+'/me/sport/activities/%(activity_id)s/gps',
				'login' :			nikeplus_base_url+'/nsl/v2.0/user/login'}
	
	nikeplus_activity_list_limit = 250 #API shits itself if we set this too high
	nikeplus_timeout_seconds = 30

	def __init__(self):
		self.logger = logging.getLogger('nikeplus.NikePlus')
		self.id = id(self)
		self.logger.info('[{i}] {f}({m})'.format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Creating Instance"))
		self.cookie = None
		self.authentication_data = {}
		self.token = None
		self.session = requests.Session()
		self.session.headers.update(self.nikeplus_headers)
		self.aggregate_data = None
		self.activities = {}
		return

	#Authentication - Only implement Nike+ Login at this stage (email+password)
	def Authenticate(self,username=None,password=None):
		if username == None:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No Username"))
			raise NikePlusError("Cant Authenticate() without a Username")
		if password == None:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No Password"))
			raise NikePlusError("Cant Authenticate() without a Password")
		authentication_payload = {'email':username,'password':password}
		r = self.session.post(self.nikeplus_endpoints['login'], data=authentication_payload, params=self.nikeplus_authentication_parameters, headers=self.nikeplus_headers,timeout=self.nikeplus_timeout_seconds)
		self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Request: "+str([r.url,r.request.headers])))
		self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Response: "+str([r.headers,r.text])))
		try:	
			self.authentication_data = r.json()
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Setting Token: "+str(self.authentication_data['access_token'])))
			self.token = self.authentication_data['access_token']
		except:
			#If json parsing fails then it was probably a bad username/password combo
			self.logger.warn("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m=r.url+" "+str(sys.exc_info()[0])))
			self.Token = None
		return self

	#You can manually set an oAuth token here if you have one from a previous session

	#Get aggregate workout data
	def RetrieveAggregateData(self):
		if self.token is None:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No Auth Token set"))
			raise NikePlusError("No Auth Token - Try to Authenticate() or manually set a NikePlus.token first")
		else:
			parameters = {'access_token':self.token}
			r = self.session.get(self.nikeplus_endpoints['aggregate_sports_data'], params=parameters, headers=self.nikeplus_headers,timeout=self.nikeplus_timeout_seconds)
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Request: "+str([r.url,r.request.headers])))
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Response: "+str([r.headers,r.text])))
			try:
				self.aggregate_data = r.json()
				self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retrieved Data"))
			except:
				self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m=r.url+" "+str(sys.exc_info()[0])))
				raise
		return self

	#Retrieve activity list/summaries
	def RetrieveActivities(self,limit=100000,offset=1):
		count = self.nikeplus_activity_list_limit #Nike+ API shits itself if you try to request more than 500 or so, keeping this relatively low to be safe. We have to page through results.
		self.logger.info("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retrieving activities in batches of {c}".format(c=count)))
		activities = {}
		eof = False
		if self.token is None:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No Auth Token set"))
			raise NikePlusError("No Auth Token - Try to Authenticate() or manually set a NikePlus.token first")
		else:	
			while (len(activities)<limit and not eof):
				parameters = {'access_token':self.token,'count':count,'offset':offset}
				r = self.session.get(self.nikeplus_endpoints['list_activities'], params=parameters, headers=self.nikeplus_headers,timeout=self.nikeplus_timeout_seconds)
				self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Request: "+str([r.url,r.request.headers])))
				self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Response: "+str([r.headers,r.text])))
				try:
					data = r.json()
					if "data" in data:
						self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retreived {c} activities".format(c=len(data['data']))))
						for a in data['data']:
							if len(activities)<limit:
								activities[str(a['activityId'])] = a #so we can search by activityId
								activities[str(a['activityId'])]['gps'] = None
						if len(data['data']) == 0 or len(activities) % count != 0: 
							eof = True
					else:
						eof = True
					offset += count
				except:
					self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m=r.url+" "+str(sys.exc_info()[0])))
					raise
		self.activities = activities
		self.logger.info("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retreived a total of {c} activities".format(c=len(self.activities))))
		return self
	
	#Downloads details for an individual Activity
	def GetActivityDetails(self,activity_id):
		if self.token is None:
			self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No Auth Token set"))
			raise NikePlusError("No Auth Token - Try to Authenticate() or manually set a NikePlus.token first")
		else:
			self.activities.setdefault(str(activity_id),{})	#If not being invoked after a RetrieveActivities, (if manually setting the activity_id) activity_id wont yet be set
			parameters = {'access_token':self.token,'activityId':activity_id}
			#Note we have to replace activityID into the endpoint in the below code
			r = self.session.get(self.nikeplus_endpoints['activity_detail'] % {'activity_id' : activity_id}, params=parameters, headers=self.nikeplus_headers,timeout=self.nikeplus_timeout_seconds)
			self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Request: "+str([r.url,r.request.headers])))
			self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Response: "+str([r.headers,r.text])))
			npa = NikePlusActivity(activity_id)
			try:
				#Attach the detail to the existing activity
				if "errorCode" in r.json().keys():
					self.logger.warn("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error getting detail for activity id {a}".format(a=activity_id)))
				else:
					npa.AddDetail(r.json())
					self.activities[str(activity_id)]['detail'] = True	
					self.logger.info("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retrieved detail for activity id {a}".format(a=activity_id)))
			except:
				self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Failure to attach detail to activity id {a}. Error {e}".format(a=activity_id, e=str(sys.exc_info()[0]))))
				raise
			#Now to retrieve GPS (if there is any)
			parameters = {'access_token':self.token,'activityId':activity_id}
			#Note we have to replace activityID into the endpoint in the below code
			r = self.session.get(self.nikeplus_endpoints['gps_data'] % {'activity_id' : activity_id}, params=parameters, headers=self.nikeplus_headers,timeout=self.nikeplus_timeout_seconds)
			self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Request: "+str([r.url,r.request.headers])))
			self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Response: "+str([r.headers,r.text])))
			try:
				#Attach the detail to the existing activity
				if "errorCode" in r.json().keys():
					self.activities[str(activity_id)]['gps'] = False
					self.logger.info("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No GPS data available for activity id {a}".format(a=activity_id)))	
				else:
					self.activities[str(activity_id)]['gps'] = True
					self.logger.info("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retrieved GPS data for activity id {a}".format(a=activity_id)))
					npa.AddGPS(r.json())
				npa.gps = self.activities[str(activity_id)]['gps']
			except:
				self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Failure to attach detail to activity " + r.url+" "+str(sys.exc_info()[0])))
				raise
		return npa

	#Download the details for all activities 
	def GetBulkActivityDetails(self):
		self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Retrieving list of activities"))
		npaList = []
		for a in self.GetActivityIds():
			npalist.append(self.RetrieveActivityDetails(a))
		return npaList

	#Get a list of available Activity ID's
	def GetActivityIds(self):
		if len(self.activities) == 0:
			self.RetrieveActivities()
			if len(self.activities) == 0:
				self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No activities for this account"))
				raise NikePlusError("There are no activities for this account")
		self.logger.debug("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m=str(self.activities.keys())))
		return self.activities.keys()

	#Return the sumary data for an individual activity
	def GetActivitySummary(self,activity_id):
		if len(self.activities) == 0:
			self.RetrieveActivities()
			if len(self.activities) == 0:
				self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="No activities for this account"))
				raise NikePlusError("There are no activities for this account")
		if activity_id not in self.activities.keys():	
			self.logger.error("[{i}] {f} ({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Activity ID {a} not found on this account".format(a=activity_id)))
			raise NikePlusError("Activity ID {a} not found!".format(a=activity_id))
		return self.activities[activity_id]



class NikePlusActivity:
	"""Class for working with a single nikeplus activity data set"""

	nikeplus_interpolatable_metrics = ['DISTANCE','SMOOTHED_DISTANCE']
	
	def __init__(self, a_id=None):
		self.logger = logging.getLogger('nikeplus.NikePlusActivity')
		self.id = id(self)
		self.logger.info('[{i}] {f}({m})'.format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Creating Instance for activity id {a}".format(a=a_id)))
		self.activity_id = a_id
		self.data = {}
		self.data['timeSeries'] = {}
		self.detail = False
		self.gps = None
		self.duration = 0
		self.distance = 0
		self.calories = 0
		self.distance_smoothing_window = 1
		self.start_datetime = None
		return
	
	#No Validation for now - we just blindly add whatever data elements that are passed
	def AddDetail(self,d={}):
		try:
			for (k,v) in d.iteritems():
				self.data[k] = v
			self.activity_type = self.data['activityType']
			self.start_time = self.data['startTime']
			self.start_datetime = datetime.strptime(self.start_time, '%Y-%m-%dT%H:%M:%SZ')
			self.duration = timestring_to_milliseconds(self.data['metricSummary']['duration'])
			self.distance = self.data['metricSummary']['distance']
			self.calories = self.data['metricSummary']['calories']
			self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Activity ID {a} has deviceType {d}".format(a=self.activity_id,d=self.data['deviceType'])))
			self._SetSmoothingWindow()._AddSmoothedDistance()._AddDataToTimeSeries()._Interpolate()
		except:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error adding detail to Activity ID {a}".format(a=self.activity_id)))
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error {e}, Detail Data: {data}".format(e=sys.exc_info()[0],data=d)))
			raise
		self.detail = True
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Added detail for activity id {a}".format(a=self.activity_id)))
		return self

	#No Validation for now - we just blindly add whatever data elements that are passed
	def AddGPS(self,g={}):
		try:
			self.data['gpsmetrics'] = [g] #Keeping it in the same format as metrics
			self._AddGPSDataToTimeSeries()._Interpolate()
		except:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error adding gps to Activity ID {a}".format(a=self.activity_id)))
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error {e}, GPS Data: {data}".format(e=sys.exc_info()[0],data=g)))
			raise	
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Added gps for activity id {a}".format(a=self.activity_id)))
		self.gps = True
		return self

	#Add timeseries data in MILLISECONDS
	def _AddDataToTimeSeries(self):
		try:
			for m in self.data['metrics']:
				if m['intervalUnit'] in ['SEC','MIN']: #Dont currently know how to handle it if we arent dealing in seconds
					multiplier = 1000 #convert seconds to milliseconds
					if m['intervalUnit'] == "MIN":
						multiplier = 60000 #convert minutes to milliseconds
					time = 0
					for d in m['values']:
						self.data['timeSeries'].setdefault(int(time), {})[m['metricType']] = d #really just self.data['timeSeries']['metric'] = d with setdefault
						time += m['intervalMetric'] * 1000	
				else:
					self.logger.warn("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Dont know how to handle metric ({metric}) with intervalUnit: ({i}) for activity id {a}".format(a=activity_id,i=m['intervalUnit'],metric=m['metricType'])))
			#Add final time and distance
			self.data['timeSeries'].setdefault(int(self.duration), {})['DISTANCE'] = str(self.distance)
			self.data['timeSeries'].setdefault(int(self.duration), {})['SMOOTHED_DISTANCE'] = str(self.distance)
		except:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error adding data to time series for activity id {a}".format(a=self.activity_id)))
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error: {e}, self.data: {data}".format(e=sys.exc_info()[0],data=self.data)))
			raise
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Added detail data to time series for activity id {a}".format(a=self.activity_id)))
		return self

	#Add timeseries data in MILLISECONDS
	#Nike+ doesnt seem to return the real interval value for waypoints, so we'll assume they are uniform and calculate the intervals ourselves
	def _AddGPSDataToTimeSeries(self):
		try:
			for m in self.data['gpsmetrics']:
				for i in range(len(m['waypoints'])):
					#add the waypoints to the time series (using setdefault to create the time entry)
					self.data['timeSeries'].setdefault(int(self.duration * (float(i) / (len(m['waypoints']) - 1))), {})['WAYPOINT'] = m['waypoints'][i]
		except:
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error gps to time series for activity id {a}".format(a=self.activity_id)))
			raise
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Added gps to time series for activity id {a}".format(a=self.activity_id)))
		return self

	#Dont know why i bothered with this. But sure, it returns a list of workout data time series keys
	def GetTimeSeries(self):
		return sorted(self.data['timeSeries'].keys())


	#Return a the specific metric in [time,metric] format
	def GetTimeSeriesDataByMetric(self,metric):
		d = {}
		for k in self.GetTimeSeries():
			if metric in self.data['timeSeries'][k]:
				d[k] = self.data['timeSeries'][k][metric]
		return d
	
	#Return a copy of the summary data	
	def GetMetricSummary(self):
		return self.data['metricSummary'].copy()
		
	#Returns true if the specified metric is available
	def HasMetric(self,metric):
		for m in self.data['metrics']:
			if metric == m['metricType']:
				return True
		return False

	#Kinda private, as we always want to add this after adding detail, but thats about it.
	def _AddSmoothedDistance(self):
		try:
			smoothed = []
			if self.HasMetric("DISTANCE"):
				for m in self.data['metrics']:
					if m['metricType'] == "DISTANCE":
						#Distance array is unicode, cast it to float before smoothing, cast result back to unicode
						smoothed = [unicode(f) for f in smooth_array([float(u) for u in m['values']],self.distance_smoothing_window)]
						self.data['metrics'].append({	'metricType': 'SMOOTHED_DISTANCE',
										'intervalMetric': m['intervalMetric'],
										'intervalUnit': m['intervalUnit'],
										'values': smoothed
										})
				self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Added SMOOTHED_DISTANCE metric for activity id {a}".format(a=self.activity_id)))		
			else:
				self.logger.warn("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Activity {a} has no distance metric!".format(a=self.activity_id)))
		except: #What could possibly go wrong?
			self.logger.error("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Error adding smoothed distance for activity id {a}".format(a=self.activity_id)))
			raise
		return self

	#Figure out what sliding window size we want to use for smoothing distance metrics (for low res treadmills)
	def _SetSmoothingWindow(self):
		s = 0
		decimals = 0
		try:
			for m in self.data['metrics']:
				if m['metricType'] == "DISTANCE":
					for d in m['values']:
						if len(d.split('.')[1]) > decimals:
							decimals = len(d.split('.')[1])
		except:
			self.logger.warn("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Exception in _SetSmoothingWindow for activity id {a}".format(a=self.activity_id)))
			pass
		if decimals == 0:
			self.distance_smoothing_window = 19
		elif decimals == 1:
			self.distance_smoothing_window = 13
		elif decimals == 2:
			self.distance_smoothing_window = 7
		elif decimals == 3:
			self.distance_smoothing_window = 3
		else:
			self.distance_smoothing_window = 1
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Set a smoothing window of {w} for activity id {a}".format(w=self.distance_smoothing_window,a=self.activity_id)))
		return self
	
	#Some tools fall over if there isnt a distance supplied in every TCX entry. So we need to interpolate the distance if our other metrics have a different interval to Distance	
	#Note we use floats here as required by numpy
	def _Interpolate(self):
		try:
			for metric in self.nikeplus_interpolatable_metrics:
				dataset = self.GetTimeSeriesDataByMetric(metric)
				#Get an array of the x values (time) of our data points for interpolation
				x_points = [float(u) for u in sorted(dataset.keys())]
				#Get an array of the y values (distance) of our data points for interpolation
				y_points = [dataset[u] for u in sorted(dataset.keys())]
				#Get an array of the x coordinates we want to interpolate onto (all of the time series)
				x_coords = [float(u) for u in self.GetTimeSeries()]
				#interpolate onto y values
				y_coords = numpy.interp(x_coords,x_points,y_points)
				#Update our interpolated values into our time series array
				for i in range(len(x_coords)):
					self.data['timeSeries'][int(x_coords[i])][metric] = unicode(y_coords[i])
		except:
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Something went horribly wrong during interpolation for activity id {a}".format(a=self.activity_id)))
			raise
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Interpolation Success for activity id {a}".format(a=self.activity_id)))
		return self		
	
	#Spitting out our data as JSON is pretty easy, especially if we dont want to do any special formatting.
	def AsJSON(self):
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="JSON export for activity id {a}".format(a=self.activity_id)))
		json_out = json.dumps(self.data,sort_keys=True,indent=2,separators=(',', ': '))
		return json_out
	
	#Generate GPX file
	def AsGPX(self):
		try:
			GPX = ET.Element('gpx')
			GPX.set('xmlns','http://www.topografix.com/GPX/1/1')
			GPX.set('xmlns:tc2','http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
			GPX.set('xmlns:xsi','http://www.w3.org/2001/XMLSchema-instance')
			GPX.set('xmlns:tp1','http://www.garmin.com/xmlschemas/TrackPointExtension/v1')
			GPX.set('version','1.1')
			GPX.set('creator','Nike+ to GPX exporter (@mccaig)')
			GPX.set('xsi:schemaLocation','http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd')
			GPXtrk = ET.SubElement(GPX,'trk')
			ET.SubElement(GPXtrk,'name').text = str(self.start_time)
			GPXtrkseg = ET.SubElement(GPXtrk,'trkseg')
			for i in self.GetTimeSeries():	
				time_slice = self.data['timeSeries'][i]
				if "WAYPOINT" in time_slice: #We need a waypoint for a record
					GPXtrkpt = ET.SubElement(GPXtrkseg,'trkpt')
					GPXtrkpt.set('lat',str(time_slice["WAYPOINT"]["latitude"]))
					GPXtrkpt.set('lon',str(time_slice["WAYPOINT"]["longitude"]))
					ET.SubElement(GPXtrkpt,'ele').text = str(time_slice["WAYPOINT"]['elevation'])
					ET.SubElement(GPXtrkpt,'time').text = (self.start_datetime + timedelta(milliseconds=int(i))).isoformat() + "Z"
					GPXextensions = ET.SubElement(GPXtrkpt,'extensions')
					if "HEARTRATE" in time_slice:
							GPXHR = ET.SubElement(GPXextensions,'tp1:TrackPointExtension')
							ET.SubElement(GPXHR,'tp1:hr').text = time_slice["HEARTRATE"]
			gpx_out = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' + ET.tostring(GPX)
		except:
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="GPX generation failed for activity id {a}".format(a=self.activity_id)))
			raise
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Exported GPX for activity id {a} [{c} characters]".format(a=self.activity_id,c=len(gpx_out))))
		return gpx_out

	#Generate TCX File
	def AsTCX(self):
		try:
			TCX = ET.Element('TrainingCenterDatabase')
			TCX.set('xmlns','http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
			TCX.set('xmlns:xsi','http://www.w3.org/2001/XMLSchema-instance')
			TCX.set('xsi:schemaLocation','http://www.garmin.com/xmlschemas/ActivityExtension/v2 http://www.garmin.com/xmlschemas/ActivityExtensionv2.xsd http://www.garmin.com/xmlschemas/FatCalories/v1 http://www.garmin.com/xmlschemas/fatcalorieextensionv1.xsd http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd')
			ET.SubElement(TCX,'Folders')
			TCXActivities = ET.SubElement(TCX,'Activities')
			TCXActivity = ET.SubElement(TCXActivities,'Activity')
			TCXActivity.set('Sport',self._GetGarminSport())
			ET.SubElement(TCXActivity,'Id').text = str(self.start_time)
			TCXLap = ET.SubElement(TCXActivity,'Lap')
			TCXLap.set('StartTime',self.start_time)
			ET.SubElement(TCXLap,'TotalTimeSeconds').text = str(self.duration / 1000)
			ET.SubElement(TCXLap,'DistanceMeters').text = str(self.distance * 1000)
			ET.SubElement(TCXLap,'Calories').text = str(self.calories)
			ET.SubElement(TCXLap,'Intensity').text = "Resting"
			ET.SubElement(TCXLap,'TriggerMethod').text = "Manual"
			TCXTrack = ET.SubElement(TCXLap,'Track')
			for i in self.GetTimeSeries():
				TCXTrackpoint = ET.SubElement(TCXTrack,'Trackpoint')
				ET.SubElement(TCXTrackpoint,'Time').text = (self.start_datetime + timedelta(milliseconds=int(i))).isoformat() + "Z"
				time_slice = self.data['timeSeries'][i]
				if "WAYPOINT" in time_slice:
					TCXPosition = ET.SubElement(TCXTrackpoint,'Position')
					ET.SubElement(TCXPosition,'LatitudeDegrees').text = str(time_slice["WAYPOINT"]['latitude'])
					ET.SubElement(TCXPosition,'LongitudeDegrees').text = str(time_slice["WAYPOINT"]['longitude'])
					ET.SubElement(TCXTrackpoint,'AltitudeMeters').text = str(time_slice["WAYPOINT"]['elevation'])
				if "SMOOTHED_DISTANCE" in time_slice:
					ET.SubElement(TCXTrackpoint,'DistanceMeters').text = str(float(time_slice["SMOOTHED_DISTANCE"]) * 1000) #Kilometres to Metres	
				if "HEARTRATE" in time_slice:
					TCXHeartRate = ET.SubElement(TCXTrackpoint,'HeartRateBpm') 
					TCXHeartRate.set("xsi:type","HeartRateInBeatsPerMinute_t")
					ET.SubElement(TCXHeartRate,'Value').text = str(time_slice["HEARTRATE"])
				TCXExtensions = ET.SubElement(TCXTrackpoint,'Extensions')
				if "SPEED" in time_slice or "CADENCE" in time_slice:
					TCXTPX = ET.SubElement(TCXExtensions,'TPX')
					TCXTPX.set('xmlns','http://www.garmin.com/xmlschemas/ActivityExtension/v2')
					TCXTPX.set('CadenceSensor','Footpod')
					if "SPEED" in time_slice:
						ET.SubElement(TCXTPX,'Speed').text = str(float(time_slice["SPEED"])/3.6) #Convert from Nike+ KPH to M/S
					if "CADENCE" in time_slice:
						#Garmin Cadence is times one foot hits the ground, nike+ cadence is in steps, so we need to divide by 2.
						ET.SubElement(TCXTPX,'RunCadence').text = str(int(float(time_slice["CADENCE"])/2)) 
				else:
					TCXExtensions.text = "\n"
			tcx_out = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' + ET.tostring(TCX)
		except:
			self.logger.debug("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="TCX generation for activity id {a} failed".format(a=self.activity_id)))
			raise
		self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Exported TCX for activity id {a} [{c} characters]".format(a=self.activity_id,c=len(tcx_out))))
		return tcx_out

	#TODO: Generate Mock GPS data for runs without any location info.
	def AddMockGPSData(self):
		pass
	
	#Map to the garmin defined sports in GPX/TCX files. If this is enhanced in the future should make it a lookup rather than hardcoding
	def _GetGarminSport(self):
		if self.activity_type == "RUN":
			self.logger.info("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Detected 'garmin' sport for activity id {a} [{t}=Running]".format(a=self.activity_id,t=self.activity_type)))
			return "Running"
		
		#elif False: #May run other mappings later (Cycling?)
			#return self.activity_type
		else:
			self.logger.info ("[{i}] {f}({m})".format(i=self.id, f=str(sys._getframe().f_code.co_name), m="Failed to detect 'garmin' sport for activity id {a} ({t})".format(a=self.activity_id,t=self.activity_type)))
			return self.activity_type

	


class NikePlusError(Exception):
	pass
		


def timestring_to_milliseconds(s):
	hours, minutes, seconds, milliseconds = re.split(':|\.',s)
	return int(milliseconds) + (int(seconds) * 1000) + (int(minutes) * 60000) + (int(hours) * 3600000)

#From http://wiki.scipy.org/Cookbook/SignalSmooth
#Could probably do a bit better here. But for now im kinda lazy, so here it is in a lone function for now.
def smooth_array(a,window_len=11,window='flat'):
	x = numpy.array(a)
        if x.ndim != 1:
                raise ValueError, "smooth only accepts 1 dimension arrays."
        if x.size < window_len:
		window_len = x.size-1
                #raise ValueError, "Input vector needs to be bigger than window size."
        if window_len<3:
                return x
        if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
                raise ValueError, "Window is one of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
        s=numpy.r_[2*x[0]-x[window_len-1::-1],x,2*x[-1]-x[-1:-window_len:-1]]
        if window == 'flat': #moving average
                w=numpy.ones(window_len,'d')
        else:  
                w=eval('numpy.'+window+'(window_len)')
        y=numpy.convolve(w/w.sum(),s,mode='same')
        return y[window_len:-window_len+1].tolist()




