#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Dan Smith <danms@us.ibm.com>
#    Guolian Yun <yunguol@cn.ibm.com>
#    Zhengang Li <lizg@cn.ibm.com>
#    Deepti B. Kalakeri <dkalaker@in.ibm.com>
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

import sys
from XenKvmLib import assoc
from XenKvmLib import enumclass
from XenKvmLib.const import default_network_name
from CimTest import Globals
from CimTest.Globals import logger
from CimTest.ReturnCodes import PASS, FAIL
from XenKvmLib.const import do_main, default_pool_name
from XenKvmLib.classes import get_typed_class

sup_types = ['Xen', 'KVM', 'XenFV', 'LXC']
@do_main(sup_types)
def main():
    options = main.options
    status = FAIL

    keys = ['Name', 'CreationClassName']
    try:
        host_sys = enumclass.enumerate(options.ip, 'HostSystem', keys, options.virt)[0]
    except Exception:
        host_cn = get_typed_class(options.virt, "HostSystem")
        logger.error(Globals.CIM_ERROR_ENUMERATE % host_cn)
        return FAIL
    try:
        assoc_cn = get_typed_class(options.virt, "HostedResourcePool")
        pool = assoc.AssociatorNames(options.ip,
                                     assoc_cn,
                                     host_sys.CreationClassName,
                                     Name = host_sys.Name,
                                     CreationClassName = host_sys.CreationClassName,
                                     virt = options.virt)
    except Exception, details:
        logger.error(Globals.CIM_ERROR_ASSOCIATORNAMES % assoc_cn)
        logger.error("Exception:",  details)
        return FAIL
   
    if pool == None:
        logger.error("System association failed")
        return FAIL
    elif len(pool) == 0:
        logger.error("No pool returned")
        return FAIL
    
    for items in pool:
        cname = items.classname
        if cname.find("MemoryPool") >=0 and items['InstanceID'] == "MemoryPool/0":
            status = PASS
        if cname.find("ProcessorPool") >=0 and items['InstanceID'] == "ProcessorPool/0":
            status = PASS
        if cname.find("NetworkPool") >=0 and \
           items['InstanceID'] == "NetworkPool/%s" %default_network_name:
            status = PASS
        if cname.find("DiskPool") >=0 and \
           items['InstanceID'] == "DiskPool/%s" % default_pool_name:
            status = PASS
        

    return status  
if __name__ == "__main__":
    sys.exit(main())
