#!/usr/bin/env python
 
import xmlrpclib
import os
import sys
import re
import commands
import subprocess
import base64
 
# GLOBAL VARS
SATELLITE_LOGIN = "LOGIN"
SATELLITE_PASSWORD = "PASSWORD"
GROUP_NAME = "GROUP_NAME"
 
 
def get_satellite ():
 
    satellite = ""
    file = '/etc/sysconfig/rhn/up2date'
    if os.path.isfile(file):
        infile = open(file, "r")
        try:
            for line in infile:
                if re.search("^serverURL=", line):
                    satellite = line.split("/",)[2]
        finally:
            infile.close()
    return satellite
 
 
def get_system_id ():
 
    file = "/etc/sysconfig/rhn/systemid"
    if os.path.isfile(file):
        infile = open(file, "r")
        try:
            for line in infile:
                if re.search("<value><string>ID-\d+<\/string><\/value>", line):
                    id = line.split("-",)[1]
                    id = id.split("<",)[0]
        finally:
            infile.close()
    return id
 
 
def create_satellite_group (key, client, group_name):
    
    description "FCOE-enabled systems."
    try:
        return client.systemgroup.create(key, group_name, description)
    except xmlrpclib.Fault as err:
        print "MESSAGE - Group already exists!"
        print "Fault code: %d" % error.faultCode
        print "Fault string: %s" % error.faultString
    
 
def add_server_to_group (key, client, server_id, group_name):
 
    try:
        return client.systemgroup.addOrRemoveSystems(key, group_name, server_id, True)
    except:
        print "Unexpected error 1:", sys.exc_info()[0]
        sys.exit(-1)
 
 
def fcoe_is_configured ():
 
    command = '/usr/sbin/fcoeadm -t'
 
    try:
        output = commands.getoutput(command)
        output = output.strip()
        output = output.split("\n")
    except:
        print "Unexpected error 2:", sys.exc_info()[0]
        sys.exit(-1)
 
    for line in output:
        # print line
        if line.startswith('No FCoE interfaces created.'):
            # FCOE not configured
            return 0
    # FCOE is configured
    return 1
 
 
def fcoe_installed (key, client, server_id):
 
    package_name = 'fcoe-utils'
    package_list = client.packages.search.name(key, package_name)
    print "MESSAGE - Found {0} versions of {1} in the repositories.".format(len(package_list), package_name)
    for package in package_list:
        p_version = package['version']
        p_release = package['release']
        
        try:
            installed = client.system.isNvreInstalled(key, server_id, package_name, p_version, p_release)
        except:
            print "Unexpected error 3:", sys.exc_info()[0]
            sys.exit(-1)
        
        if installed == 1:
            print "MESSAGE - {0}.{1}.{2} installed.".format(package_name, p_version, p_release)
            return 1
    return 0
 
 
def is_physical ():
 
    command = '/usr/sbin/dmidecode -s system-manufacturer'
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    p_status = p.wait()
 
    if "Dell" in output:
        # is physical
        return 1
    else:
        return 0
 
 
def main ():
 
    if not is_physical():
        print "Server is not Dell hardware, exiting ..."
        sys.exit(1)
 
    # SATELLITE CONNECTION
    SATELLITE_URL = "https://" + get_satellite() + "/rpc/api"
    client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
 
    try:
        key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)
    except xmlrpclib.Fault, error:
        # print "Fault code: %d" % error.faultCode
        print "Fault string: %s" % error.faultString
        sys.exit(-1)
 
    # MAIN CODE
    server_id = int(get_system_id())
    
    create_satellite_group(key, client, GROUP_NAME)
 
    if ( fcoe_installed(key, client, server_id) == 1 ) and ( fcoe_is_configured() == 1 ):
        print "MESSAGE - FCOE for SAN is configured, adding to group..."
 
        if add_server_to_group (key, client, server_id, GROUP_NAME) == 1:
            print "MESSAGE - {0} server added!".format(server_id)
            sys.exit(0)
        else:
            print "Problem?"
    else:
        print "MESSAGE - FCOE not configured, exiting..."
        sys.exit(1)
 
 
if __name__ == '__main__':
    # The 0th arg is the module filename
    main()
