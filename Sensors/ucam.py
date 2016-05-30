#!/usr/bin/env python
"""
Licensed under MIT (../LICENSE)

ucam.py

Take photos with vx0706, the program is sensible to latitude and longitude
to take photos only if there is light, two photos tops if day is long enough
at golden hours (within 10 minutes close to them). 


 Input files:
           * timelog.log : for the current coordinates, doy, golden hours
           * photoday.log : stores the last doy where a photo was taken, 
                            and an hourly id identifier per photo (max 2)

V0. Daniel Peyrolon & Oriol Sanchez, ICM-CSIC
"""
import fox #Specific library to access serial ports on fox board kernel 2.7
import os
import time
from sensors import vc0706 #Custom library for SATICE on board payload
import math

def newDay():
#    cfile = open("lastphoto.log",'w')
    cfile = open("/home/satice/log/lastphoto.log",'w')
    now = time.localtime()
    cfile.write(time.strftime("%j", now)+'\n')
    hnow=int(time.strftime("%H", now))
#    print "local time %s" %(tzone+hnow)
    if ((hnow+tzone)<12): #Dawn never happens after local noon
        cfile.write('10.0\n')
    else: #Consider dawn at 4 in case system is restarted after local noon
        cfile.write('.04\n')
    cfile.write('10.0')
    cfile.close()


def formatime(t):
    if t<10.0: 
        (tm,th)=math.modf(float(t)*100)
        tm=int(tm*100)
        th=int(th)
    else:
        tm='1000'
        th='1000'
#    print "T %s Hm %s:%s" %(t,th,tm)
    return (tm,th)

def lastPhoto():
    '''Checks if last photos log file exists, loads the information of the last photos taken by the system'''
#    logfile="lastphoto.log"
    logfile="/home/satice/log/lastphoto.log"
    if (os.path.isfile(logfile) == False): #If file doesn't exist
        newDay()
    cfile = open(logfile,'r')
    doy=cfile.readline().strip()
    p1=cfile.readline().strip()
    p2=cfile.readline().strip()
    cfile.close()
    print "last photo log loaded"
    return (int(doy),p1,p2)


def currentDay():
	'''Loads data from current position and current golden hour settings'''
#        cfile = open("timelog.log",'r')
        cfile = open("/home/satice/log/timelog.log",'r')
        cfile.readline()
        doy=cfile.readline().strip()
#        print "Srise %s" % doy
        cfile.readline()
        coord=cfile.readline().strip()
        cfile.readline()
        srise=cfile.readline().strip()
#        print "Srise %s" % srise
        cfile.readline()
        sdown=cfile.readline().strip()
#        print "Sdown %s" % sdown
        cfile.close()
        coord=coord.split()
#        print "--------> longtidue %s" %coord[1]
        timez=int((float(coord[1])/15))
#        print "Timezone correction %s" %timez
        return (int(doy),float(srise),float(sdown),timez)


def timepostfix():
    """Will create the postfix to be used when writing files."""
    # To represent the hour.
    hours_l = 'abcdefghijklmnopqrstuvwx'
    now = time.localtime()
    doy = time.strftime("%j", now)
    hour = time.strftime("%H", now)
    minute = time.strftime("%M", now)
    year = time.strftime("%Y", now)
    hour_rep = hours_l[int(hour)]
    return ((doy + hour_rep + '.' + year[2:] + 'i'),int(hour),int(minute))

def getbuoyname():
	"""Fetch the buoy name from the configuration (i.e. SI06)."""
	cfile = open("/home/satice/conf/tplogger.conf",'r')
	# The first line contains comments.
	cfile.readline()
	# Take out the last '\n'.
	return cfile.readline().strip()

def savetime(p1,tstamp,ldoy):
#    cfile = open("lastphoto.log",'w+')
    cfile = open("/home/satice/log/lastphoto.log",'w+')
    cfile.write(str(ldoy) +'\n')
    if (p1>1.0):
        #Save on P1
        print "Save dawn time"
        cfile.write(str(tstamp)+'\n')
        cfile.write('10.0')
    else:        
        #Save on P2
        print "Save dusk time"
        cfile.write(str(p1) +'\n')
        cfile.write(str(tstamp))
    cfile.close()

