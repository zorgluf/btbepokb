#!/usr/bin/python
#
# Bluetooth keyboard emulator
# 
# Adapted from 
# http://yetanotherpointlesstechblog.blogspot.com/2016/04/emulating-bluetooth-keyboard-with.html
# Under MIT License
##################################################################################
#Copyright (c) 2017 http://yetanotherpointlesstechblog.blogspot.com
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
###################################################################################
#

from __future__ import absolute_import, print_function

from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
from bluetooth.btcommon import BluetoothError
from bluetooth import *
import json


from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject



#
#define a bluez 5 profile object for our keyboard
#
class BTKbBluezProfile(dbus.service.Object):
    fd = -1

    @dbus.service.method("org.bluez.Profile1",
                                    in_signature="", out_signature="")
    def Release(self):
            print("Release")
            mainloop.quit()

    @dbus.service.method("org.bluez.Profile1",
                                    in_signature="", out_signature="")
    def Cancel(self):
            print("Cancel")

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
            self.fd = fd.take()
            print("NewConnection(%s, %d)" % (path, self.fd))
            for key in properties.keys():
                    if key == "Version" or key == "Features":
                            print("  %s = 0x%04x" % (key, properties[key]))
                    else:
                            print("  %s = %s" % (key, properties[key]))
            


    @dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
            print("RequestDisconnection(%s)" % (path))

            if (self.fd > 0):
                    os.close(self.fd)
                    self.fd = -1

    def __init__(self, bus, path):
            dbus.service.Object.__init__(self, bus, path)


