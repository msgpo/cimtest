#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Dan Smith <danms@us.ibm.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#
"""Some utilities to xenoblade test suite
"""

import os
import commands

# ssh utils

SSH_PARMS="-q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
root_dot_ssh = os.path.join(os.getenv('HOME'), '.ssh')
SSH_KEY = os.path.join(root_dot_ssh, 'id_rsa')
AUTHED_KEYS = os.path.join(root_dot_ssh, 'authorized_keys')

localhost = ["0.0.0.0", "127.0.0.1", "localhost"]

def run_remote(ip, cmd):
    
    if ip not in localhost:
        cmd = "ssh %s -i %s root@%s '%s'" % (SSH_PARMS, SSH_KEY, ip, cmd)
    return commands.getstatusoutput(cmd)

def copy_remote(ip, local, remote='/tmp'):

    if ip not in localhost:
        cmd = 'scp -r %s -i %s %s root@%s:%s' % (SSH_PARMS,
                                                 SSH_KEY, local, ip, remote)
    else:
        if local == remote:
            return (0, "")
        cmd = 'cp -r %s %s' % (local, remote)

    return commands.getstatusoutput(cmd)

def setup_ssh_key():

    ssh_key="""-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEAxVN2bbhDyVHX4K0hvteoFraE6n7v4XzJHbtFtfiHepS9iNrS
yCoku46kByheNs42+uqU/+IEY59slqaZNkpIupczL3rpU6Yxk5q8N/vocTOltRGY
HEru7jJ+J3p09CqTtqTXDbD8m8BFGKVUu3JpIIj9Itmot1CfuatpJqZgkSRIh/VV
qmyvcOHsuh9j/4sQs3N8ZtVxThumHZIZljiMRfppEkPeEDtkwUCLvSdb2TM14szQ
/qaAUo6uB2GrYmjzMMhVfQjZJjxXfV+yWe+ETQovJPOSx/85UsmvojdJMXiLYQg2
7ubTTh9nQHf3QptdAFv+D4ic8ynYP51d/N14nwIBIwKCAQAtGmQ2VgDdjwzFo+p0
w5QictyNXte+guwkDYxG2biRDA4Qpwubd1jaab8XlDLKssq9AmszLFjGUFNVomwp
qpRH6AuzFMeeF1vJ93t6grjJauQMIUdW7I5iVK8e92swfsKtZ4Gcur1lbcamjDCf
36MAH0/Nc5RHKF8F3gln64PJZvnHs7/lLodmL2E092jc5iEhggqPr/yUmUhZjz0t
S+cgR1zPJiiIGmL5WZfzOre7zm1NZBHb5Q+TS2wfqEVEnAtoNXyFGM4rNUat1WRZ
mjMgcxEoguod9p8hjHYPeYD/vD7K0iIdS5yfsIV8XfHR1baWknXGlPMTTuTfYiFp
64eLAoGBAPhJ3dYzF8NAGEUfCp/77pnId6gpwREDRsSOnn5uEITQUObfyvrJopoo
FfPLICcWJZteDfRF+gnhA3a0PGjRgdicnoiUTBIpSQzMb9825heTl5Km0Shqbjd2
cxFxfA/Z+2FWZMfgaYCsrRYovkORapcP2n5dg10s6bZaqdZL0EgfAoGBAMt0ZRfs
qVvRul5TWlk9LaX4YuYIcm9AtkUHIO+B+/RIcUwoMfHzJVmWQp8p5lDtZnxSKQ6W
olJNIT5IpROEvGisP8wicED/6jV4ajwbBs0LezFs5aoaegmpkBmtB6T4pZdTTBnO
UoVmzgkXnrG7KccdwLxtOZhRxviTpjWBpr+BAoGAP9h63073e1mf10J/EzInaV9v
Od7Z382ke6+lGTI+wxD+3Egs4WcMjgpOyalCyDjlGVKzIY5WPQ35k41unpxF9d8h
c5PZC/v812fE/uI7KqJLjBxEaXp0HOPxtAc9KKXETDrJdTm0urAPQDZcz4vK86T9
q3chx4CT3m8VusMJrCUCgYARcGBvw9QAjlHNkh2v4KwkKzutUS5hTrCJkuWQ30F7
VqqgILPS6PSSpnq9L3okMZsR+GnrTr10xMhVy7ZgwjwI+NJEsn6mfFXnU3bR87Ag
NC8hflzUEOXjkjDsQgf4MpHZxU+qcMU+omlufl4PO+2jWlJZSzDSiqqnl6CIPlAf
CwKBgQDijr6WQ/m6+OYG3UfJC3hrHfiBYXbanYJXC/cfuLXYdrQ2z0epWhSJQaKU
FQaK0/Gc1ulcR2uC/dr4P8Lrghj90SBEHrZ3NwOFPZL7mlmkpWOjfpNk8Zrf0Ybt
t0Vm53Jlg5CzFbn9EZp3LN9D/GEwKOqPehB+P0qhz15H8j6VQQ==
-----END RSA PRIVATE KEY-----
"""
    
    def write_pubkey(pubkey):
        f = open(AUTHED_KEYS, 'a+')
        f.write('\n'+pubkey)
        f.flush()
        f.close()

    def write_privkey(privkey):
        f = open(SSH_KEY, 'w')
        f.write(privkey)
        f.flush()
        f.close()
        os.chmod(SSH_KEY, 0400)

    if os.path.exists(SSH_KEY):
        cmd = 'ssh-keygen -y -f %s' % SSH_KEY
        pubkey = commands.getoutput(cmd)
        if os.path.exists(AUTHED_KEYS):
            cmd = """grep "%s" %s >/dev/null 2>&1""" % (pubkey, AUTHED_KEYS)
            rc, o = commands.getstatusoutput(cmd)
            if rc != 0:
                write_pubkey(pubkey)
        else:
            write_pubkey(pubkey)
    else:
        write_privkey(ssh_key)
        cmd = 'ssh-keygen -y -f %s' % SSH_KEY
        pubkey = commands.getoutput(cmd)
        write_pubkey(pubkey)
