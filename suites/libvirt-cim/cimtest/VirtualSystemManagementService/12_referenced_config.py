#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
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
# Purpose:
#   Verify DefineSystem() properly uses the settings of the referenced passed in
#   for the ReferenceConfiguration parameter.
#
# Steps:
#  1) Define and start a guest
#  2) Get the reference of the guest
#  3) Define a second guest using the reference of the first guest
#  4) Verify the settings of the second guest


import sys
from XenKvmLib.common_util import get_cs_instance
from CimTest.Globals import logger
from XenKvmLib.const import do_main
from CimTest.ReturnCodes import FAIL, PASS
from XenKvmLib.classes import get_typed_class, inst_to_mof
from XenKvmLib.assoc import AssociatorNames
from XenKvmLib.test_xml import dumpxml
from XenKvmLib.vxml import get_class
from XenKvmLib.rasd import get_default_rasds

sup_types = ['Xen', 'XenFV', 'KVM']
test_dom = 'rstest_domain'
test_dom2 = 'rstest_domain2'

mac = "aa:aa:aa:00:00:00"

def setup_first_guest(ip, virt, cxml):
    ret = cxml.cim_define(ip)
    if not ret:
        logger.error("Unable to define %s using DefineSystem()" % test_dom)
        return FAIL, None

    status = cxml.cim_start(ip)
    if status != PASS:
        logger.error("Unable to start %s" % test_dom)
        return FAIL, "define"

    return PASS, "start"

def get_vssd_ref(ip, virt):
    rc, cs = get_cs_instance(test_dom, ip, virt)
    if rc != 0:
        return None

    an = get_typed_class(virt, 'SettingsDefineState')
    vssd = AssociatorNames(ip, an, cs.CreationClassName, Name=cs.Name, 
                           CreationClassName=cs.CreationClassName)

    if len(vssd) != 1:
        logger.error("Returned %i vssd insts for '%s'", len(vssd), test_dom)
        return None

    return vssd[0]

def setup_second_guest(ip, virt, cxml2, ref):
    nrasd_cn = get_typed_class(virt, "NetResourceAllocationSettingData")

    rasds = get_default_rasds(ip, virt)

    rasd_list = {}

    for rasd in rasds:
        if rasd.classname == nrasd_cn:
            rasd['Address'] = mac
            rasd['NetworkType'] = "network" 
            rasd_list[nrasd_cn] = inst_to_mof(rasd)
        else:
            rasd_list[rasd.classname] = None

    if rasd_list[nrasd_cn] is None:
        logger.error("Unable to get template NetRASD")
        return FAIL

    cxml2.set_res_settings(rasd_list)

    ret = cxml2.cim_define(ip, ref_conf=ref)
    if not ret:
        logger.error("Unable to define %s using DefineSystem()" % test_dom2)
        return FAIL, None

    return PASS, "define"

def get_dom_macs(server, dom, virt):
    mac_list = []

    myxml = dumpxml(dom, server, virt=virt)

    lines = myxml.splitlines()
    for l in lines:
        if l.find("mac address=") != -1:
            mac = l.split('=')[1]
            mac = mac.lstrip('\'')
            mac = mac.rstrip('\'/>')
            mac_list.append(mac)
   
    return mac_list 

@do_main(sup_types)
def main():
    options = main.options
    virt = options.virt
    ip = options.ip

    cxml = get_class(virt)(test_dom)
    cxml2 = get_class(virt)(test_dom2)

    guest1_setup = None 
    guest2_setup = None 

    try:
        status, guest1_setup = setup_first_guest(ip, virt, cxml)
        if status != PASS:
            raise Exception("Unable to start %s" % test_dom)

        ref = get_vssd_ref(ip, virt)
        if ref is None:
            raise Exception("Unable to get %s reference" % test_dom)

        status, guest2_setup = setup_second_guest(ip, virt, cxml2, ref)
        if status != PASS:
            raise Exception("Unable to define %s" % test_dom2)

        dom1_mac_list = get_dom_macs(ip, test_dom, virt)
        if len(dom1_mac_list) != 1:
            raise Exception("%s has %d macs, expected 1" % (test_dom, 
                            len(dom1_mac_list)))

        dom2_mac_list = get_dom_macs(ip, test_dom2, virt)
        if len(dom2_mac_list) != 2:
            raise Exception("%s has %d macs, expected 2" % (test_dom2, 
                            len(dom2_mac_list)))

        for item in dom2_mac_list:
            if item != mac and item != dom1_mac_list[0]:
                raise Exception("%s has unexpected mac value, exp: %s %s" % \
                                (item, mac, dom1_mac_list[0]))

        status = PASS
      
    except Exception, details:
        logger.error(details)
        status = FAIL

    if guest1_setup == "start": 
        cxml.cim_destroy(ip)

    if guest1_setup == "define": 
        cxml.undefine(ip)

    if guest2_setup == "define": 
        cxml2.undefine(ip)

    return status 

if __name__ == "__main__":
    sys.exit(main())
    
