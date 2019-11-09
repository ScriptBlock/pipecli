import argparse
import http.client
import urllib.parse
import ssl
import json
import re

config = {}
context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
context.verify_mode = ssl.CERT_NONE

basePipeline = {"bypassValidation":True, "createUserId":"", "data":"","description":"", "name":""}


def checkparams():
    parser = argparse.ArgumentParser(description="Utility for exporting and importing pipelines.  You will need your DSP client secret.  You can obtain this by executing \"sudo kubectl get -n dsp secret auth-provider-api-credentials -o go-template='{{ .data.password | base64decode }}'\" on a DSP master node")

    parser.add_argument("--namematch", "-n", help="Use a regular expression to match pipeline name.  This parameter can be repeated.", action='append')
    parser.add_argument("--idmatch", "-i", help="Use pipeline IDs. This parameter can be repeated", action='append')
    parser.add_argument("--filename", "-f", help="File name for export/import")
    parser.add_argument("--server", "-s", help="DSP server to contact")
    parser.add_argument("--port", "-p", help="DSP port number", default=31000)
    parser.add_argument("--secret", "-secret", help="Client secret.  \"sudo kubectl get -n dsp secret auth-provider-api-credentials -o go-template='{{ .data.password | base64decode }}'\"")
    parser.add_argument("--confirm", "-c", help="Confirm overwriting existing pipelines", action="store_true")
    
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--backup", "-b", help="Export the pipelines that match the given patterns/numbers", action="store_true")
    action_group.add_argument("--restore", "-r", help="Import the pipelines that match the given patterns/numbers", action="store_true")
    action_group.add_argument("--list", "-l", help="List pipelines with their IDs.  Can be combined with NAMEMATCH and IDMATCH to test patterns.", action="store_true")
    action_group.add_argument("--testauth", "-t", help="You can use this to test your client_secret authorization", action="store_true")
    

    args = parser.parse_args()

    config["nameMatches"] = args.namematch
    config["idMatches"] = args.idmatch
    config["filename"] = args.filename
    config["server"] = args.server
    config["port"] = args.port
    config["secret"] = args.secret
    config["confirm_overwrite"] = args.confirm
    
    
    if not args.backup and not args.restore and not args.list and not args.testauth:
        quit("You must specify at least one action ")
        
    if args.backup: config["mode"] = "backup"
    if args.restore: config["mode"] = "restore"
    if args.list: config["mode"] = "list"
    if args.testauth: config["mode"] = "testauth"
    
    return config

def obtainCredentials(config):
    #print("Getting auth token")
    params = urllib.parse.urlencode({'client_id': 'client-api', 'client_secret': config["secret"], 'grant_type': 'client_credentials' })
    header = {"Content-type":"application/x-www-form-urlencoded"}
    
    dspConnection.request('POST', '/system/identity/v2beta1/token', params, header)
    
    resp = dspConnection.getresponse()

    
    #print(resp.status, resp.reason)
    
    if resp.status == 200:
        data = resp.read()
        dataJSON = json.loads(data)    
        dspConnection.close()
        return dataJSON["access_token"]
    else:
        print("Unable to get access token from identity API.  check your client_secret")
        quit(resp.reason)
        
    

def setupConnection(config):
    global dspConnection
    dspConnection = http.client.HTTPSConnection(config["server"], config["port"], context=context)
    
def closeConnection():
    try : 
        dspConnection.close()
    except:
        pass

def buildRequestHeader():
    header = {"Authorization": "Bearer " + config["access_token"]}
    #print("Built logged in request header")
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
    dspConnection.close()

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
    retVal = []
    for i in config["nameMatches"]:
        for j in data:
            if re.search(i, j["name"]): retVal.append(j)
    
    return retVal


def getPipeline(pipeID):
    dspConnection.request('GET', '/default/streams/v2beta1/pipelines/' + pipeID, '', buildRequestHeader())
    resp = dspConnection.getresponse()
    
    if resp.status == 200:
        dspConnection.close()
        return json.loads(resp.read())
    else:
        print("failed to get pipeline id: " + pipeID)
        dspConnection.close()
        quit(resp.reason)

    

def getPipelines(forRestore = False):
    retVal = []
    if (config["filename"] and not config["server"]) or forRestore:
        jsonFile = open(config["filename"], "r")
        pipelines = json.loads(jsonFile.read())
        
    
    else:
        dspConnection.request('GET', '/default/streams/v2beta1/pipelines?includeData=false', '', buildRequestHeader())
        resp = dspConnection.getresponse()
        
        if resp.status == 200:
            #print("got list of pipelines")
            data = resp.read()
            pipelines = (json.loads(data))["items"]
            dspConnection.close()
        else:
            print("Failed to get list of pipelines.") 
            dspConnection.close()
            quit(resp.reason)
        

    pipelines.sort(key=pipeListSort)
    
    if not config["idMatches"] and not config["nameMatches"]: 
        retVal = pipelines
    else:
        if config["idMatches"]:  
            for i in cullToIDList(pipelines):
                if i not in retVal:
                    retVal.append(i)

        if config["nameMatches"]: 
            for i in cullToNameMatch(pipelines):
                if i not in retVal:
                    retVal.append(i)

    #print(retVal)
    return retVal

    

