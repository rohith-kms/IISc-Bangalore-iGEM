#!/usr/bin/python

import serial
import serial.tools.list_ports
import time
from time import sleep
import re
from datetime import datetime
import matplotlib.pyplot as plt
from pushbullet import Pushbullet
from pushbullet import InvalidKeyError
from requests import ConnectionError
from math import log10
from Tkinter import *
import tkMessageBox
import os
import csv

testing = True

pb_api_key = ""

# ********** GUI Setup **********

root = Tk()

# Frames

pb_key_screen = Frame(root)
loading_screen = Frame(root)
device_selection_screen = Frame(root)
method_selection_screen = Frame(root)
curve_parameters_screen = Frame(root)
od_parameters_screen = Frame(root)
time_parameters_screen = Frame(root)
setpoint_parameters_screen = Frame(root)
filename_screen = Frame(root)
exit_screen = Frame(root)

# Screen to obtain OD Growth Curve parameters

Label(curve_parameters_screen, text="How often do you want to take the readings? (in minutes): ").pack()
dT = Entry(curve_parameters_screen)
dT.pack()
Label(curve_parameters_screen, text="How many readings do you want to take?: ").pack()
N = Entry(curve_parameters_screen)
N.pack()

# Screen to obtain OD Interval message parameters

Label(od_parameters_screen, text="At what OD intervals do you want a message on your phone? : ").pack()
dX = Entry(od_parameters_screen)
dX.pack()

# Screen to obtain time interval message parameters

Label(time_parameters_screen, text="How often do you want an OD reading to be sent to your phone? (in minutes): ").pack()
dT1 = Entry(time_parameters_screen)
dT1.pack()

# Screen to obtain setpoint parameters

Label(setpoint_parameters_screen, text="What OD do you want an alert at? ").pack()
sp = Entry(setpoint_parameters_screen)
sp.pack()

# Screen to obtain filename

Label(filename_screen, text="Enter a name for output file").pack()
filename_field = Entry(filename_screen)
filename_field.pack()

loading_screen.pack()

status = StringVar()
status.set("Loading")

loading_statement_label = Label(loading_screen, textvariable = status)
loading_statement_label.pack()

root.update_idletasks()

# ********** GUI Setup ends **********

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

    def push(self, str1, str2):
        while 1:
            try:
                self.pb.push_note(str1,str2)
                break
            except ConnectionError:
                tkMessageBox.showerror("Internet not available", "Your internet connection seems broken, please check and try again")

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
                return float('nan')

    def getOD(self):
        return -log10(self.stableBrightIntensity()/self.blank_reading)

    def blank(self):
        self.blank_reading   = self.stableBrightIntensity()

    def growthCurve(self, dT, N):
        ODs = []
        iteration = 0
        nextJobTime = time.time()
        f, ax = plt.subplots()
        with open(filename, 'w+b') as csvfile:
            datawriter = csv.writer(csvfile, delimiter=',')
            datawriter.writerow(['Time', 'Iteration', 'OD'])

        while True:
            if time.time() < nextJobTime:
                time.sleep(1)
            else:
                # Set next job time
                nextJobTime = time.time() + dT
                # Increment the iteration counter
                iteration += 1
                # Get reading
                OD       = self.getOD()
                ODs.append(OD)
                # Print reading along with date, time, iteration
                with open(filename, 'ab') as csvfile:
                    datawriter = csv.writer(csvfile, delimiter=',')
                    datawriter.writerow([datetime.now().strftime('%H:%M:%S')]+[iteration*float(dT)/60]+[OD])

                print datetime.now().strftime('%Y-%m-%d %H:%M:%S'),"\t",
                print iteration*float(dT)/60, "\t",
                print "OD: ", OD
                # If OD too high, send alert
                if OD > self.gc_od_warning:
                    print "Alert: OD reaching saturation; OD = ",
                    print str(OD)
                    self.push("Alert: OD reaching saturation; OD = ", str(OD))
                # Plot graph for every reading
                timings = [i*float(dT)/60 for i in range(iteration)]
                plt.cla()
                ax.plot(timings, ODs)
                plt.pause(.01)
                ax.relim()
                ax.autoscale_view()
                plt.draw()
                plt.pause(0.01)
                # Wait until it is time for the next iteration
                if iteration >= N:
                    self.push("Growth curve complete", "")
                    plt.show(block=True)
                    break

    def ODmessage(self, dX):
        # Every time reading crosses offset+dX, offset+=dX, and message is sent
        with open(filename, 'w+b') as csvfile:
            datawriter = csv.writer(csvfile, delimiter=',')
            datawriter.writerow(['OD', 'Time'])
        offset = 0
        while True:
            OD       = self.getOD()
            with open(filename, 'ab') as csvfile:
                datawriter = csv.writer(csvfile, delimiter=',')
                datawriter.writerow([OD]+[datetime.now().strftime('%H:%M:%S')])
            print "OD: ",
            print OD
            if OD > offset:
                offset += dX
                self.push("OD alert", str(OD))
            time.sleep(self.cont_sample_interval_s)

    def Tmessage(self, dT):
        with open(filename, 'w+b') as csvfile:
            datawriter = csv.writer(csvfile, delimiter=',')
            datawriter.writerow(['Time', 'OD'])
        while True:
            OD       = self.getOD()
            with open(filename, 'ab') as csvfile:
                datawriter = csv.writer(csvfile, delimiter=',')
                datawriter.writerow([datetime.now().strftime('%H:%M:%S')]+[OD])
            print "Current OD",
            print OD
            self.push("Current OD", str(OD))
            time.sleep(dT)

    def ODalert(self, OD_limit):
        while True:
            OD       = self.getOD()
            print OD
            if OD > OD_limit:
                print "OD Limit Reached"
                self.push("OD limit reached: ", str(OD))
                with open(filename, 'ab') as csvfile:
                    datawriter = csv.writer(csvfile, delimiter=',')
                    datawriter.writerow([datetime.now().strftime('%H:%M:%S')]+[OD])
                return
            time.sleep(self.cont_sample_interval_s)

