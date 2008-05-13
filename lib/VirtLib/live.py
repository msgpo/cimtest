#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Dan Smith <danms@us.ibm.com>
#    Deepti B. Kalakeri <dkalaker@in.ibm.com>
#    Kaitlin Rupert <karupert@us.ibm.com>
#    Veerendra Chandrappa <vechandr@in.ibm.com>
#    Zhengang Li <lizg@cn.ibm.com>
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
import os
import utils
import socket

def processors_count(ip, vs_name):
    """Returns the number of processors of the specified VS
    """

    guest_cmd = "grep '^$' /proc/cpuinfo | wc -l"

    rc, out = utils.run_remote_guest(ip, vs_name, guest_cmd)
    if rc != 0:
        return -1

    try:
        cpus = int(out)
        return cpus
    except ValueError:
        return -1

def memory_count(ip, vs_name):
    """Returns the memory size (in Bytes) of the specified VS.
    """

    guest_cmd = "grep MemTotal /proc/meminfo"

    rc, out = utils.run_remote_guest(ip, vs_name, guest_cmd)
    if rc != 0:
        return -1

    try:
        mem = int( out.split()[1] )
        return mem * 1024
    except (IndexError, ValueError):
        return -1

def network_macs(ip, vs_name):
    """Returns a list of MAC address of the specified VS.
    """

    guest_cmd = "ifconfig -a | grep eth"

    rc, out = utils.run_remote_guest(ip, vs_name, guest_cmd)
    if rc != 0:
        return []

    ret = []
    lines = out.splitlines()
    for l in lines:
        try:
            mac = l.split()[-1]
            ret.append( mac )
        except IndexError:
            pass

    return ret 

def available_bridges(ip):
    """Return a list of the available bridges in the running dom0.
    """

    cmd = "brctl show | grep -v 'bridge name' | awk '/^[^\t]/ { print \$1 }'"

    rc, out = utils.run_remote(ip, cmd)
    if rc != 0:
        return []

    return out.splitlines()

def exclude_vir_bridge(ip):
    cmd = "brctl show | grep -v 'bridge name' | grep -v vir | \
                                  grep -v vif | awk '/^[^\t]/ { print \$1 }'"
    rc, out = utils.run_remote(ip, cmd)
    if rc != 0:
        return []

    return out.splitlines()

def available_virt_bridge(ip):
    """Return a list of the available virtual bridges in the running dom0.
    """

    cmd = "brctl show | grep -v 'bridge name' | grep -v peth | awk '/^[^\t]/ { print \$1 }'"

    rc, out = utils.run_remote(ip, cmd)
    if rc != 0:
        return []

    return out.splitlines()

def xm_domname(ip, domid):
    
    cmd = "xm domname %s" % domid
 
    rc, out = utils.run_remote(ip, cmd)
    if rc != 0:
        return None

    return out
    
def list_guests_on_bridge(ip, bridge):
    """Returns a list of domU names that have vifs in the 
    specified bridge.
    """

    cmd = "brctl show %s | grep 'vif' | grep -v vif0.*" % bridge

    rc, out = utils.run_remote(ip, cmd)
    if rc != 0:
        return []

    ret = []
    lines = out.splitlines()
    for l in lines:
        vif = l.split()[-1]
        domid = vif.replace('vif', '').split('.')[0]
        domname = xm_domname(ip, domid)
        if domname != None:
            ret.append(domname)

    return ret

def disk_list(ip, vs_name):
    """Returns the list of disk of the specified VS
    """

    guest_cmd = "cat /proc/partitions | awk '/^ /{ print $4 } ' "
    rc, out = utils.run_remote_guest(ip, vs_name, guest_cmd)

    if rc != 0:
        return None

    return out

def create_disk_file(ip, size, diskfile) :
    """Creates a disk file 1MB block-size ,and if succsess returns disk created.
    """
    cmd =  "dd if=/dev/zero of=" + diskfile + " bs=1M count=" +  str(size)

    rc, out = utils.run_remote(ip, cmd)

    if rc != 0:
        return None
    return rc


def max_free_mem(server):
    """Function to get max free mem on dom0.

    Returns an int containing the value in MB.
    """

    xm_ret, mfm = utils.run_remote(server,
                    "xm info | awk -F ': ' '/max_free_memory/ {print \$2}'")
    if xm_ret != 0:
        return None

    return int(mfm)

