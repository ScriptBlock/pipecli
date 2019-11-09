import argparse
import http.client
import urllib.parse
import ssl
import json

config = {}
context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
context.verify_mode = ssl.CERT_NONE



def checkparams():
    parser = argparse.ArgumentParser(description="Utility for exporting and importing pipelines.  You will need your DSP client secret.  You can obtain this by executing \"sudo kubectl get -n dsp secret auth-provider-api-credentials -o go-template='{{ .data.password | base64decode }}'\" on a DSP master node")

    parser.add_argument("--pipematch", "-n", help="Use a regular expression to match pipeline name.  This parameter can be repeated.", action='append')
    parser.add_argument("--pipeid", "-id", help="Use pipeline IDs. This parameter can be repeated", action='append')
    parser.add_argument("--filename", "-f", help="File name for export/import")
    parser.add_argument("--server", "-s", help="DSP server to contact")
    parser.add_argument("--port", "-p", help="DSP port number", default=31000)
    parser.add_argument("--secret", "-secret", help="Client secret.  \"sudo kubectl get -n dsp secret auth-provider-api-credentials -o go-template='{{ .data.password | base64decode }}'\"")
    
    
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--backup", "-b", help="Export the pipelines that match the given patterns/numbers", action="store_true")
    action_group.add_argument("--restore", "-r", help="Import the pipelines that match the given patterns/numbers", action="store_true")
    action_group.add_argument("--list", "-l", help="List pipelines with their IDs.  Can be combined with PIPEMATCH and PIPEID to test patterns.", action="store_true")
    

    args = parser.parse_args()

    global config

    config["nameMatches"] = args.pipematch
    config["idMatches"] = args.pipeid
    config["filename"] = args.filename
    config["server"] = args.server
    config["port"] = args.port
    config["secret"] = args.secret
    
    
    if not args.backup and not args.restore and not args.list:
        quit("You must specify at least one action ")
    
    
    if args.backup: config["mode"] = "backup"
    if args.restore: config["mode"] = "restore"
    if args.list: config["mode"] = "list"
    

def obtainCredentials():
    print("Getting auth token")
    params = urllib.parse.urlencode({'client_id': 'client-api', 'client_secret': config["secret"], 'grant_type': 'client_credentials' })
    header = {"Content-type":"application/x-www-form-urlencoded"}
    
    dspConnection.request('POST', '/system/identity/v2beta1/token', params, header)
    
    resp = dspConnection.getresponse()
    
    print(resp.status, resp.reason)
    data = resp.read()
    
    dataJSON = json.loads(data)    
    
    config["token"] = dataJSON["access_token"]
    print("Token: ", dataJSON["access_token"])


def setupConnection():
    global dspConnection
    dspConnection = http.client.HTTPSConnection(config["server"], config["port"], context=context)
    
    

def main():
    checkparams()
    setupConnection()
    obtainCredentials()
    
    if config["mode"] == "list":
        print("list mode")
    
    
    
main()
