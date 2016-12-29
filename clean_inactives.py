#!/usr/bin/env python

import argparse
import base64
import getpass
import logging
import sys
import xmlrpclib
import time


# GLOBAL VARS
SATELLITE_URL = "URL"
SATELLITE_LOGIN = "LOGIN"
SATELLITE_PASSWORD = "PASSWD"
DECOMM_GROUP = "GROUP_NAME"
LOG_FILE = "PATH"
DAYS = 30


def list_inactive(key, client, DAYS):
    """Gets a list of all inactive systems in Satellite.
    
    Args:
        key: Satellite session key.
        client: RPC connection information.
        DAYS: number of days of inactivity. By default the number of days is 30.
    
    Returns: A list of inactive servers, containing ID, name and last-checkin. Returns 1 if it fails
    """
    
    try:
        inactive_list = client.system.listInactiveSystems(key, DAYS)
    except xmlrpclib.Fault, error:
        logging.error("Fault code: %d" % error.faultCode)
        logging.error("Fault string: %s" % error.faultString)
        sys.exit(-1)
    except:
        print "Unexpected error 1:", sys.exc_info()[0]
        return 1

    # Write logs
    logging.info("Found {0} servers that have been inactive for {1} days".format(len(inactive_list), DAYS))
    for system in inactive_list:
        logging.info("Server {0} ({1}) is inactive. Last check-in on {2}".format(system['name'], system['id'], system['last_checkin']))
    
    # Printing output
    # for system in inactive_list:
    #    print "{0}\t{1}\t{2}".format(system['id'], system['name'].split(".")[0], system.get('last_checkin'))

    return inactive_list


def delete_inactive(key, client, delete_ids):
    """Remove inactive systems that are marked for decommission from the Satellite server
    
    Args:
        key: Satellite session key.
        client: RPC connection information.
        DAYS: a list of server IDs of the servers to be removed
    
    Returns: 0 if it worked, 1 otherwise
    """
    
    logging.info("Found {0} inactive systems marked to be decommissioned".format(len(delete_ids)))
    try:
        # print "Doing nothing yet, just testing ..."
        client.system.deleteSystems(key, delete_ids)
    except xmlrpclib.Fault, error:
        logging.error("Fault code: %d" % error.faultCode)
        logging.error("Fault string: %s" % error.faultString)
        sys.exit(-1)
    except:
        print "Unexpected error 2:", sys.exc_info()[0]
        return 1
    
    # Write logs
    for system in delete_ids:
        logging.info("Server {0} sucessfully removed from Satellite".format(system))
    
    # Printing output
    # print delete_ids

    return 0


def get_decomm_servers (key, client, DECOMM_GROUP):
    """Get the list of servers marked to be decommissioned
    
    Args:
        key: Satellite session key.
        client: RPC connection information.
        DECOMM_GROUP: name of the group in Satellite used for to-be-decommissioned servers
    
    Returns: A list of servers in the Decommission group. Returns 1 if it fails
    """

    try:
        decomm_list = client.systemgroup.listSystemsMinimal (key, DECOMM_GROUP)
    except xlmrpclib.Fault, error:
        logging.error("Fault code: %d" % error.faultCode)
        logging.error("Fault string: %s" % error.faultString)
        sys.exit(-1)
    except:
        print "Unexpected error 3:", sys.exc_info()[0]
        return 1

    # Write logs
    logging.info("Found {0} marked to be decommissioned".format(len(decomm_list)))
    for system in decomm_list:
        logging.info("Server {0} ({1}) marked to be decommissioned".format(system['name'], system['id']))

    # Printing output
    # print [system['name'] for system in decomm_list]
    
    return decomm_list


def main():
    
    # Measure running time
    start_time = time.time()
    
    client = xmlrpclib.Server(SATELLITE_URL, verbose=0)
    try:
        key = client.auth.login(SATELLITE_LOGIN, SATELLITE_PASSWORD)
    except xmlrpclib.Fault, error:
        logging.error("Fault code: %d" % error.faultCode)
        logging.error("Fault string: %s" % error.faultString)
        sys.exit(-1)
    # SATELLITE_LOGIN = str(raw_input("User (ey.net): ")).rstrip()
    # SATELLITE_PASSWORD = getpass.getpass()
    
    print ("\nGetting Inactive server list from Satellite ...")
    inactives = list_inactive(key, client, DAYS)
    if inactives != 1:
        inactive_ids = [server['id'] for server in inactives]
    else:
        print "Couldn't get the list of inactive servers. Exiting..."
        logging.error("Error getting the list of inactive systems")
        sys.exit(-1)
    
    print ("\nGetting Decomm server list from Satellite ...")
    decomms = get_decomm_servers (key, client, DECOMM_GROUP)
    if decomms != 1:
        decomm_ids = [server['id'] for server in decomms]
    else:
        print "Couldn't get the list of servers to be decommissioned. Exiting..."
        logging.error("Error getting the list of decommissioned servers")
        sys.exit(-1)
    
    print ("\nCalculating the list of servers to be removed from Satellite ...")
    # delete_ids =  list(set(decomm_ids) & set(inactive_ids))
    delete_ids = list(set(decomm_ids).intersection(set(inactive_ids)))
    # Printing Output
    # print delete_ids
    
    if len(delete_ids) > 0:
        print ("\nRemoving server(s) from Satellite ...")
        delete_inactive(key, client, delete_ids)
    else:
        logging.info("Housecleaning is over! No servers were removed")
    
    logging.info("Cleanup process completed. Running time {0:4} seconds".format((time.time() - start_time)))
    
    client.auth.logout(key)
    sys.exit(0)


if __name__ == '__main__':
    # The 0th arg is the module filename
    parser = argparse.ArgumentParser(
    description="This script removes inactive systems that should be ready for decommission")
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    parser.add_argument("-d", "--days", help="Number of inactive days, default 30",
                         type=int)
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        print "\nVerbose mode on, logging to a file...\n"
    if args.days:
        DAYS = args.days
        logging.info("Overriding the default 30 days period, using {0} instead".format(args.days))

    main()
