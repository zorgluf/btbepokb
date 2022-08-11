##############################################################################
#
# Copyright (c) 2020 Francois Valley zorgluf@gmail.com
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


import os
import codecs

modkeys = {
   "meta" : 0x80,
   "altgr" : 0x40,
   "Altgr" : 0x40,
   "shift" : 0x20,
   "Shift" : 0x20,
   "shiftr" : 0x20,
   "ctrlr" : 0x10,
   "meta" : 0x08,
   "alt": 0x04,
   "Alt": 0x04,
   "shiftl": 0x02,
   "ctrll": 0x01,
   "Control": 0x10,
   "control": 0x10,
   "plain": 0x00,
}

def loadkeymap(keymapfile):
    out = list()
    with codecs.open(keymapfile,"r",encoding="UTF-16") as kfile:
        layout_section = False
        for line in kfile.readlines():
            #read until LAYOUT line
            if line.startswith("LAYOUT"):
                layout_section = True
                continue
            if layout_section:
                if line.startswith("DEADKEY"):
                    #end of layout : exit
                    break
                if line != "\r\n" and line[0] != "/":
                    #split columns
                    row = line[:-2].replace('\t'," ").split("//")[0].split(" ")
                    row = filter(lambda item: item != "",row)
                    #convert all char to code
                    for i in range(3,8):
                        if len(row) > i and len(row[i]) == 1:
                            row[i] = '{:04x}'.format(ord(row[i]))
                    #c1
                    if row[3] != "-1":
                        out.append([ row[3], int(row[0],16), 0])
                    #c2 : shift
                    if len(row) > 4 and row[4] != "-1":
                        out.append([ row[4], int(row[0],16), modkeys["shiftr"] ])
                        out.append([ row[4], int(row[0],16), modkeys["shiftl"] ])
                    #c3 : Ctrl
                    if len(row) > 5 and row[5] != "-1":
                        out.append([ row[5], int(row[0],16), modkeys["ctrll"] ])
                        out.append([ row[5], int(row[0],16), modkeys["ctrlr"] ])
                    #c4 : Ctrl + Alt, altgr
                    if len(row) > 6 and row[6] != "-1":
                        out.append([ row[6], int(row[0],16), modkeys["altgr"] ])
                        out.append([ row[6], int(row[0],16), modkeys["ctrlr"] ^ modkeys["alt"] ])
                        out.append([ row[6], int(row[0],16), modkeys["ctrll"] ^ modkeys["alt"] ])
                    #c5 : shift + Ctrl + Alt, shift + altgr
                    if len(row) > 7 and row[7] != "-1":
                        out.append([ row[7], int(row[0],16), modkeys["altgr"] ^ modkeys["shiftr"] ])
                        out.append([ row[7], int(row[0],16), modkeys["altgr"] ^ modkeys["shiftl"] ])
                        out.append([ row[7], int(row[0],16), modkeys["alt"] ^ modkeys["shiftr"] ^ modkeys["ctrlr"] ])
                        out.append([ row[7], int(row[0],16), modkeys["alt"] ^ modkeys["shiftr"] ^ modkeys["ctrlr"] ])
                        out.append([ row[7], int(row[0],16), modkeys["alt"] ^ modkeys["shiftl"] ^ modkeys["ctrll"] ])
                        out.append([ row[7], int(row[0],16), modkeys["alt"] ^ modkeys["shiftl"] ^ modkeys["ctrlr"] ])
    return out

'''
build a keymap conv table
table[keycode_ori][modkey_ori] = (keycode_dest,modkey_dest)
'''
def build_table(keymap1, keymap2):
    table = dict()
    missings = dict()
    for key1 in keymap1:
        found = False
        for key2 in keymap2:
            if key1[0] == key2[0]:
                if key1[1] not in table:
                    table[key1[1]] = dict()
                if key1[2] in table[key1[1]]:
                    #try to prioritise matching modkey
                    if key1[2] == key2[2]:
                        table[key1[1]][key1[2]] = (key2[1],key2[2])
                        #print "T: "+str(key1[1])+"/"+str(key1[2])+" <- "+str(key2[1])+"/"+str(key2[2])+" : "+str(key2[0])
                    #otherwise, keep the old key
                else:
                    table[key1[1]][key1[2]] = (key2[1],key2[2])
                    #print "F: "+str(key1[1])+"/"+str(key1[2])+" <- "+str(key2[1])+"/"+str(key2[2])+" : "+str(key2[0])
                found = True
        if not found:
            if key1[1] not in missings:
                missings[key1[1]] = dict()
            missings[key1[1]][key1[2]] = key1
    return (table,missings)
        

if __name__=="__main__":
    bepo_map = loadkeymap(os.path.dirname(__file__) + "/windows_bepo.klc")
    print "Bepo map sample :"
    print bepo_map
    fr_map = loadkeymap(os.path.dirname(__file__) + "/KBDFR.klc")
    print "Azerty map sample :"
    print fr_map
    (table, missings) = build_table(bepo_map,fr_map)
    print "table sample:"
    print table
    print "missings"
    print missings

