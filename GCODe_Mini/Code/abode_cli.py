#!/usr/bin/python
# usage: send_and_receive_arduino <DEVICE> <BAUDRATE> <TEXT>
# where <DEVICE> is typically some /dev/ttyfoobar
# and where <BAUDRATE> is the baudrate
# and where <TEXT> is a text, e.g. "Hello"
import sys
import serial
import time
import re
import serial.tools.list_ports
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from pushbullet import Pushbullet
from math import log10

SD_TOL                     = 1
LED_STABILISE_MS           = 10000
SER_TIMOUT_S               = 60
ALERT_SAMPLING_INTERVAL_S  = 10
MSG_SAMPLING_INTERVAL_S    = 10
GC_OD_LIMIT                = .95

pb = Pushbullet("o.1Zm51JStkCwZ6X1wKWu369A06fY7upBN")

def findDevices():
   devs = 0
   devs = serial.tools.list_ports.grep("2341:0043")
   if (devs == 0):
      return 0
   else:
      devList            = []
      
   for dev in devs:
      print "Found device: ",
      print dev.serial_number
      print ""
      print "Attempting to initialise device..."
      print dev.device
      serDev             = serial.Serial(dev.device, 115200, timeout = SER_TIMOUT_S)
      print "Opening serial port..."
      time.sleep(3)
      serDev.flushInput()
      print "Checking ID..."
      serDev.write("ID\n")
      time.sleep(2)
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

def switchLED(serDev, status):
    if (status == "on"):
        serDev.write("LED ON\n")
        time.sleep(1)
    elif (status == "off"):
        serDev.write("LED OFF\n")
        time.sleep(1)
    else:
        print 'Invalid input: switchLED("on") or switchLED("off")'
    return

def readIntensity(serDev, ms_duration):
    serDev.write("READ " + str(ms_duration))
    #serDev.write("READ 1000\n")
    time.sleep(2)
    response = serDev.readline()
    #print response,
    s_readings = re.findall(r"[+-]?\d+\.?\d*", response)
    intensity = float(s_readings[0])
    SD = float(s_readings[1])
    readings = [intensity, SD]
    return readings

def readStableBrightIntensity(usbSerialNo, ms_duration, sd_tolerance):
   # Find and connect to device
   dev      = serial.tools.list_ports.grep(usbSerialNo).next()
   serDev   = serial.Serial(dev.device, 115200, timeout = SER_TIMOUT_S)
   time.sleep(3)
   serDev.flushInput()
   
   # Switch LED on
   switchLED(serDev, "on")
   
   # Set maximum number of loops before giving up on stabilisation
   loopLimit = 5
   
   for i in range(loopLimit):
      readings = readIntensity(serDev, ms_duration)
      # If reading stable, return
      if readings[1] < sd_tolerance:
         switchLED(serDev, "off")
         return readings
   else:
      print "Reading did not stabilise"
      return [-1,-1]

def intervalJob(s_interval, iterations, job, *args):
    n = iterations
    i = 0
    nextJobTime = time.time()
    while True:
        if i<n:
            if time.time() < nextJobTime:
                time.sleep(1)
            else:
                i += 1
                job(*args)
        else:
            return

def growthCurve(usbSerialNo, dT, iterations):
   ODs = []
   i0 = CLIblank(usbSerialNo)
   iteration = 0
   raw_input("Now, insert sample and press <ENTER>")
   
   while True:
      # Increment the iteration counter
      iteration += 1
      # Get reading
      reading  = readStableBrightIntensity(usbSerialNo,LED_STABILISE_MS,SD_TOL)
      OD       = -log10(reading[0]/i0)
      ODs.append(OD)
      # Print reading along with date, time, iteration
      print datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
      print "\t",
      print str(iteration*dT/60),
      print "\tOD: ",
      print OD
      # If OD too high, send alert
      if OD > GC_OD_LIMIT:
         pb.push_note("Alert: OD reaching saturation; OD = ", str(OD))
      # Plot graph for every reading
      timings     = [i*dT/60 for i in range(iteration)]
      #print timings
      #print ODs
      plt.close()
      plt.plot(timings, ODs)
      plt.show(block=False)
      # Wait until it is time for the next iteration
      if iteration < iterations:
         time.sleep(dT)
      else:
         pb.push_note("Growth curve complete", "")
         plt.close()
         plt.plot(timings,ODs)
         plt.show(block=True)
         break

