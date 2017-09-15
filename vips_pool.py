import requests
import json
import getpass
import argparse
import logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def userpass(username):
    """
    Determine username and password to use for API auth
    """
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


def get_things(host,auth):
    try:
        all_vs_url = "https://%s/mgmt/tm/ltm/virtual" % host
        all_pools_url = "https://%s/mgmt/tm/ltm/pool?expandSubcollections=true" % host
        all_vips_url = "https://%s/mgmt/tm/ltm/virtual-address" % host
        all_snatpools_url = "https://%s/mgmt/tm/ltm/snatpool" % host
        all_snattrans_url = "https://%s/mgmt/tm/ltm/snat-translation" % host

        all_vs_response = icontrol_request(all_vs_url,"GET","",auth)
        all_pool_response = icontrol_request(all_pools_url,"GET","",auth)
        all_vips_response = icontrol_request(all_vips_url,"GET","",auth)
        all_snatpools_response = icontrol_request(all_snatpools_url,"GET","",auth)
        all_snattrans_response = icontrol_request(all_snattrans_url,"GET","",auth)

        all_responses = [all_vs_response,all_pool_response,all_vips_response,all_snatpools_response,all_snattrans_response]

        return all_responses
    except Exception as exc:
        print exc
        sys.exit(0)


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

    friendly = True
    all_responses = get_things(args.f5,auth)
    for icontrol_response in all_responses:
        # print response code and reason, headers, body
        print "\nResponse Code:\n" + str(icontrol_response.status_code)

        print "\nResponse Headers:\n" + str(icontrol_response.headers)
        try:
            if friendly:
                print "\nResponse Body:\n" + json.dumps(icontrol_response.json(), sort_keys=True,indent=2, separators=(',',': '))
            else:
                print "\nResponse Body:\n%s" % json.dumps(icontrol_response.json())
        except Exception as exc:
            print "\nResponse Body: No body"
        print "######################################################################################################################################\n######################################################################################################################################\n######################################################################################################################################\n######################################################################################################################################\n######################################################################################################################################\n######################################################################################################################################\n######################################################################################################################################\n################################\n"
