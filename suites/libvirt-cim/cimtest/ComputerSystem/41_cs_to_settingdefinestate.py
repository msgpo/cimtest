#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Deepti B. Kalakeri <dkalaker@in.ibm.com>
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

#
# This is a cross-provider testcase to 
# Verify starting ComputerSystem instance is the same as returned by the 
# SettingsDefineState.
#
# It traverses the following path: 
# {ComputerSystem} (select the guest domain) --> [SystemDevice](from output select 
# guest domain instances of Device, from the guest domain instances, 
# select one Device instance) --> [SettingsDefineState] (from output, select a RASD
# instance - should only be 1) --> [VSSDComponent] (from output, select a VSSD instance 
# - should only be 1) --> [SettingsDefineState] (Verify the ComputerSystem instance is 
# the one we started with)
#
# Steps:
# ------
# 1) Create a guest domain.  
# 2) Enumerate ComputerSystem and Select the guest domain from the output 
#    and and verify the EnabledState is 2.
# 3) Create info list for the guest domain to be used later for comparison.
# 4) Get the various devices allocated to the domain by using the SystemDevice
#    association and giving the ComputerSystem output from the previous enumeration 
#    as inputs to the association. 
# 5) For each of the Devices get the association on SettingsDefineState, we should 
#    get only one record as output.
# 6) Verify the Disk, Memory, Network, Processor RASD values.
# 7) Call VSSDComponent association for each of the RASD types, we should
#    get only one VSSD record as output.  
# 8) Verify the VSSD output for every VSSDComponent association with the RASD types.
# 9) Using the VSSD output query the SettingsDefineState association, again we should
#    get only one computersystem record as output.
# 10)Verify the computersystem values with the computersystem info that was created from 
#    the enumeration in the beginning.
# 11) Destroy the domain.
#                                                                  Date : 05.02.2008

import sys
from VirtLib import utils
from XenKvmLib.vxml import get_class
from XenKvmLib.classes import get_typed_class
from XenKvmLib.test_doms import destroy_and_undefine_all
from XenKvmLib.assoc import Associators, AssociatorNames
from CimTest.Globals import logger, CIM_ERROR_ASSOCIATORNAMES, \
CIM_ERROR_ASSOCIATORS
from XenKvmLib.const import do_main
from CimTest.ReturnCodes import PASS, FAIL
from XenKvmLib import rasd
from XenKvmLib.rasd import verify_procrasd_values, verify_netrasd_values, \
verify_diskrasd_values, verify_memrasd_values, rasd_init_list
from XenKvmLib.common_util import poll_for_state_change
from XenKvmLib.classes import get_typed_class

sup_types = ['Xen', 'XenFV', 'KVM']

test_dom    = "CrossClass_GuestDom"
test_vcpus  = 1
test_mem    = 128
test_mac    = "00:11:22:33:44:aa"

def vssd_init_list(virt):
    """
        Creating the lists that will be used for comparisons.
    """
    if virt == 'XenFV':
        virt = 'Xen'

    vssd_values = { 
                      'Caption'                 : "Virtual System", 
                      'InstanceID'              : '%s:%s' % (virt, test_dom),
                      'ElementName'             : test_dom, 
                      'VirtualSystemIdentifier' : test_dom,
                      'VirtualSystemType'       : virt, 
                      'Classname'               : get_typed_class(virt, 
                                                  "VirtualSystemSettingData")
                  } 

    return vssd_values

def cs_init_list(cs_dom):
    """
        Creating the lists that will be used for comparisons.
    """
    cs_values =  {
                       'Caption'              : cs_dom.Caption,        
                       'EnabledState'         : cs_dom.EnabledState,   
                       'RequestedState'       : cs_dom.RequestedState, 
                       'CreationClassName'    : cs_dom.CreationClassName, 
                       'Name'                 : cs_dom.Name
                 }
    return cs_values 

def setup_env(server, virt, test_disk):
    vsxml_info = None
    status = PASS
    destroy_and_undefine_all(server)
    virt_xml =  get_class(virt)

    vsxml_info = virt_xml(test_dom, mem = test_mem,
                          vcpus=test_vcpus,
                          mac = test_mac,
                          disk = test_disk)

    ret = vsxml_info.create(server)
    if not ret:
        logger.error("Failed to create the dom: %s", test_dom)
        status = FAIL

    return status, vsxml_info


def print_err(err, detail, cn):
    logger.error(err % cn)
    logger.error("Exception: %s", detail)

def vssd_sds_err( an, fieldname, ret_val, exp_val):
    error    = "Mismatching %s Values in %s association"
    details  = "Returned %s instead of %s"
    err      = error % (fieldname, an)
    detail   = details % (ret_val, exp_val)
    logger.error(err)
    logger.error(detail)