def domain_list(server, virt="Xen"):
    """Function to list all domains"""
    if virt == "XenFV":
       virt = "Xen"

    cmd = "virsh -c %s list --all | sed -e '1,2 d' -e '$ d'" % \
                utils.virt2uri(virt)
    ret, out = utils.run_remote(server, cmd)

    if ret != 0:
        return None
    names = []
    lines = out.split("\n")
    for line in lines:
        dinfo = line.split()
        if len(dinfo) > 1:
            names.append(dinfo[1])

    return names

def active_domain_list(server, virt="Xen"):
    """Function to list all active domains"""
    if virt == "XenFV":
        virt = "Xen"
    
    cmd = "virsh -c %s list | sed -e '1,2 d' -e '$ d'" % \
                utils.virt2uri(virt)
    ret, out = utils.run_remote(server, cmd)
    
    if ret != 0:
        return None
    names = []
    lines = out.split("\n")
    for line in lines:
        dinfo = line.split()
        if len(dinfo) > 1:
            names.append(dinfo[1])

    return names

def bootloader(server, gtype = 0):
    """
       Function to find the bootloader to be used.
       It uses the following steps to determine the bootloader.
       1) The function checks if the machine is full virt or para virt.
       2) Checks if a Full virt guest option is set
          NOTE : gtype = 1 for FV and gtype = 0 for PV 
          i) If yes, then verifies if the machine has the support to 
             create the full virt guest. If both options are true then
             bootloader is set to 'hvmloader'
          ii) Otherwise, a paravirt guest creation is requested.
              a) Verfies the OS on which it is running is Red hat/Fedora/SLES.
              b) sets the bootloader to pygrub for Red hat/Fedora
                 or domUloader.py for SLES.
       3) returns the bootloader.
    """
    if fv_cap(server) and gtype == 1:
        bootloader = "/usr/lib/xen/boot/hvmloader"
    else:
        cmd = "cat /etc/issue | grep -v ^$ | egrep 'Red Hat|Fedora'"
        ret, out = utils.run_remote(server,cmd)
        if ret != 0:
        # For SLES 
            bootloader = "/usr/lib/xen/boot/domUloader.py"
        else:
        # For Red Hat or Fedora
            bootloader = "/usr/bin/pygrub"
    return bootloader

def fv_cap(server):
    cmd = "egrep flags /proc/cpuinfo | uniq | egrep 'vmx|svm'"
    ret, out = utils.run_remote(server, cmd)
    return ret == 0

def hostname(server):
    """To return the hostname of the cimserver"""

    ret, out = utils.run_remote(server, "hostname")

    if ret != 0:
        return None

    return out

def full_hostname(server):
    """To return the fully qualifiec domain name(FQDN) of the system"""

    return socket.gethostbyaddr(socket.gethostname())[0]


def net_list(server, virt="Xen"):
    """Function to list active network"""
    names = []
    cmd = "virsh -c %s net-list | sed -e '1,2 d' -e '$ d'" % \
                utils.virt2uri(virt)
    ret, out = utils.run_remote(server, cmd)
    
    if ret != 0:
        return names 
    lines = out.split("\n")
    for line in lines:
        virt_network = line.split()
        if len(virt_network) >= 1 and virt_network[1] == "active":
            names.append(virt_network[0])

    return names

def get_bridge_from_network_xml(network, server, virt="Xen"):
    """Function returns bridge name for a given virtual network"""

    cmd = "virsh -c %s net-dumpxml %s | awk '/bridge name/ { print $2 }'" % \
                (utils.virt2uri(virt), network)
    ret, out = utils.run_remote(server, cmd)
    
    if ret != 0:
        return None 
    bridge = out.split("'")
    if len(bridge) > 1:
        return bridge[1] 

def network_by_bridge(bridge, server, virt="Xen"):
    """Function returns virtual network for a given bridge"""

    networks = net_list(server, virt)
    if len(networks) == 0:
        return None 

    for network in networks:
        if bridge == get_bridge_from_network_xml(network, server, virt):
            return network

    return None

def virsh_version(server, virt="KVM"):
    cmd = "virsh -c %s -v " % utils.virt2uri(virt)
    ret, out = utils.run_remote(server, cmd)
    if ret != 0:
        return None
    return out

def diskpool_list(server, virt="KVM"):
    """Function to list active DiskPool list"""
    names = []
    cmd = "virsh -c %s pool-list | sed -e '1,2 d' -e '$ d'" % \
           utils.virt2uri(virt)
    ret, out = utils.run_remote(server, cmd)
    
    if ret != 0:
        return names 

    lines = out.split("\n")
    for line in lines:
        disk_pool = line.split()
        if len(disk_pool) >= 1 and disk_pool[1] == "active":
            names.append(disk_pool[0])

    return names