def ODmessage(usbSerialNo, dX, samplingInterval):
   # Every time reading crosses offset+dX, offset+=dX, and message is sent
   offset = 0
   i0 = CLIblank(usbSerialNo)
   raw_input("Now, insert sample and press <ENTER>")
   while True:
      reading  = readStableBrightIntensity(usbSerialNo,LED_STABILISE_MS,SD_TOL)
      OD       = -log10(reading[0]/i0)
      print "OD: ",
      print OD
      if OD > offset:
         offset += dX
         pb.push_note("OD alert", str(OD))
      time.sleep(samplingInterval)
   
def Tmessage(usbSerialNo, samplingInterval):
   i0 = CLIblank(usbSerialNo)
   raw_input("Now, insert sample and press <ENTER>")
   while True:
      reading  = readStableBrightIntensity(usbSerialNo,LED_STABILISE_MS,SD_TOL)
      OD       = -log10(reading[0]/i0)
      print OD
      pb.push_note("Current OD", str(OD))
      time.sleep(samplingInterval)
   
def ODalert(usbSerialNo, OD_limit, samplingInterval):
   i0 = CLIblank(usbSerialNo)
   raw_input("Now, insert sample and press <ENTER>")
   while True:
      reading  = readStableBrightIntensity(usbSerialNo,LED_STABILISE_MS,SD_TOL)
      OD       = -log10(reading[0]/i0)
      print OD
      if OD > OD_limit:
         print "OD Limit Reached"
         pb.push_note("OD alert", str(OD))
         return
      time.sleep(samplingInterval)

def CLIblank(usbSerialNo):
   raw_input("Insert blank reading into device, and press <ENTER>")
   i0 = readStableBrightIntensity(usbSerialNo,LED_STABILISE_MS,SD_TOL)
   print "Blank reading: ",
   print i0[0]
   return i0[0]

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
dev         = devList[deviceIndex].device
devSerial   = devList[deviceIndex].serial_number

# Select procedure
print ""
print "What do you want to do with this device?"
print "0. Growth curve: Take OD readings every time interval T for N iterations"
print "1. Message every dX OD"
print "2. Message every dT time"
print "3. Alert when OD reaches setpoint X"

pI = procedureIndex = input()

if (pI == 0):
   dT          = input("How often do you want to take the readings? (in minutes): ")*60
   iterations  = input("How many readings do you want to take?: ")
   growthCurve(devSerial, dT, iterations)
elif (pI == 1):
   dX       = input("At what OD intervals do you want a message on your phone? : ")
   ODmessage(devSerial, dX, MSG_SAMPLING_INTERVAL_S)
elif (pI == 2):
   dT       = input("How often do you want an OD reading to be sent to your phone? (in minutes): ")
   Tmessage(devSerial, dT*60)
elif (pI == 3):
   OD_limit = input("What OD do you want an alert at? ")
   ODalert(devSerial, OD_limit, ALERT_SAMPLING_INTERVAL_S)
else:
   print "Invalid input"

# *********** CLI Body End *********

exit()

'''

def growthCurveStep():
    print datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    i = readStableBrightIntensity(2000, 100)
    #i = [500,10]
    print i
    global I
    I = np.append(I, i[0])
    
def readStableDarkIntensity(dev, ms_duration, sd_tolerance):
    switchLED("off")
    while True:
        readings = readIntensity(ms_duration)
        if readings[1] < sd_tolerance:
            return readings

def findUno():
    dev = serial.tools.list_ports.grep("2341:0043")
    uno = 0
    uno = dev.next().device
    return uno

def initUno():
    print "Initialising ABODe Machine V1.1 FW 0.2"

    global uno
    uno = serial.Serial()
    uno.port = findUno()
    if (uno.port == 0):
     print "No device found. Please connect device"
     # Wait until device is found
     exit()
    uno.baudrate = 115200
    uno.open()
    time.sleep(3)
    uno.flushInput()

    print "Checking device ID:"
    uno.write("ID")
    time.sleep(1)
    response = uno.readline()
    print response,
    if (response.find("ABODe V1.1") >= 0):
        uno.write("FW")
        time.sleep(1)
        response = uno.readline()
        print response,
        if (float(response) >= 0.2):
            print "Initialisation successful: Device Compatible\n"
            return
        else:
            print "Initialisation failed: Update Device Firmware"
    else:
        print "Initialisation failed: Unrecognised device"
    exit()

def readStableIntensity(ms_duration, sd_tolerance):
    return (np.array(readStableBrightIntensity(ms_duration, sd_tolerance))
            - np.array(readStableDarkIntensity(ms_duration, sd_tolerance)))
'''