def findDevices():
    devs = None
    devs = serial.tools.list_ports.grep("2341")
    devList  = []
    if devs is None:
      return devList

    for dev in devs:
        statement = "\nFound device: " + str(dev.serial_number)
        status.set(statement)
        root.update_idletasks()
        time.sleep(0.1)
        # print "Found device: ",
        # print dev.serial_number
        # print ""
        statement += "\nAttempting to initialise device..." + str(dev.device)
        status.set(statement)
        root.update_idletasks()
        time.sleep(0.1)
        # print "Attempting to initialise device..."
        # print dev.device
        serDev             = serial.Serial(dev.device, 115200, timeout = 5)
        statement += "\nOpening serial port"
        status.set(statement)
        root.update_idletasks()
        # print "Opening serial port..."
        time.sleep(5)
        serDev.flushInput()
        statement += "\nChecking ID..."
        status.set(statement)
        root.update_idletasks()
        sleep(0.1)
        # print "Checking ID..."
        serDev.write("ID\n")
        response = serDev.readline()
        statement += "\n"+response
        status.set(statement)
        root.update_idletasks()
        sleep(0.1)
        # print response,
        if (response.find("ABODe V1.1") >= 0):
            statement += "Checking FW"
            status.set(statement)
            root.update_idletasks()
            sleep(0.1)
            # print "Checking FW"
            serDev.write("FW\n")
            response = serDev.readline()
            statement += response
            status.set(statement)
            root.update_idletasks()
            sleep(0.1)
            # print response,
            if (float(response) >= 0.2):
                devList.append(dev)
                statement += "Initialisation successful: Device compatible."
                status.set(statement)
                root.update_idletasks()
                sleep(0.1)
                # print "Initialisation successful: Device compatible.\n"
            else:
                statement += "Initialisation failed : Update Device Firmware."
                status.set(statement)
                root.update_idletasks()
                sleep(0.1)
                # print "Initialisation failed : Update Device Firmware.\n"
        else:
            statement += "\nIncompatible device."
            status.set(statement)
            root.update_idletasks()
            sleep(0.1)
            # print "Incompatible device.\n"
        serDev.close()

    return devList

# *********** GUI Body *********

print "GUI Start\n"

def show_device_screen():
    global pb_api_key
    global mini
    pb_api_key = pb_key_input.get()
    while 1:
        try:
            pb_temp = Pushbullet(pb_api_key)
            with open('pbkey.txt', 'w+') as f:
                f.write(pb_api_key)
            pb_key_screen.pack_forget()
            if len(devList)==1:
                if testing:
                    mini = gcodemini(devList[0].serial_number, pb_api_key,100, 1000)
                else:
                    mini = gcodemini(devList[0].serial_number, pb_api_key)

                method_selection_screen.pack()
            else:
                device_selection_screen.pack()
            break
        except ConnectionError:
            tkMessageBox.showerror("Internet not available", "Your internet connection seems broken, please check and try again")
        except InvalidKeyError:
            tkMessageBox.showerror("Error", "Invalid PushBullet key, please try again")
            break

def show_method_screen():
    deviceIndex = listbox.curselection()[0]
    global mini
    if testing:
        mini = gcodemini(devList[deviceIndex].serial_number, pb_api_key,100, 1000)
    else:
        mini = gcodemini(devList[deviceIndex].serial_number, pb_api_key)
    method_selection_screen.pack()
    device_selection_screen.pack_forget()