def listPipelines():
    pipelines = getPipelines()
        
    for i in pipelines:
        print(i["name"] + ":\t" + i["description"] + "\t\t\t[" + i["id"] + "]")

def backupPipelines():
    pipelines = getPipelines()
    pipelinesToBackup = []
    for i in pipelines:
        pipelinesToBackup.append(getPipeline(i["id"]))
    
    if config["filename"]:
        backupFile = open(config["filename"], "w")
        backupFile.write(json.dumps(pipelinesToBackup))
        backupFile.close()
    else:
        print(json.dumps(pipelinesToBackup))
    

def restorePipelines():
    if not config["filename"]: 
        quit("you have to specify a filename from which to restore")

    pipelinesFromFile = getPipelines(True)
    
    #print("Retrieved the following pipelines for restore from the file: " + config["filename"])
    #for i in pipelinesFromFile:
    #    print(i["name"] + ":\t[" + i["id"] + "]\t" + i["description"])

    
    pipelinesFromDestinationServer = getPipelines()
    #print("Retrieved the following pipelines from the server")
    #for i in pipelinesFromDestinationServer:
    #    print(i["name"] + ":\t[" + i["id"] + "]\t" + i["description"])


    uniquePipelines = pipelinesFromFile.copy()
    overlappingPipelines = []
    for i in pipelinesFromFile:
        for j in pipelinesFromDestinationServer:
            if i["name"] == j["name"]:
                overlappingPipelines.append({'name':i["name"], 'id':j["id"], 'data':i["data"]})
                for k in uniquePipelines:
                    if i["name"] == k["name"]:
                        #print("removing " + i["name"] + " from unique list")
                        uniquePipelines.remove(k)
                        break
                        

    #print("unique")
    #for i in uniquePipelines:
    #    print(i["name"] + ":\t[" + i["id"] + "]")

    #print("overlapping")
    #for i in overlappingPipelines:
    #    print(i["name"] + ":\t[" + i["id"] + "]")
    
    

    if len(overlappingPipelines) > 0 and not config["confirm_overwrite"]:
        print("The following pipelines already exist in the target DSP instance.  This utility will update the existing pipelines with the definition contained in the backup file. Execute this script with the --confirm switch to proceed.")
        for i in overlappingPipelines:
            print(i["name"] + ":\t[" + i["id"] + "]")


    #main restore procedure here
    for i in uniquePipelines:
        newPipeline = basePipeline.copy()
        newPipeline["data"] = i["data"]
        newPipeline["name"] = i["name"]
        newPipeline["createUserId"] = i["createUserId"]
        newPipeline["description"] = i["description"]

        postJSON = json.dumps(newPipeline)
        postHeader = buildRequestHeader()
        postHeader["Content-Type"] = "application/json"
        postHeader["Accept"] = "application/json"
        #print(postJSON)
        dspConnection.request('POST', '/default/streams/v2beta1/pipelines', postJSON, postHeader)
        resp = dspConnection.getresponse()
        #print(resp.status, resp.reason)
        if resp.status < 300:
            print("Created new pipeline: " + i["name"])
        else:
            print("Failed to create new pipelines for " + i["name"])
            print(resp.reason)

        dspConnection.close()

    if config["confirm_overwrite"]:
        for i in overlappingPipelines:
            newPipeline = {}
            newPipeline["bypassValidation"] = True
            newPipeline["data"] = i["data"]
            newPipeline["id"] = i["id"]

            postJSON = json.dumps(newPipeline)
            postHeader = buildRequestHeader()
            postHeader["Content-Type"] = "application/json"
            postHeader["Accept"] = "application/json"
            #print(postJSON)
            dspConnection.request('PATCH', '/default/streams/v2beta1/pipelines/' + i["id"], postJSON, postHeader)
            resp = dspConnection.getresponse()
            #print(resp.status, resp.reason)
            if resp.status < 300:
                print("Updated existing pipeline: " + i["name"])
            else:
                print("Failed to update pipeline for " + i["name"])
                print(resp.reason)

            dspConnection.close()



def main():
    global config
    config = checkparams()
    if config["server"] and config["secret"]:
        setupConnection(config)
        config["access_token"] = obtainCredentials(config)
    
    if config["mode"] == "testauth":
        testAuthorizationToken()
    
    if config["mode"] == "list":
        #print("list mode")
        listPipelines()
    
    if config["mode"] == "backup":
        #print("backup mode")
        backupPipelines()

    if config["mode"] == "restore":
        restorePipelines()
    
    closeConnection()
    
    
main()