def get_associatornames_info(server, virt, vsxml, cn, an, qcn, name):
    status = PASS
    assoc_info = []
    try:
        assoc_info = AssociatorNames(server,
                                         an,
                                         cn,
                       CreationClassName=cn,
                                Name = name)
        if len(assoc_info) < 1:
            logger.error("%s returned %i %s objects" % (an, len(assoc_info), qcn))
            status = FAIL
    except Exception, detail:
        print_err(CIM_ERROR_ASSOCIATORNAMES, detail, cn)
        status = FAIL

    if status != PASS:
        vsxml.destroy(server)

    return status, assoc_info

def get_associators_info(server, virt, vsxml, cn, an, qcn, instid):
    status = PASS
    assoc_info = []
    try:
        assoc_info = Associators(server,
                                     an,
                                     cn,
                    InstanceID = instid)
        if len(assoc_info) < 1:
            logger.error("%s returned %i %s objects" % 
                         (an, len(assoc_info), qcn))
            status = FAIL

    except Exception, detail:
        print_err(CIM_ERROR_ASSOCIATORS, detail, cn)
        status = FAIL

    if status != PASS:
        vsxml.destroy(server)

    return status, assoc_info

def check_len(an, assoc_list_info, qcn, exp_len):
    if len(assoc_list_info) != exp_len:
        logger.error("%s returned %i %s objects", an, 
                                                  len(assoc_list_info), qcn)
        return FAIL 
    return PASS 

def get_SDS_verify_RASD_build_vssdc_input(server, virt, vsxml, 
                                          test_disk, sd_assoc_info):
    status = PASS
    in_setting_define_state = {} 
    in_vssdc = {}
    prasd = get_typed_class(virt, 'ProcResourceAllocationSettingData')
    mrasd = get_typed_class(virt, 'MemResourceAllocationSettingData')
    nrasd = get_typed_class(virt, 'NetResourceAllocationSettingData')
    drasd = get_typed_class(virt, 'DiskResourceAllocationSettingData') 

    try:

        # Building the input for SettingsDefineState association.
        for i in range(len(sd_assoc_info)):
            if sd_assoc_info[i]['SystemName'] == test_dom:
                classname_keyvalue = sd_assoc_info[i]['CreationClassName']
                deviceid =  sd_assoc_info[i]['DeviceID']
                in_setting_define_state[classname_keyvalue] = deviceid

        # Expect the SystemDevice to return 4 logical device records.
        # one each for memory, network, disk and processor and hence 4.
        # and hence expect the in_setting_define_state to contain just 4 entries.
        an  = get_typed_class(virt, "SystemDevice")
        qcn = "Logical Devices"
        exp_len = 4
        if check_len(an, in_setting_define_state, qcn, exp_len) != PASS:
            return FAIL, in_setting_define_state

        # Get the rasd values that will be used to compare with the SettingsDefineState
        # output.
        status, rasd_values, in_list = rasd_init_list(vsxml, virt, test_disk, 
                                                      test_dom, test_mac, 
                                                      test_mem)
        if status != PASS:
            return status, rasd_values
        
        sccn =  get_typed_class(virt,"ComputerSystem")
        an   =  get_typed_class(virt,"SettingsDefineState")
        for cn, devid in sorted(in_setting_define_state.items()):
            assoc_info = Associators(server,
                                     an, 
                                     cn,
                                     DeviceID = devid,
                                     CreationClassName = cn,
                                     SystemName = test_dom,
                                     SystemCreationClassName = sccn)

            # we expect only one RASD record to be returned for each device that is used to 
            # query with the SettingsDefineState association.
            if len(assoc_info) != 1:
                logger.error("%s returned %i %s objects" % (an, len(assoc_info), cn))
                status = FAIL
                break
            index = (len(assoc_info) - 1)
            rasd  = rasd_values[cn]
            CCName = assoc_info[index].classname
            if  CCName == prasd:
                status = verify_procrasd_values(assoc_info[index], rasd)
            elif CCName == nrasd:
                status  = verify_netrasd_values(assoc_info[index], rasd)
            elif CCName == drasd:
                status = verify_diskrasd_values(assoc_info[index], rasd)
            elif CCName == mrasd:
                status  = verify_memrasd_values(assoc_info[index], rasd)
            else:
                status = FAIL
            if status != PASS:
                logger.error("Mistmatching RASD values" )
                break
            vs_name = assoc_info[index]['InstanceID']
            if vs_name.find(test_dom) >= 0:
                instid =  assoc_info[index]['InstanceID']
                in_vssdc[CCName] = instid 
    except Exception, detail:
        print_err(CIM_ERROR_ASSOCIATORS, detail, an)
        status = FAIL
    return status, in_vssdc


def verify_fields(an, field_name, vssd_cs_assoc_info, vssd_cs_values):
    if vssd_cs_assoc_info[field_name] != vssd_cs_values[field_name]:
        vssd_sds_err(an, field_name, vssd_cs_assoc_info[field_name], \
                                           vssd_cs_values[field_name])
        return FAIL 
    return PASS 


