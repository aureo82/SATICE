#!/usr/bin/python
"""
Licensed under MIT (../LICENSE)

latlong.py

Extract position from the log XYZ, convert to Lat Long.
Calculates daily dawn and dusk time.

V0. Oriol Sanchez,ICM-CSIC

TBD: Extract from HOURLY RINEX FILE...
"""

# LatLong extraction from the log

#DEPENDENCES
import time
import datetime
from math import atan2, cos, pi, sin, sqrt, tan, radians, degrees, acos
      

#LOAD THE DATA FROM POSITION LOGFILE
cfile = open("/home/satice/log/position.log",'r')
line=cfile.readline()
XYZ =line.split(',')
X=float(XYZ[0])
Y=float(XYZ[1])
Z=float(XYZ[2])
#X= -1372621.7569
#Y= -965290.0859
#Z= 6132800.4643

#CURRENT DOY
now=datetime.datetime.now()
today=now.strftime("%j")
print "TODAY DOY"
print today
#today=60

#CONVERTING XYZ TO LAT LONG
if float(X) != 0:
     # Constants (WGS ellipsoid)
     a = 6378137
     e = 8.1819190842622e-2
     # Calculation
     b = sqrt(pow(a,2) * (1-pow(e,2)))
     ep = sqrt((pow(a,2)-pow(b,2))/pow(b,2))
     p = sqrt(pow(X,2)+pow(Y,2))
     th = atan2(a*Z, b*p)
     lon = atan2(Y, X)
     lat = atan2((Z+ep*ep*b*pow(sin(th),3)), (p-e*e*a*pow(cos(th),3)))
     n = a/sqrt(1-e*e*pow(sin(lat),2))
     alt = p/cos(lat)-n
     lat = (lat*180)/pi
     lon = (lon*180)/pi
     #lat=41.385
     #lon=2.195
     #alt=67.4689
     #print "LATITUDE %s | LONGITUDE %s | ALTITUDE %s" % (lat, lon, alt)
     print "COORDINATES: LATITUDE | LONGITUDE | ALTITUDE " 
     print "%s %s %s" % (lat, lon, alt)
     j=-tan(radians(lat))*tan(radians(23.44*sin(radians((360*(int(today)+284))/365))))
     #print j
     if j>=1:
       light=0
     elif j<=-1:
       light=12
     else :    
       light=(degrees(acos(j)))/15
     timez=(lon/15) #timezone correction
     rise=(12-light+timez)*3600
     dusk=(12+light+timez)*3600
     rise=(datetime.timedelta(seconds=rise))
     dusk=(datetime.timedelta(seconds=dusk))
     print "UTC TIME SUNRISE (0.HHmm)"
     #print rise
     #Hours
     Hrise=(rise.seconds)/3600
     #Minutes
     Mrise=int((((float(rise.seconds))/3600)-float((rise.seconds)/3600))*60)
     print float(Hrise*100+Mrise)/10000
     print "UTC TIME SUNSET (0.HHmm)"
     #print dusk
     Hdusk=(dusk.seconds)/3600
     #Minutes
     Mdusk= int((((float(dusk.seconds))/3600)-float((dusk.seconds)/3600))*60)
     print float(Hdusk*100+Mdusk)/10000
     #print "UTC TIME NOW"
     #unow=datetime.datetime.utcnow()
     #unow=unow.strftime("%H:%M:%S")
     #print unow
