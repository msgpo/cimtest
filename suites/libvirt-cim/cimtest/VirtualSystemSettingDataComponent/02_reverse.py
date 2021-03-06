#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Deepti B. Kalakeri <dkalaker@in.ibm.com>
#    Kaitlin Rupert <karupert@us.ibm.com>
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

# This test case is used to verify the Xen_VirtualSystemSettingDataComponent
# association.
#
# Ex: Command and the fields that are verified are given below.
# wbemcli ain -ac Xen_VirtualSystemSettingDataComponent \
# 'http://localhost:5988/root/virt:Xen_VirtualSystemSettingData.\
#  InstanceID="Xen:domgst"'
#
# Output:
# localhost:5988/root/virt:Xen_ProcResourceAllocationSettingData.\
# InstanceID="domgst/0" 
# localhost:5988/root/virt:Xen_NetResourceAllocationSettingData\
# .InstanceID="domgst/00:22:33:aa:bb:cc" 
# localhost:5988/root/virt:Xen_DiskResourceAllocationSettingData.\
# InstanceID="domgst/xvda"
# localhost:5988/root/virt:Xen_MemResourceAllocationSettingData.\
# InstanceID="domgst/mem"
# 
# 
# 
#                                               Date : 01-01-2008


import sys
from XenKvmLib import enumclass
from VirtLib import utils
from XenKvmLib import assoc
from XenKvmLib.test_doms import destroy_and_undefine_all 
from XenKvmLib import vxml
from XenKvmLib.classes import get_typed_class
from XenKvmLib.xm_virt_util import virsh_version, virsh_version_cmp
from CimTest.Globals import logger, CIM_ERROR_ASSOCIATORS
from XenKvmLib.const import do_main, get_provider_version
from CimTest.ReturnCodes import PASS, FAIL, XFAIL_RC

bug_libvirt = "00009"
sup_types = ['Xen', 'XenFV', 'KVM', 'LXC']

test_dom    = "VSSDC_dom"
test_vcpus  = 1
test_mem    = 128
test_mac    = "00:11:22:33:44:aa"

controller_rev = 1310

