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
import json

class btkbconfig:

    filename = os.path.dirname(__file__) + "/paired_host"
    active_host = "1"
    hosts = dict()

    def __init__(self,filename=None):
        if filename:
            self.filename = filename
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            content = json.loads(open(self.filename,"r").read())
            self.active_host = content["active_host"]
            print("loaded active_host :"+str(self.active_host))
            self.hosts = content["hosts"]
            print("loaded hosts :"+str(self.hosts))

    def save(self):
        content = { "active_host": self.active_host, "hosts": self.hosts }
        with open(self.filename,"w") as fi:
            fi.write(json.dumps(content))

    def get_active_host(self):
        return self.get_host(self.active_host)

    def get_active_host_addr(self):
        return self.get_host_addr(self.active_host)

    def get_active_host_mapping_status(self):
        return self.get_host_mapping_status(self.active_host)

    def switch_active_host_mapping_status(self):
        self.set_active_host(self.get_active_host_addr(),not(self.get_active_host_mapping_status()))

    def set_active_host(self,addr,mapping_status=True):
        self.set_host(self.active_host,addr,mapping_status)

    def set_active_host_index(self,i):
        self.active_host = i
        self.save()

    def get_active_host_index(self):
        return self.active_host

    def get_host(self,i):
        self.load()
        if i in self.hosts.keys():
            return self.hosts[i]
        else:
            return None

    def get_host_addr(self,i):
        if self.get_host(i):
            return self.hosts[i]["addr"]
        else:
            return None

    def get_host_mapping_status(self,i):
        if self.get_host(i):
            return self.hosts[i]["mapping_status"]
        else:
            return None

    def set_host(self,i,addr,mapping_status=True):
        self.hosts[i] = { "addr": addr, "mapping_status": mapping_status }
        self.save()

    def del_host(self,i):
        del self.hosts[self.active_host]
        self.save()