def takephoto(photoname):
    #Switch on the relay.
    relay = fox.Pin('J7.4', 'low')
    relay.on()
    time.sleep(0.5)
    camera = vc0706()
    camera.take_photo(photoname)
    relay.off()
    #Photo now is copied to new folder, from there the chk_tpl will sort it.
    os.system('cp ' + photoname + ' /home/satice/new')
    print "Photo %s taken" % photoname 
 
   
if __name__ == '__main__':
    shoot=0 #flag that indicates a photo can be taken
    #Data initialization
    name,hour,minute=timepostfix()
    nowtime=(hour*60+minute)/10000
    photoname = '/home/satice/img/'+ getbuoyname() + name
#   photoname= 'SI94'+name    
    (doy,srise,sdown,tzone)= currentDay()
#    (doy,srise,sdown)= (int(53),0.1150,0.1150)
#    hour=18
#    minute=9
    #dawn and dusk divided into HH mm
    (rim, rih)= formatime(srise)
    (sdm, sdh)= formatime(sdown)
    #last photos taken by the system
    (ldoy,p1,p2)=lastPhoto()    
    #format times to HH mm
    p1=float(p1)
    p2=float(p2)
    (p1m,p1h) = formatime(p1)
    (p2m,p2h) = formatime(p2)
#    print "P1h %s P2h %s Now %s:%s, rise %s:%s, down %s:%s" %(p1h, p2h, hour, minute, rih, rim, sdh, sdm)
    delta=(((hour-rih)*60)+(minute-rim)) #I'd rather take a photo after dawn, therefore delta is always positive
    velta=(((hour-sdh)*60)+(minute-sdm)) #I'd rather take a photo before dusk, therefore velta can be negative
    lighttime=abs((sdh-rih)*60-(sdm-rim)) #Only interested in how many sunlight minutes I have
    wnight=(srise==sdown)#Logic flag indicating winter night
    #Conditions to take the photos
    if ((ldoy-doy)!=0):
        print "Day is incorrect"
        print doy
        print ldoy
        newDay()  
    else:
#        print "Time off dawn %s minutes" %delta
#        print "Time off dusk %s minutes" %velta
        print "Day is correct"
#        if p1<1: print "Dawn photo already taken"
#        if p2<1: print "Dusk photo already taken"
        #Takes the 1st photo 10 minutes after the rising golden hour
        if ((int(p1)>1) and ((delta>10) and (delta<30)) and not(wnight)):
            print "Take dawn photo"
            print "p1 %s" %p1
            print "p2 %s" %p2
            print "Time off dawn %s" %delta
            shoot=1
        #Takes the 2nd photo 10 minutes before down golden hour
        #Only if golden hour happens at least four hours from sunrise or in a day with less than 20 hours of sunlight. 
        elif ((int(p1)<1) and (p2>1) and ((velta<20) and (velta>-10)) and (lighttime>=120) and (lighttime<=1200) and not(wnight)):
            print "Take dusk photo"
            print "p1 %s" %p1
            print "p2 %s" %p2
            print "Time off dusk %s" %velta
            shoot=1
        elif (p1<1) and ((p2<1) or (lighttime<120) or (lighttime>1200)) or (wnight):
            print "Done for today because..."
            if (wnight):
                print "No sunlight hours available"
            elif not(lighttime>=120):
                print "Only dawn photo available, only %s minutes of sunlight today" %(lighttime)
            elif not(1200>=lighttime):
                print "Only dawn photo available, %s minutes of sunlight today, day is too long" %(lighttime)
            else: 
                print "All photos taken"
        else  :
            print "Not yet"
            if (nowtime-srise)>0:
                print "Waiting for dawn"
            else:
                print "Waiting for dusk"
 
    #If everything is under limits, take photo and store
    if shoot==1:
          takephoto(photoname)
          tstamp= float(hour*100 + minute)/10000
          savetime(p1,tstamp,ldoy)
          #Save timestamp to first or second line...

    