def verify_VSSD_values(assoc_info, vssd_values, an, qcn):
    # We expect that VirtualSystemSettingDataComponent returns only one 
    # VirtualSystemSettingData object when queried with disk, processor,
    # network and memory rasd's and all of them return the same output.
    exp_len = 1

    if check_len(an, assoc_info, qcn, exp_len) != PASS:
        return FAIL
    vssd_assoc = assoc_info[0]
    if verify_fields(an, 'Caption', vssd_assoc, vssd_values) != PASS:
        return FAIL
    if verify_fields(an, 'InstanceID', vssd_assoc, vssd_values) != PASS:
        return FAIL
    if verify_fields(an, 'ElementName', vssd_assoc, vssd_values) != PASS:
        return FAIL
    if verify_fields(an, 'VirtualSystemIdentifier', vssd_assoc, vssd_values) != PASS:
        return FAIL
    if verify_fields(an, 'VirtualSystemType', vssd_assoc, vssd_values) != PASS:
        return FAIL
    if vssd_assoc.classname != vssd_values['Classname']:
        vssd_sds_err(an, 'Classname', vssd_assoc.classname, 
                     vssd_values['Classname'])
        return FAIL
    return PASS

def verify_CS_values(assoc_info, cs_values, an, qcn):
    exp_len = 1

    if check_len(an, assoc_info, qcn, exp_len) != PASS:
        return FAIL
    cs_assoc = assoc_info[0]
    if verify_fields(an, 'Caption', cs_assoc, cs_values) != PASS:
        return FAIL
    if verify_fields(an, 'EnabledState', cs_assoc, cs_values) != PASS:
        return FAIL
    if verify_fields(an, 'RequestedState', cs_assoc, cs_values) != PASS:
        return FAIL
    if verify_fields(an, 'CreationClassName', cs_assoc, cs_values) != PASS:
        return FAIL
    if verify_fields(an, 'Name', cs_assoc, cs_values) != PASS:
        return FAIL
    return PASS 

@do_main(sup_types)
def main():
    server = main.options.ip
    virt   = main.options.virt
    if virt == 'Xen':
        test_disk = "xvda"
    else:
        test_disk = "hda"

    status, vsxml = setup_env(server, virt, test_disk)
    if status != PASS:
        return status

    status, cs_dom  = poll_for_state_change(server, virt, test_dom, 2, 
                                            timeout=10)
    if status != PASS and cs_dom.RequestedState != 0:
        vsxml.destroy(server)
        return FAIL

    # Creating the cs info list which will be used later for comparison.
    cs_values = cs_init_list(cs_dom)
    
    cn        = cs_dom.CreationClassName
    an        = get_typed_class(virt, 'SystemDevice')
    qcn       = 'Logical Devices'
    name      = test_dom
    status, sd_assoc_info = get_associatornames_info(server, virt, vsxml, 
                                                     cn, an, qcn, name)
    if status != PASS or len(sd_assoc_info) == 0:
        return status

    status, in_vssdc_list = get_SDS_verify_RASD_build_vssdc_input(server, virt,
                                                                  vsxml, test_disk,
                                                                  sd_assoc_info)
    if status != PASS or len(in_vssdc_list) == 0 :
        vsxml.destroy(server)
        return status

    # Verifying that the in_vssdc_list contains 4 entries one each for mem rasd,
    # network rasd, processor rasd and disk rasd.
    exp_len = 4
    if check_len(an, in_vssdc_list, qcn, exp_len) != PASS:
        vsxml.destroy(server)
        return FAIL 

    # Get the vssd values which will be used for verifying the 
    # VirtualSystemSettingData output from the 
    # VirtualSystemSettingDataComponent results.
    vssd_values = vssd_init_list(virt)
    an  = get_typed_class(virt, 'VirtualSystemSettingDataComponent')
    qcn = get_typed_class(virt, 'VirtualSystemSettingData')
    for cn, instid in sorted((in_vssdc_list.items())):
        status, vssd_assoc_info = get_associators_info(server, virt, vsxml, cn, 
                                                       an, qcn, instid)
        if status != PASS or len(vssd_assoc_info) == 0:
            break 
        status = verify_VSSD_values(vssd_assoc_info, vssd_values, an, qcn)    
        if status != PASS:
            break
    if status != PASS:
        vsxml.destroy(server)
        return status

    # Since the VirtualSystemSettingDataComponent returns similar 
    # output when queried with every RASD, we are taking the output of 
    # the last associtaion query as inputs for 
    # querying SettingsDefineState.
    cn     = vssd_assoc_info[0].classname
    an     = get_typed_class(virt, 'SettingsDefineState')
    qcn    = get_typed_class(virt, 'ComputerSystem')
    instid = vssd_assoc_info[0]['InstanceID']
    status, cs_assoc_info = get_associators_info(server, virt, vsxml, cn, 
                                                 an, qcn, instid)
    if status != PASS or len(cs_assoc_info) == 0:
        return status

    # verify the results of SettingsDefineState with the cs_values list that was 
    # built using the output of the enumeration on ComputerSystem.
    status = verify_CS_values(cs_assoc_info, cs_values, an, qcn)
    vsxml.destroy(server)
    return status
if __name__ == "__main__":
    sys.exit(main())