def assoc_values(ip, assoc_info, virt="Xen"):
    """
        The association info of 
        Xen_VirtualSystemSettingDataComponent is
        verified. 
    """
    status = PASS
    if virt == 'LXC':
        input_device = "mouse:usb"
    elif virt == 'Xen':
        input_device = "mouse:xen"
    else:
        input_device = "mouse:ps2"
        keybd_device = "keyboard:ps2"

    rasd_list = {
                 "proc_rasd" : '%s/%s' %(test_dom, "proc"), 
                 "net_rasd"  : '%s/%s' %(test_dom,test_mac),
                 "disk_rasd" : '%s/%s' %(test_dom, test_disk),
                 "mem_rasd"  : '%s/%s' %(test_dom, "mem"),
                 "input_rasd": '%s/%s' %(test_dom, input_device),
                 "grap_rasd" : '%s/%s' %(test_dom, "vnc")
                }

    curr_cim_rev, changeset = get_provider_version(virt, ip)
    if virt == 'KVM':
        # libvirt 1.2.2 adds a keyboard as an input option for KVM domains
        # so we need to handle that
        libvirt_version = virsh_version(ip, virt)
        if virsh_version_cmp(libvirt_version, "1.2.2") >= 0:
            rasd_list.update({"keybd_rasd":
                               '%s/%s' %(test_dom, keybd_device)})

        if curr_cim_rev >= controller_rev:
            # Add controllers too ... will need a cim/cimtest version check
            rasd_list.update({"pci_rasd":"%s/controller:pci:0" % test_dom})
            rasd_list.update({"usb_rasd":"%s/controller:usb:0" % test_dom})

    expect_rasds = len(rasd_list)

    try: 
        assoc_count = len(assoc_info)
        if assoc_count <= 0:
            logger.error("No RASD instances returned")
            return FAIL

        proc_cn = get_typed_class(virt, 'ProcResourceAllocationSettingData')
        net_cn = get_typed_class(virt, 'NetResourceAllocationSettingData')
        disk_cn = get_typed_class(virt, 'DiskResourceAllocationSettingData')
        mem_cn = get_typed_class(virt, 'MemResourceAllocationSettingData')
        input_cn = get_typed_class(virt, 'InputResourceAllocationSettingData')
        grap_cn = get_typed_class(virt, 'GraphicsResourceAllocationSettingData')
        ctl_cn = get_typed_class(virt, 'ControllerResourceAllocationSettingData')
    
        rasd_cns = [proc_cn, net_cn, disk_cn, mem_cn, input_cn, grap_cn]
        if curr_cim_rev >= controller_rev and virt == 'KVM':
            rasd_cns.append(ctl_cn)

        # Iterate over the rasds, looking for the expected InstanceID
        # listed in the rasd_list dictionary for the same classname in
        # the returned assoc_info list
        try:
            found_rasds = 0
            # Keep track of what worked
            found_list = {}
            assoc_list = {}
            for cn in rasd_cns:
                for rasd_key, rasd_value in rasd_list.iteritems():
                    for j, inst in enumerate(assoc_info):
                        if inst.classname == cn and \
                           inst['InstanceID'] == rasd_value:
                            #found_list.append((rasd_key, rasd_value))
                            found_list.update({rasd_key: rasd_value})
                            assoc_list.update({rasd_value: cn})
                            found_rasds += 1
        except Exception, detail:
            logger.error("Exception evaluating InstanceID: %s", detail)
            for (i,j) in found_list:
                logger.error("Found cn=%s exp_id=%s", i, j)
            return FAIL

        # Check for errors
        if expect_rasds != found_rasds:
            logger.error("RASD instances don't match expect=%d found=%d.",
                         expect_rasds, found_rasds)
            status = FAIL
            # What did we expect to find from the rasd_list, but did not
            # find in the found_list (key'd by rasd name)?
            # This means we're missing some device or perhaps the
            # InstanceID format changed...
            for k, v in rasd_list.iteritems():
                if k not in found_list:
                    logger.error("rasd_list ('%s','%s') not in found_list",
                                 k , v)
            # Thankfully the alternative is not possible - after all how
            # could there be something in the found list that isn't in the
            # rasd_list to start with...

        if assoc_count != found_rasds:
            status = FAIL
            logger.error("Assoc instances don't match expect=%d found=%d.",
                         assoc_count, found_rasds)
            # What's in the assoc_info that's not in found assoc_list (key'd
            # by InstanceID)
            # Meaning there's a new device type that we haven't accounted for
            for j, inst in enumerate(assoc_info):
                if inst['InstanceID'] not in assoc_list:
                    logger.error("Did not find association id=%s in assoc_list",
                                 inst['InstanceID'])
            # Thankfully the alternative is not possible - after all how
            # could there be something in the found list that isn't in the
            # assoc_info list to start with...


    except  Exception, detail :
        logger.error("Exception in assoc_values function: %s", detail)
        status = FAIL

    return status

@do_main(sup_types)
def main():
    options = main.options
    status = PASS

    destroy_and_undefine_all(options.ip)

    global test_disk
    if options.virt == "Xen":
        test_disk = "xvdb"
    elif options.virt == "LXC":
        test_disk = "/tmp"
    else:
        test_disk = "vdb"

    virt_xml = vxml.get_class(options.virt)
    if options.virt == 'LXC':
        cxml = virt_xml(test_dom)
    else:
        cxml = virt_xml(test_dom, vcpus = test_vcpus, 
                        mac = test_mac, disk = test_disk)

    ret = cxml.cim_define(options.ip)
    if not ret:
        logger.error("Failed to define the dom: %s", test_dom)
        return FAIL

    ret = cxml.cim_start(options.ip)
    if ret != PASS:
        cxml.undefine(options.ip)
        logger.error("Failed to start the dom: %s", test_dom)
        return ret

    if options.virt == "XenFV":
        instIdval = "Xen:%s" % test_dom
    else:
        instIdval = "%s:%s" % (options.virt, test_dom)
    
    try:
        an = get_typed_class(options.virt, 'VirtualSystemSettingDataComponent')
        cn = get_typed_class(options.virt, 'VirtualSystemSettingData')
        assoc_info = assoc.AssociatorNames(options.ip, an, cn,
                                           InstanceID = instIdval)
        status = assoc_values(options.ip, assoc_info, options.virt)

    except  Exception, detail :
        logger.error(CIM_ERROR_ASSOCIATORS, an)
        logger.error("Exception : %s", detail)
        status = FAIL

    cxml.destroy(options.ip)
    cxml.undefine(options.ip)
    return status

if __name__ == "__main__":
    sys.exit(main())
