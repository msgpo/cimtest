#!/usr/bin/python
#
# Copyright 2008 IBM Corp.
#
# Authors:
#    Guolian Yun <yunguol@cn.ibm.com>
#    Kaitlin Rupert <karupert@us.ibm.com>
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

import sys
from pywbem import CIM_ERR_FAILED
from CimTest.Globals import logger
from XenKvmLib.const import do_main
from CimTest.ReturnCodes import PASS, FAIL
from XenKvmLib.vxml import get_class

sup_types = ['Xen', 'KVM', 'XenFV', 'LXC']
exp_rc = CIM_ERR_FAILED
exp_desc = 'Unable to parse embedded object'

@do_main(sup_types)
def main():
    options = main.options

    dname = 'test_domain'

    cxml = get_class(options.virt)(dname)
    cxml.set_sys_settings("wrong")

    ret = cxml.cim_define(options.ip)
    if ret:
        logger.error('DefineSystem should NOT return OK with a wrong ss input')
        status = FAIL

    try:
        if int(cxml.err_rc) != exp_rc:
            raise Exception("Got rc: %d, exp %d." % (int(cxml.err_rc), exp_rc))

        if cxml.err_desc.find(exp_desc) < 0:
            raise Exception("Got desc: '%s', exp '%s'" % (cxml.err_desc,
                            exp_desc))

        status = PASS

    except Exception, details:
        logger.error(details)
        status = FAIL

    cxml.undefine(options.ip)

    return status 

if __name__ == "__main__":
    sys.exit(main())
    
