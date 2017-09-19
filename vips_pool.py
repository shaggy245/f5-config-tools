import sys
import requests
import json
import getpass
import argparse
import logging
import collections
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def userpass(username):
    """Determine username and password to use for API auth"""
    if username:
      uname = username
    else:
      uname = raw_input('Username: ')
    upass = getpass.getpass()
    return({"user": uname, "pass": upass})


def icontrol_request(url,method,body,auth):
    # Create URL
    icontrol_url_full = url
    # Create headers
    icontrol_headers = {'Content-Type' : 'application/json'}
    # Create body
    if body:
        icontrol_body = body
    else:
        icontrol_body = ""
    # Create Requests Session object for iControl REST connection reuse
    icontrol_session = requests.Session()

    # run icontrol REST command
    if method=="GET":
        icontrol_response = icontrol_session.get(icontrol_url_full, verify=False, auth=(auth["user"],auth["pass"]), headers=icontrol_headers)
    elif method=="POST":
        icontrol_response = icontrol_session.post(icontrol_url_full, verify=False, auth=(auth["user"],auth["pass"]), headers=icontrol_headers, data=icontrol_body)
    elif method=="PUT":
        icontrol_response = icontrol_session.put(icontrol_url_full, verify=False, auth=(auth["user"],auth["pass"]), headers=icontrol_headers, data=icontrol_body)
    elif method=="PATCH":
        icontrol_response = icontrol_session.patch(icontrol_url_full, verify=False, auth=(auth["user"],auth["pass"]), headers=icontrol_headers, data=icontrol_body)

    return icontrol_response


def create_struct(f5_response):
    """Create dictionary for each set of items.

    The key of each item will be the 'kind' of item + ':' + 'fullPath' of item
    and the value will be the associated json payload as a defaultdict. The
    'kind' optins can be seen in the print_things function.
    """
    try:
        f5_response_dict = {}
        for item in f5_response.json()["items"]:
            f5_response_dict[item["kind"] + ":" + item["fullPath"]] = collections.defaultdict(str,item)
        return f5_response_dict
    except Exception as exc:
        print exc
        print "\nResponse Code:\n" + str(f5_response.status_code)
        print "\nResponse Headers:\n" + str(f5_response.headers)
        sys.exit(0)


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def get_things(host,auth):
    """Make iControl REST calls and return all results as two dicts.

    The first dict is virtual servers since that is the starting point for finding
    other objects, the second is all items in one dict.
    """
    try:
        all_vs_url = "https://%s/mgmt/tm/ltm/virtual" % host
        all_pools_url = "https://%s/mgmt/tm/ltm/pool?expandSubcollections=true" % host
        all_vips_url = "https://%s/mgmt/tm/ltm/virtual-address" % host
        all_snatpools_url = "https://%s/mgmt/tm/ltm/snatpool" % host
        all_snattrans_url = "https://%s/mgmt/tm/ltm/snat-translation" % host

        all_vs_response = create_struct(icontrol_request(all_vs_url,"GET","",auth))
        all_pool_response = create_struct(icontrol_request(all_pools_url,"GET","",auth))
        all_vips_response = create_struct(icontrol_request(all_vips_url,"GET","",auth))
        all_snatpools_response = create_struct(icontrol_request(all_snatpools_url,"GET","",auth))
        all_snattrans_response = create_struct(icontrol_request(all_snattrans_url,"GET","",auth))

        all_things = merge_dicts(all_vs_response, all_pool_response, all_vips_response, all_snatpools_response, all_snattrans_response)
        return all_vs_response, all_things

    except Exception as exc:
        print exc
        sys.exit(0)


def print_things(all_things):
    """Print to screen for each F5 config item based on 'kind'"""
    for thing in all_things:
        print "######################################################"
        print thing["kind"]
        print thing["fullPath"]
        if thing["kind"] == "tm:ltm:virtual-address:virtual-addressstate":
            print thing["address"]
            print thing["trafficGroup"]
        elif thing["kind"] == "tm:ltm:virtual:virtualstate":
            print thing["destination"]
            print thing["pool"]
            # Convert sourceAddressTranslation into defaultdict in case pool doesn't exist
            print collections.defaultdict(str,thing["sourceAddressTranslation"])["pool"]
        elif thing["kind"] == "tm:ltm:pool:poolstate":
            # Convert membersReference into defaultdict in case items doesn't exist
            for member in collections.defaultdict(str,thing["membersReference"])["items"]:
                print member["address"]
        elif thing["kind"] == "tm:ltm:snat-translation:snat-translationstate":
            print thing["address"]
            print thing["trafficGroup"]
        elif thing["kind"] == "tm:ltm:snatpool:snatpoolstate":
            for member in thing["members"]:
                print member


def tie_together(vs_s, all_things):
    """Create a list of lists that combine virtual servers with associated
    virtual addresses, snat-pools, snat-translations, pools, and pool members.
    """
    grouped_items = []
    for vs in vs_s.values():
        pass



if __name__ == "__main__":
    # Set logging level to critical and log to stdout to prevent unnecessary errors being sent to stdout
    logging.basicConfig(level=50)

    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description="Get list of all F5 virtual servers, associated pools, and associated pool members.")
    parser.add_argument("-l", "--username",help="Specify username. If no username is supplied, script will prompt for username",type=str)
    parser.add_argument("f5", help="Specify the F5 to query.",type=str)
    args=parser.parse_args()

    # If no username supplied in args, ask for username and get password
    auth = userpass(args.username)

    all_vs, all_responses = get_things(args.f5,auth)
    tie_together(all_vs, all_responses)
