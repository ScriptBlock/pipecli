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
    action_group.add_argument("--testauth", "-t", help="You can use this to test your client_secret authorization", action="store_true")
    

    args = parser.parse_args()

    config["nameMatches"] = args.pipematch
    config["idMatches"] = args.pipeid
    config["filename"] = args.filename
    config["server"] = args.server
    config["port"] = args.port
    config["secret"] = args.secret
    
    
    if not args.backup and not args.restore and not args.list and not args.testauth:
        quit("You must specify at least one action ")
        
    if args.backup: config["mode"] = "backup"
    if args.restore: config["mode"] = "restore"
    if args.list: config["mode"] = "list"
    if args.testauth: config["mode"] = "testauth"
    
    return config

def obtainCredentials(config):
    print("Getting auth token")
    params = urllib.parse.urlencode({'client_id': 'client-api', 'client_secret': config["secret"], 'grant_type': 'client_credentials' })
    header = {"Content-type":"application/x-www-form-urlencoded"}
    
    dspConnection.request('POST', '/system/identity/v2beta1/token', params, header)
    
    resp = dspConnection.getresponse()
    
    print(resp.status, resp.reason)
    
    if resp.status == 200:
        data = resp.read()
        dataJSON = json.loads(data)    
        return dataJSON["access_token"]
    else:
        print("Unable to get access token from identity API.  check your client_secret")
        quit(resp.reason)
        
    

def setupConnection(config):
    global dspConnection
    dspConnection = http.client.HTTPSConnection(config["server"], config["port"], context=context)
    
def closeConnection():
    global dspConnection
    dspConnection.close()

def buildRequestHeader():
    header = {"Authorization": "Bearer " + config["access_token"]}
    print("Built logged in request header")
    #print(header)
    return header


def testAuthorizationToken():
    dspConnection.request('GET', '/default/streams/v2beta1/license', '', buildRequestHeader())
    resp = dspConnection.getresponse()
    if resp.status == 200:
        print("Connection succeeded")
    else:
        print("Connection failed")
        print(resp.reason)

def pipeListSort(e):
    return e["name"]

def cullToIDList(data):
    retVal = []
    #print("Checking id list against")
    #print(config["idMatches"])
    for i in data:
        if i["id"] in config["idMatches"]:
            retVal.append(i)
    return retVal

def cullToNameMatch(data):
    pass


def listPipelines():
    dspConnection.request('GET', '/default/streams/v2beta1/pipelines?includeData=false', '', buildRequestHeader())
    resp = dspConnection.getresponse()
    if resp.status == 200:
        print("got list of pipelines")
        data = resp.read()
        pipelines = (json.loads(data))["items"]
        pipelines.sort(key=pipeListSort)
        
        if config["idMatches"]: pipelines = cullToIDList(pipelines)
        
        for i in pipelines:
            print(i["name"] + ":\t" + i["description"] + "\t\t\t[" + i["id"] + "]")
    else:
        print("Failed to get list of pipelines.") 
        quit(resp.reason)

def main():
    global config
    config = checkparams()
    setupConnection(config)
    config["access_token"] = obtainCredentials(config)
    
    if config["mode"] == "testauth":
        testAuthorizationToken()
    
    if config["mode"] == "list":
        print("list mode")
        listPipelines()
    
    closeConnection()
    
    
main()