#
#create a bluetooth device to emulate a HID keyboard, 
# advertize a SDP record using our bluez profile class
#
class BTKbDevice():
    
    MY_DEV_NAME="Bepo Keyboard"
    PAIRED_HOST_FILE = os.path.dirname(__file__) + "/paired_host" 

    #define some constants
    P_CTRL =17  #Service port - must match port configured in SDP record
    P_INTR =19  #Service port - must match port configured in SDP record#Interrrupt port  
    PROFILE_DBUS_PATH="/bluez/lutze/btbepokb_profile" #dbus path of  the bluez profile we will create
    SDP_RECORD_PATH = os.path.dirname(__file__) + "/sdp_record.xml" #file path of the sdp record to laod
    UUID="00001124-0000-1000-8000-00805f9b34fb"
             
 
    def __init__(self):

        self.active_host = "1"
        self.hosts = dict()
        self.load_hosts()

        self.hotkey = ("",0)

        self.cinterrupt = None
        self.ccontrol = None

        print("Setting up BT device")

        self.init_bt_device()
        self.init_bluez_profile()
        self.start_connect()
                    

    #configure the bluetooth hardware device
    def init_bt_device(self):

        print("Configuring for name "+BTKbDevice.MY_DEV_NAME)
        #set the device up
        os.system("hciconfig hcio up")

        #set the device class to a keybord and set the name
        os.system("hciconfig hcio class 0x002540")
        os.system("hciconfig hcio name \"" + BTKbDevice.MY_DEV_NAME + "\"")

        #make the device discoverable
        os.system("hciconfig hcio piscan")


    #set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):

        print("Configuring Bluez Profile")

        #setup profile options
        service_record=self.read_sdp_service_record()

        opts = {
            "ServiceRecord":service_record,
#            "Role":"server",
            "RequireAuthentication":False,
            "RequireAuthorization":False,
#            "AutoConnect" : True,
        }

        #retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object("org.bluez","/org/bluez"), "org.bluez.ProfileManager1")

        profile = BTKbBluezProfile(bus, BTKbDevice.PROFILE_DBUS_PATH)

        manager.RegisterProfile(BTKbDevice.PROFILE_DBUS_PATH, BTKbDevice.UUID,opts)

        print("Profile registered ")


    #read and return an sdp record from a file
    def read_sdp_service_record(self):

        print("Reading service record")

        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")

        return fh.read()   


    def load_hosts(self):

        if os.path.exists(self.PAIRED_HOST_FILE):
            content = json.loads(open(self.PAIRED_HOST_FILE,"r").read())
            self.active_host = content["activeHost"]
            print("loaded active_host :"+str(self.active_host))
            self.hosts = content["hosts"]
            print("loaded hosts :"+str(self.hosts))

    def save_hosts(self):

        content = { "activeHost": self.active_host, "hosts": self.hosts }
        with open(self.PAIRED_HOST_FILE,"w") as fi:
            fi.write(json.dumps(content))

    def start_connect(self):

        if self.active_host in self.hosts:
            try:
                self.connect(self.hosts[self.active_host])
            except:
                pass
        else:
            self.start_pairing()

    def close_connexions(self):
       
        try:
            self.cinterrupt.close()
            self.ccontrol.close()
        except:
            pass

    def start_pairing(self):

        print("set pairing on on the agent")
        os.system("""bluetoothctl <<EOF
power on
discoverable on
pairable on
agent NoInputNoOutput
default-agent 
EOF""")
        self.listen()

    def listen(self):

        print("Waiting for connections")
        self.scontrol=BluetoothSocket(L2CAP)
        self.sinterrupt=BluetoothSocket(L2CAP)

        #bind these sockets to a port - port zero to select next available		
        self.scontrol.bind(("",self.P_CTRL))
        self.sinterrupt.bind(("",self.P_INTR ))

        #Start listening on the server sockets 
        self.scontrol.listen(1) # Limit of 1 connection
        self.sinterrupt.listen(1)

        self.ccontrol,cinfo = self.scontrol.accept()
        print ("Got a connection on the control channel from " + cinfo[0])

        self.cinterrupt, cinfo = self.sinterrupt.accept()
        print ("Got a connection on the interrupt channel from " + cinfo[0])

        #record new address
        self.hosts[self.active_host] = cinfo[0]
        self.save_hosts()


    def connect(self,addr):
        print("Connecting to known host "+addr)
        self.scontrol=BluetoothSocket(L2CAP)
        self.sinterrupt=BluetoothSocket(L2CAP)

        self.scontrol.connect((addr,self.P_CTRL))
        print ("Connected to the control channel to " + addr)
        self.sinterrupt.connect((addr,self.P_INTR))
        print ("Connected to the interrupt channel to " + addr)
        self.cinterrupt = self.sinterrupt
        self.ccontrol = self.scontrol



    #send a string to the bluetooth host machine
    def send_string(self,message):
        #FIXME : start_connect can block execution, causing dbus timeout
        #capture hotkey F1-F4
        if ord(message[2]) == 1 and ord(message[4]) in range(58,62):
            if ord(message[4]) == self.hotkey[0] and (time.time()-self.hotkey[1])<1:
                #switch active host
                self.active_host = str(self.hotkey[0]-57)
                print("Switch to host "+self.active_host)
                self.save_hosts()
                self.close_connexions()
                self.start_connect()
                return
            #first press of hotkey
            self.hotkey = (ord(message[4]),time.time())
        #capture hotkey F12
        if ord(message[2]) == 1 and ord(message[4]) == 69:
            if ord(message[4]) == self.hotkey[0] and (time.time()-self.hotkey[1])<1:
                #reset active host
                del self.hosts[self.active_host]
                print("Reset host "+self.active_host)
                self.save_hosts()
                self.close_connexions()
                self.start_connect()
                return
            #first press of hotkey
            self.hotkey = (ord(message[4]),time.time())

        try:
            if self.cinterrupt:
                #send key on bt socket
                self.cinterrupt.send(message)
        except BluetoothError:
            #on error, try to reconnect
            self.close_connexions()
            self.start_connect()
            return



#define a dbus service that emulates a bluetooth keyboard
#this will enable different clients to connect to and use 
#the service
class  BTKbService(dbus.service.Object):

    def __init__(self):

        print("Setting up service")

        #set up as a dbus service
        bus_name=dbus.service.BusName("fr.lutze.btbepokbservice",bus=dbus.SystemBus())
        dbus.service.Object.__init__(self,bus_name,"/fr/lutze/btbepokbservice")

        #create and setup our device
        self.device= BTKbDevice();

            
    @dbus.service.method('fr.lutze.btbepokbservice', in_signature='yay')
    def send_keys(self,modifier_byte,keys):

        cmd_str=""
        cmd_str+=chr(0xA1)
        cmd_str+=chr(0x01)
        cmd_str+=chr(modifier_byte)
        cmd_str+=chr(0x00)

        count=0
        for key_code in keys:
            if(count<6):
                cmd_str+=chr(key_code)
            count+=1

        self.device.send_string(cmd_str);		


#main routine
if __name__ == "__main__":
    # we an only run as root
    if not os.geteuid() == 0:
       sys.exit("Only root can run this script")

    DBusGMainLoop(set_as_default=True)
    myservice = BTKbService();

    mainloop = GObject.MainLoop()
    mainloop.run()
