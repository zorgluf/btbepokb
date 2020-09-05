#!/usr/bin/python
#
##############################################################################
#
# Copyright (c) 2020  Francois Valley zorgluf@gmail.com
#
#This file is part of btbepokb.
#
#    btbepokb is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    later version.
#
#    btbepokb is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with btbepokb.  If not, see <https://www.gnu.org/licenses/>.
#############################################################################
#
# Bluetooth keyboard emulation and convertor service
# Reads local key events, map them from bepo to azerty and forwards them to the btk_server DBUS service
#
# Based (but largely modified) on the work of keef from http://yetanotherpointlesstechblog.blogspot.com/2016/04/emulating-bluetooth-keyboard-with.html
#
#
import os
import sys
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import evdev
from evdev import *
import keymap # used to map evdev input to hid keodes
from keymapconv import loadkeymap, build_table
from utils.config import btkbconfig

WIN_MODE = True
AZERTY_SHORTCUTS = False

#Define a client to listen to local key events
class Keyboard():


        def __init__(self):

                #load config
                self.config = btkbconfig()

                #keyboard state
                self.modkeys = 0x00
                self.keysarray = list()
                self.new_modkeys = 0
                self.new_keysarray = [ 0 ] * 6

                self.hotkey = ("",0)
                self.mapping_status = self.config.get_active_host_mapping_status()

                print "setting up DBus Client"  

                self.bus = dbus.SystemBus()
                self.btkservice = self.bus.get_object('fr.lutze.btbepokbservice','/fr/lutze/btbepokbservice')
                self.iface = dbus.Interface(self.btkservice,'fr.lutze.btbepokbservice')    

                print "load bepo conversion table"
                bepo_map = loadkeymap(os.path.dirname(__file__) + "/windows_bepo.klc")
                fr_map = loadkeymap(os.path.dirname(__file__) + "/KBDFR.klc")
                (self.bepotable, self.missings) = build_table(bepo_map,fr_map)
                '''
                print "load CP850/unicode table"
                self.CP850_map = dict()
                with open(os.path.dirname(__file__) + "/CP850.TXT","r") as f:
                    for line in f.readlines():
                        if len(line) > 5 and line[0] not in ("#", "\n"):
                            (cp850,uni) = line.split("\t")[:2]
                            self.CP850_map[int(uni,16)] = int(cp850,16)
                '''
                print "load CP1252/unicode table"
                self.CP1252_map = dict()
                with open(os.path.dirname(__file__) + "/CP1252.TXT","r") as f:
                    for line in f.readlines():
                        if len(line) > 5 and line[0] not in ("#", "\n"):
                            (cp1252,uni) = line.split("\t")[:2]
                            try:
                                self.CP1252_map[int(uni,16)] = int(cp1252,16)
                            except:
                                pass
                            

                print "waiting for keyboard"

                #keep trying to key a keyboard
                have_dev=False
                while have_dev==False:
                        try:
                                #try and get a keyboard - should always be event0 as
                                #we're only plugging one thing in
                                self.dev = InputDevice("/dev/input/event0")
                                have_dev=True
                        except OSError:
                                print "Keyboard not found, waiting 10 seconds and retrying"
                                time.sleep(10)
                        print "found a keyboard"

        def change_state(self,key,is_pressed):
            #if modkey pressed/released
            evdev_code=ecodes.KEY[key]
            modkey_element = keymap.modkey(evdev_code)
            if modkey_element > 0:
                #modify state
                self.modkeys = self.modkeys ^ (0x80 >> modkey_element)
            else:
                #test if key pressed or released
                if is_pressed:
                    self.keysarray.append(key)
                else:
                    if key in self.keysarray:
                        self.keysarray.remove(key)

        #poll for keyboard events
        def event_loop(self):
                for event in self.dev.read_loop():
                        #only bother if we hit a key and its an up or down event
                        if event.type==ecodes.EV_KEY and event.value < 2:
                                #print "debug code :"+str(event.code)+"/"+str(event.value)
                                #test if mapping (translation) activated
                                if self.mapping_status:
                                    #check for key/char not translatable into azerty : try win alt combo
                                    if WIN_MODE and event.value == 1 and event.code in self.missings and self.modkeys in self.missings[event.code]:
                                        #check if char exists in CP1252
                                        unikey = int(self.missings[event.code][self.modkeys][0],16)
                                        if unikey in self.CP1252_map:
                                            self.send_using_alt_combo(unikey)
                                            continue
                                    #update internal state
                                    self.change_state(event.code,event.value)
                                    #translation bepo -> azerty
                                    self.translate()
                                    #print "after translation : "+str(self.new_modkeys)+"/"+str(self.new_keysarray)
                                else:
                                    self.copy(event.code,event.value)
                                self.send_input()

        def copy(self,key,is_pressed):
            #if modkey pressed/released
            evdev_code=ecodes.KEY[key]
            modkey_element = keymap.modkey(evdev_code)
            if modkey_element > 0:
                #modify state
                self.modkeys = self.modkeys ^ (0x80 >> modkey_element)
            else:
                #test if key pressed or released
                if is_pressed:
                    self.keysarray.append(key)
                else:
                    if key in self.keysarray:
                        self.keysarray.remove(key)
            self.new_keysarray = [ 0 ] * 6
            for i,key in enumerate(self.keysarray):
                self.new_keysarray[i] = key
            self.new_modkeys = self.modkeys

        def translate(self):
            self.new_keysarray = [ 0 ] * 6
            self.new_modkeys = self.modkeys
            for i in range(len(self.keysarray)-1,-1,-1):
                key = self.keysarray[i]
                #check if a mapping is needed
                if key in self.bepotable:
                    if self.modkeys in self.bepotable[key]:
                        if self.new_modkeys == self.bepotable[key][self.modkeys][1]:
                            self.new_keysarray[len(self.keysarray)-i-1] = self.bepotable[key][self.modkeys][0]
                            self.new_modkeys = self.bepotable[key][self.modkeys][1]
                            continue
                        else: #if we have diff keymod -> conflict, we take the last key only
                            self.new_keysarray = [ 0 ] * 6
                            self.new_keysarray[0] = self.bepotable[key][self.modkeys][0]
                            self.new_modkeys = self.bepotable[key][self.modkeys][1]
                            return
                    if not AZERTY_SHORTCUTS and self.modkeys in [ 128, 16, 8, 1 ]: #in case of meta or ctrl key pressed, we try to convert sc (modkeys = 0) even if not in translation table
                        self.new_keysarray[len(self.keysarray)-i-1] = self.bepotable[key][0][0]
                        continue
                self.new_keysarray[len(self.keysarray)-i-1] = key
                self.new_modkeys = self.modkeys

        def send_using_alt_combo(self,code):
            self.new_modkeys = 4
            #send 0
            self.new_keysarray[0] = ecodes.ecodes["KEY_KP0"]
            self.send_input()
            self.new_keysarray[0] = 0
            self.send_input()
            #convert unicode to CP1252
            cp1252 = str(self.CP1252_map[code])
            #send combo (using keypad)
            for c in cp1252:
                self.new_keysarray[0] = ecodes.ecodes["KEY_KP"+c]
                self.send_input()
                self.new_keysarray[0] = 0
                self.send_input()

        #forward keyboard events to the dbus service
        def send_input(self):
            keysarray = [0] * 6
            #convert sc to HID keycode
            for i,k in enumerate(self.new_keysarray):
                keysarray[i] = keymap.convert(ecodes.KEY[self.new_keysarray[i]])
            #print("Send modkey/keyarray : "+str(modkey)+"/"+str(keysarray))
            self.iface.send_keys(self.new_modkeys,keysarray)

            #detect special ctrl key combinations
            #capture hotkey F10
            if self.new_modkeys == 1 and keysarray[0] == 67:
                if keysarray[0] == self.hotkey[0] and (time.time()-self.hotkey[1])<1:
                    #switch mapping status
                    self.config.switch_active_host_mapping_status()
                    self.mapping_status = not(self.mapping_status)
                    print("Set mapping status to "+str(self.mapping_status))
                #first press of hotkey
                self.hotkey = (keysarray[0],time.time())




if __name__ == "__main__":

        print "Setting up keyboard"
        kb = Keyboard()

        print "starting event loop"
        kb.event_loop()

