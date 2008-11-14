#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Guolian Yun <yunguol@cn.ibm.com>
#    Kaitlin Rupert <karupert@us.ibm.com>
#    Veerendra Chandrappa <vechandr@in.ibm.com>
#    Deepti B. Kalakeri<deeptik@linux.vnet.ibm.com>
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

# This tc is used to verify the results of the ElementConformsToProfile 
# association.  This test focuses on RegisteredProfile -> ManagedElement
# 
#   "CIM:DSP1042-SystemVirtualization-1.0.0" ,
#   "CIM:DSP1057-VirtualSystem-1.0.0a"
#   "CIM:DSP1059-GenericDeviceResourceVirtualization-1.0.0_d"
#   "CIM:DSP1059-GenericDeviceResourceVirtualization-1.0.0_n"
#   "CIM:DSP1059-GenericDeviceResourceVirtualization-1.0.0_p"
#   "CIM:DSP1045-MemoryResourceVirtualization-1.0.0"
#   "CIM:DSP1081-VirtualSystemMigration-0.8.1"
#
#                                                          Date : 04-12-2007

import sys
from VirtLib import utils, live
from XenKvmLib import assoc
from XenKvmLib.test_doms import destroy_and_undefine_all
from XenKvmLib.classes import get_typed_class
from XenKvmLib import vxml
from CimTest import Globals 
from XenKvmLib.common_util import print_field_error, check_sblim, get_host_info 
from CimTest.Globals import logger, CIM_ERROR_ENUMERATE
from XenKvmLib.const import do_main, get_provider_version 
from CimTest.ReturnCodes import PASS, FAIL, XFAIL, XFAIL_RC
from XenKvmLib.enumclass import EnumInstances

sup_types = ['Xen', 'XenFV', 'KVM', 'LXC']
test_dom = "domU"
bug_sblim = '00007'
libvirt_cim_ectp_changes = 686

def  init_vs_pool_values(server, virt):
    verify_ectp_list = {} 

    cn_names = ["ComputerSystem"]

    curr_cim_rev, changeset = get_provider_version(virt, server)
    if curr_cim_rev >= libvirt_cim_ectp_changes:
        cn_names2 = ["VirtualSystemMigrationService", "DiskPool", "NetworkPool",
                     "ProcessorPool", "MemoryPool"]
        cn_names.extend(cn_names2)

    status, host_name, host_ccn = get_host_info(server, virt)
    if status != PASS:
        logger.error("Unable to get host system instance objects")
        return FAIL, verify_ectp_list

    #FIXME - get_host_info() should be updated to return the host instance
    insts = EnumInstances(server, host_ccn, True)
    if len(insts) < 1: 
        logger.error("Expected 1 %s instance", host_ccn)
        return FAIL, verify_ectp_list

    verify_ectp_list[host_ccn] = insts

    for cn_base in cn_names:
        cn = get_typed_class(virt, cn_base)
        insts = EnumInstances(server, cn, True)
         
        if len(insts) < 1: 
            logger.error("Expected at least 1 %s instance", cn)
            return FAIL, verify_ectp_list

        verify_ectp_list[cn] = insts

    return PASS, verify_ectp_list

def verify_fields(assoc_val, managed_ele_values):
    try:
        cn = assoc_val.classname
        elements = managed_ele_values[cn]

        for ele in elements:
            if assoc_val.items() == ele.items():
                managed_ele_values[cn].remove(ele)
                return PASS, managed_ele_values

    except Exception, details:
        logger.error("verify_fields() exception: %s", details)
        return FAIL, managed_ele_values
      
    logger.error("%s not in expected list %s", assoc_val, elements)
    return FAIL, managed_ele_values

def get_proflist(server, reg_classname, virt):
    profiles_instid_list = []
    status = PASS
    try: 
        proflist = EnumInstances(server, reg_classname) 
        curr_cim_rev, changeset = get_provider_version(virt, server)
        if curr_cim_rev < libvirt_cim_ectp_changes:
            len_prof_list = 5
        else:
            len_prof_list = 7 
        if len(proflist) < len_prof_list:
            logger.error("'%s' returned '%d' '%s' objects, expected atleast %d",
                         reg_classname, len(proflist), 'Profile', len_prof_list)
            return FAIL, profiles_instid_list

    except Exception, detail:
        logger.error(CIM_ERROR_ENUMERATE, reg_classname)
        logger.error("Exception: %s", detail)
        status = FAIL

    if status != PASS:
        return status, profiles_instid_list

    unsupp_prof = []
    if curr_cim_rev < libvirt_cim_ectp_changes:
        unsupp_prof = ["CIM:DSP1059-GenericDeviceResourceVirtualization-1.0.0",
                       "CIM:DSP1045-MemoryResourceVirtualization-1.0.0",
                       "CIM:DSP1081-VirtualSystemMigration-0.8.1"]

    for profile in proflist:
        if profile.InstanceID not in unsupp_prof:
            profiles_instid_list.append(profile.InstanceID)

    return status, profiles_instid_list 

@do_main(sup_types)
def main():
    options = main.options
    server  = options.ip
    virt    = options.virt
  
    status = None 
    destroy_and_undefine_all(options.ip, options.virt)

    virt_xml = vxml.get_class(options.virt)
    cxml = virt_xml(test_dom)
    ret = cxml.cim_define(server)
    if not ret:
        logger.error('Unable to define domain %s' % test_dom)
        return FAIL

    ret = cxml.start(server)
    if not ret:
        cxml.undefine(server)
        logger.error('Unable to start domain %s' % test_dom)
        return FAIL

    prev_namespace = Globals.CIM_NS
    Globals.CIM_NS = 'root/interop'

    try:
        reg_classname = get_typed_class(virt, "RegisteredProfile")
        an = get_typed_class(virt,"ElementConformsToProfile")

        status, prof_inst_lst = get_proflist(server, reg_classname, virt)
        if status != PASS:
            raise Exception("Failed to get profile list") 

        status, verify_ectp_list = init_vs_pool_values(server, virt)
        if status != PASS:
            raise Exception("Failed to get instances needed for verification") 

        for prof_id in prof_inst_lst:
            logger.info("Verifying '%s' with '%s'", an, prof_id)
            assoc_info = assoc.Associators(server,
                                           an,
                                           reg_classname,
                                           InstanceID = prof_id)

            if len(assoc_info) < 1:
                ret_val, linux_cs = check_sblim(server, virt)
                if ret_val != PASS:
                    status = FAIL
                    raise Exception(" '%s' returned (%d) '%s' objects" % \
                                    (len(assoc_info), reg_classname))
                else:
                    status = XFAIL_RC(bug_sblim)
                    raise Exception("Known failure")

            for inst in assoc_info:
                status, verify_ectp_list = verify_fields(inst, verify_ectp_list)
                if status != PASS:
                    raise Exception("Failed to verify instance") 

        if status == PASS:
            for k, l in verify_ectp_list.iteritems():
                if len(l) != 0:
                    status = FAIL
                    raise Exception("%s items weren't returned: %s" % (k, l))

    except Exception, detail:
        logger.error("Exception: %s" % detail)
        status = FAIL

    Globals.CIM_NS = prev_namespace
    cxml.destroy(server)
    cxml.undefine(server)
    return status

if __name__ == "__main__":
    sys.exit(main())