# Find attached ABODes
while 1:
    global devList
    devList = findDevices()
    if (devList == []):
        tkMessageBox.showerror("Error", "No compatible devices detected. Please connect a compatible device and press ok.")
    else:
        break

# Select ABODe

def get_blank():
    tkMessageBox.showinfo("Insert blank solution", "All procedures require blanking; insert the blank solution and press ok.")
    mini.blank()

if os.path.isfile('pbkey.txt'):
    global mini
    with open('pbkey.txt') as f:
        pb_api_key = f.read()

    if len(devList)==1:
        if testing:
            mini = gcodemini(devList[0].serial_number, pb_api_key,100, 1000)
        else:
            mini = gcodemini(devList[0].serial_number, pb_api_key)

        method_selection_screen.pack()
    else:
        device_selection_screen.pack()
else:
    pb_key_screen.pack()

Label(pb_key_screen, text="Enter your Pushbullet key as described in the documentation.").pack()
pb_key_input = Entry(pb_key_screen)
pb_key_input.pack()
Button(pb_key_screen, text="Next", command=show_device_screen).pack()

loading_screen.pack_forget()

Label(device_selection_screen, text="Pick a device:").pack()
listbox = Listbox(device_selection_screen)
listbox.pack()
for i in range(len(devList)):
    listbox.insert(END, str(i)+"\t"+str(devList[i].serial_number))

Button(device_selection_screen, text = "Next", command = show_method_screen).pack()

# Select procedure

Label(method_selection_screen, text="What do you want to do with this device?").pack()

def exit_program():
    exit()

def create_file(filename_holder):
    global filename
    filename = filename_holder+".csv"
    with open(filename, 'w+b') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',')
        datawriter.writerow(['File created: '+str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))])

def curve_screen():
    try:
        x = float(dT.get())
        y = int(N.get())
        filename_holder = filename_field.get()
        try:
            create_file(filename_holder)
        except IOError:
            tkMessageBox.showerror("Invalid file name", "Please enter a valid name.")

        curve_parameters_screen.pack_forget()
        filename_screen.pack_forget()
        exit_screen.pack()
        mini.growthCurve(x*60, y)
    except ValueError:
        tkMessageBox.showerror("Incorrect Input", "You have input a wrong value.")

def od_screen():
    try:
        x = float(dX.get())
        filename_holder = filename_field.get()
        create_file(filename_holder)
        od_parameters_screen.pack_forget()
        filename_screen.pack_forget()
        exit_screen.pack()
        mini.ODmessage(dX)
    except ValueError:
        tkMessageBox.showerror("Incorrect Input", "You have input a wrong value.")

def time_screen():
    try:
        x = float(dT1.get())
        filename_holder = filename_field.get()
        create_file(filename_holder)
        time_parameters_screen.pack_forget()
        filename_screen.pack_forget()
        exit_screen.pack()
        mini.Tmessage(x*60)
    except ValueError:
        tkMessageBox.showerror("Incorrect Input", "You have input a wrong value.")

def setpoint_screen():
    try:
        x = float(sp.get())
        filename_holder = filename_field.get()
        create_file(filename_holder)
        time_parameters_screen.pack_forget()
        filename_screen.pack_forget()
        exit_screen.pack()
        mini.ODalert(x)
    except ValueError:
        tkMessageBox.showerror("Incorrect Input", "You have input a wrong value.")

def curve():
    get_blank()
    method_selection_screen.pack_forget()
    Button(curve_parameters_screen, text="Next", command=curve_screen).pack()
    filename_screen.pack()
    curve_parameters_screen.pack()

def take_od():
    get_blank()
    method_selection_screen.pack_forget()
    Button(od_parameters_screen, text="Next", command=od_screen).pack()
    filename_screen.pack()
    od_parameters_screen.pack()

def take_time():
    get_blank()
    method_selection_screen.pack_forget()
    Button(time_parameters_screen, text="Next", command=time_screen).pack()
    filename_screen.pack()
    time_parameters_screen.pack()

def alert_setpoint():
    get_blank()
    method_selection_screen.pack_forget()
    Button(setpoint_parameters_screen, text="Next", command=setpoint_screen).pack()
    filename_screen.pack()
    setpoint_parameters_screen.pack()

Button(method_selection_screen, text="Growth curve: Take OD readings every time interval T for N iterations", command=curve).pack()
Button(method_selection_screen, text="Message every dX OD", command=take_od).pack()
Button(method_selection_screen, text="Message every dT time", command=take_time).pack()
Button(method_selection_screen, text="Alert when OD reaches setpoint X", command=alert_setpoint).pack()

Button(exit_screen, text="Exit Program", command=exit_program).pack()

# *********** GUI Body End *********

root.mainloop()
exit()
