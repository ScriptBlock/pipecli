# pipecli
Command line tool for exporting and importing DSP pipelines

Uses client secret and API to do pipelines backups and restores to and from text files.

## Modes
 - testauth: combined with --server and --secret, will test obtaining authorization token
 - list: if you have a --server and --secret, this will list out pipelines found in the DSP instance.  
         if you have a --filename and NOT a --server, then this will list out the pipelines found in the provided file.

 - backup: combined with --server and --secret will export pipeline detail.  
           if you don't specify a --filename, then output will be to stdout, otherwise will send to the file (overwriting)

 - restore: --server and --secret indicate the DSP instance that the restore will target.  --filename is required to import data from.
            restore supports both new pipelines and replacing existing pipelines with different pipeline definition.  If the script detects existing pipelines in the target server, you must specify the --confim parameter to perform the overwrite.  This script leverages the **PATCH** API call for updating pipelines.  

 **Note that list, backup, and restore modes ALL work with the idmatch and namematch parameters**

## Parameters
 - namematch: regex pattern for pipelines names to match.  can be specified multiple times
 	- eg - ./pipecli ... --namematch ^Foo --namematch Bar$

 - idmatch: literal pipeline ID matching
 	- eg - ./pipecli .. --idmatch 0eaa1683-6b43-46fa-9290-8826e6c9bf32

 - filename:  for **backups**, this is the file that the backup data should be written to.  
              for **restores**, this is the file that the restore data is coming from.
              for **list**, this is the file to read from (as long as --server isn't specified)

 - server:  for **backups**, this is the server to pull the pipeline data from.
            for **restores**, this is the server to push the pipeline data to.

 - port: defaults to 31000, can be changed to whatever

 - secret: this is the client-id secret from your dsp instance, which notably will be different if you are backing up and restore to/from different DSP instances.  The easiest way to get the client secret is to SSH into a DSP server and execute `sudo kubectl get -n dsp secret auth-provider-api-credentials -o go-template='{{ .data.password | base64decode }}'`.  You can use this client-id verbatim in the --secret parameter.

 - confirm:  user must specify this parameter to overwrite existing pipelines as part of restore.