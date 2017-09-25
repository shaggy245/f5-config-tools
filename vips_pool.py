import sys
import requests
import getpass
import argparse
import logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Global Variables
GL_KIND = {"VIP": "tm:ltm:virtual-address:virtual-addressstate", "VS": "tm:ltm:virtual:virtualstate", "POOL": "tm:ltm:pool:poolstate", "SNATPOOL": "tm:ltm:snatpool:snatpoolstate", "SNATTRANS": "tm:ltm:snat-translation:snat-translationstate"}


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

    The key of each item will be the 'kind' of item +  'fullPath' of item
    and the value will be the associated json payload as a defaultdict. The
    'kind' optins can be seen in the print_things function.
    """
    try:
        f5_response_dict = {}
        for item in f5_response.json()["items"]:
            f5_response_dict[str(item["fullPath"])] = item
        return f5_response_dict
    except Exception as exc:
        print exc
        print "\nResponse Code:\n" + str(f5_response.status_code)
        print "\nResponse Headers:\n" + str(f5_response.headers)
        sys.exit(0)


def merge_dicts(dict_args):
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

        all_things = {"vss": all_vs_response, "pools": all_pool_response, "vips": all_vips_response, "snatpools": all_snatpools_response, "snattrans": all_snattrans_response}
        return all_things
    except Exception as exc:
        print exc
        sys.exit(0)


def print_things(all_things):
    """Print to screen for each F5 config item based on 'kind'"""
    print "######################################################"
    for k, thing in all_things.items():
        print "######################################################"
        print k, thing["kind"]
        print k, thing["fullPath"]
        if thing["kind"] == GL_KIND["VIP"]:
            print k, thing["address"]
            print k, thing["trafficGroup"]
        elif thing["kind"] == GL_KIND["VS"]:
            print k, thing["destination"]
            print k, thing.get("pool", "none")
            print k, thing["sourceAddressTranslation"].get("pool", "none")
        elif thing["kind"] == GL_KIND["POOL"]:
            # Iterate over pool members if they exist and
            for member in thing["membersReference"].get("items", "none"):
                # Check if member is a dict before trying to print
                if isinstance(member, dict):
                    print k, member["address"]
        elif thing["kind"] == GL_KIND["SNATTRANS"]:
            print k, thing["address"]
            print k, thing["trafficGroup"]
        elif thing["kind"] == GL_KIND["SNATPOOL"]:
            for member in thing["members"]:
                print k, member


def tie_together(all_things):
    """Tie vs/pool items together for TG/SNAT validation
    Group items by virtual-address - find all vs's and associated pools for a particular virtual-address
    """
    grouped_items = {}
    # Iterate over vss items and start grouping things together
    for k, vs in all_things["vss"].items():
        vip_id = str(vs["destination"].split(":")[0])
        vs_id = k
        pool_id = vs.get("pool", "none")
        snatpool_id = vs["sourceAddressTranslation"].get("pool", "none")

        # Add VIP item
        if vip_id in grouped_items.keys():
            # If VIP already exists in grouped_items, then we don't need to do
            # anything else
            #grouped_items[vip_id][vip_id] = all_things["vips"].get(vip_id, "none")
            pass
        else:
            grouped_items[vip_id] = {}
            grouped_items[vip_id][GL_KIND["VIP"] + vip_id] = all_things["vips"].get(vip_id, "none")
        # Add VS item
        grouped_items[vip_id][GL_KIND["VS"] + vs_id] = vs
        # Add pool item
        if pool_id!="none":
            grouped_items[vip_id][GL_KIND["POOL"] + pool_id] = all_things["pools"].get(pool_id, "none")
        # Add snatpool item
        if snatpool_id!="none":
            grouped_items[vip_id][GL_KIND["SNATPOOL"] + snatpool_id] = all_things["snatpools"].get(snatpool_id, "none")
            snattrans_id = grouped_items[vip_id][GL_KIND["SNATPOOL"] + snatpool_id]["members"]
            for trans_id in snattrans_id:
                grouped_items[vip_id][GL_KIND["SNATTRANS"] + trans_id] = all_things["snattrans"].get(trans_id, "none")

    for k,item in grouped_items.items():
        print_things(item)


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

    all_responses = get_things(args.f5,auth)
    tie_together(all_responses)
    #print_things(all_responses["vips"])
    #print all_responses["vips"].keys()
    #print_things(merge_dicts(all_responses.values()))
