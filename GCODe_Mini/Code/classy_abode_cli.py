#!/usr/bin/python

import serial
import serial.tools.list_ports
import time
import re
from datetime import datetime
import matplotlib.pyplot as plt
from pushbullet import Pushbullet
from math import log10

pb_api_key = "o.1Zm51JStkCwZ6X1wKWu369A06fY7upBN"

class gcodemini:
   def __init__(
      self,
      _devUsbSerialNo,
      _pb_api_key,
      _pd_sd_tolerance           = 1,
      _pd_stabilisation_ms       = 2000,
      _pd_stabilisation_attempts = 5,
      _blank_reading             = 700,
      _serial_timeout_s          = 60,
      _cont_sample_interval_s    = 10,
      _gc_od_warning             = .95):
      
      self.devUsbSerialNo              = _devUsbSerialNo
      self.pd_sd_tolerance             = _pd_sd_tolerance
      self.pd_stabilisation_ms         = _pd_stabilisation_ms
      self.pd_stabilisation_attempts   = _pd_stabilisation_attempts
      self.blank_reading               = _blank_reading
      self.serial_timeout_s            = _serial_timeout_s
      self.cont_sample_interval_s      = _cont_sample_interval_s
      self.gc_od_warning               = _gc_od_warning 
      self.pb                          = Pushbullet(_pb_api_key)
     
   def stableBrightIntensity(self):
      # Find and connect to device
      dev      = serial.tools.list_ports.grep(self.devUsbSerialNo).next()
      serDev   = serial.Serial(dev.device, 115200, timeout = self.serial_timeout_s)
      time.sleep(3)
      serDev.flushInput()
      
      # Switch LED on
      serDev.write("LED ON\n")
      time.sleep(1)
      
      # Set maximum number of loops before giving up on stabilisation
      loopLimit = self.pd_stabilisation_attempts
      
      for i in range(loopLimit):
         # Read intensity
         serDev.write("READ " + str(self.pd_stabilisation_ms))
         response = serDev.readline()
         #print response,
         s_readings = re.findall(r"[+-]?\d+\.?\d*", response)
         intensity = float(s_readings[0])
         SD = float(s_readings[1])
         readings = [intensity, SD]
         # If reading stable, turn LED off and return
         if readings[1] < self.pd_sd_tolerance:
            serDev.write("LED OFF\n")
            time.sleep(1)
            return readings[0]
      else:
         print "Reading did not stabilise"
         return -1
   
   def getOD(self):
      return -log10(self.stableBrightIntensity()/self.blank_reading)
      
   def blank(self):
      self.blank_reading   = self.stableBrightIntensity()
      
   def growthCurve(self, dT, N):
      ODs = []
      iteration = 0
      
      while True:
         # Increment the iteration counter
         iteration += 1
         # Get reading
         OD       = self.getOD()
         ODs.append(OD)
         # Print reading along with date, time, iteration
         print datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         print "\t",
         print iteration*float(dT)/60,
         print "\tOD: ",
         print OD
         # If OD too high, send alert
         if OD > self.gc_od_warning:
            print "Alert: OD reaching saturation; OD = ",
            print str(OD)
            self.pb.push_note("Alert: OD reaching saturation; OD = ", str(OD))
         # Plot graph for every reading
         timings     = [i*float(dT)/60 for i in range(iteration)]
         #print timings
         #print ODs
         plt.close()
         plt.plot(timings, ODs)
         plt.show(block=False)
         # Wait until it is time for the next iteration
         if iteration < N:
            time.sleep(dT)
         else:
            self.pb.push_note("Growth curve complete", "")
            plt.close()
            plt.plot(timings,ODs)
            plt.show(block=True)
            break

   def ODmessage(self, dX):
      # Every time reading crosses offset+dX, offset+=dX, and message is sent
      offset = 0
      while True:
         OD       = self.getOD()
         print "OD: ",
         print OD
         if OD > offset:
            offset += dX
            self.pb.push_note("OD alert", str(OD))
         time.sleep(self.cont_sample_interval_s)
      
   def Tmessage(self, dT):
      while True:
         OD       = self.getOD()
         print "Current OD", 
         print OD
         self.pb.push_note("Current OD", str(OD))
         time.sleep(dT)

   def ODalert(self, OD_limit):
      while True:
         OD       = self.getOD()
         print OD
         if OD > OD_limit:
            print "OD Limit Reached"
            self.pb.push_note("OD limit reached: ", str(OD))
            return
         time.sleep(self.cont_sample_interval_s)
      
def findDevices():
   devs = None
   devs = serial.tools.list_ports.grep("2341:0043")
   devList  = []
   if devs is None:
      return devList
      
   for dev in devs:
      print "Found device: ",
      print dev.serial_number
      print ""
      print "Attempting to initialise device..."
      print dev.device
      serDev             = serial.Serial(dev.device, 115200, timeout = 5)
      print "Opening serial port..."
      time.sleep(5)
      serDev.flushInput()
      print "Checking ID..."
      serDev.write("ID\n")
      response = serDev.readline()
      print response,
      if (response.find("ABODe V1.1") >= 0):
         print "Checking FW"
         serDev.write("FW\n")
         response = serDev.readline()
         print response,
         if (float(response) >= 0.2):
            devList.append(dev)
            print "Initialisation successful: Device compatible.\n"
         else:
            print "Initialisation failed : Update Device Firmware.\n"
      else:
         print "Incompatible device.\n"
      serDev.close()
      
   return devList

'''
devList = findDevices()

p = gcodemini(devList[0].serial_number, pb_api_key, 100, 1000)
p.blank()
p.growthCurve(5, 5)
'''
# *********** CLI Body *********

print "CLI Start\n"

# Find attached ABODes
while 1:
   devList = findDevices()
   if (devList == []):
      raw_input("No compatible devices detected. Please connect a compatible device and hit <enter>")
   else:
      break

# Select ABODe
print "Pick a device:"
for i in range(len(devList)):
   print i,
   print "\t",
   print devList[i].serial_number
deviceIndex = input()
mini        = gcodemini(devList[deviceIndex].serial_number, pb_api_key)

# Select procedure
print ""
print "What do you want to do with this device?"
print "0. Growth curve: Take OD readings every time interval T for N iterations"
print "1. Message every dX OD"
print "2. Message every dT time"
print "3. Alert when OD reaches setpoint X"

pI = procedureIndex = input()

raw_input("All procedures require blanking; insert the blank and press <ENTER>:")
mini.blank()

if (pI == 0):
   dT          = input("How often do you want to take the readings? (in minutes): ")
   N           = input("How many readings do you want to take?: ")
   mini.growthCurve(dT*60, N)
elif (pI == 1):
   dX       = input("At what OD intervals do you want a message on your phone? : ")
   mini.ODmessage(dX)
elif (pI == 2):
   dT       = input("How often do you want an OD reading to be sent to your phone? (in minutes): ")
   mini.Tmessage(dT*60)
elif (pI == 3):
   OD_limit = input("What OD do you want an alert at? ")
   mini.ODalert(OD_limit)
else:
   print "Invalid input"

# *********** CLI Body End *********

exit()
