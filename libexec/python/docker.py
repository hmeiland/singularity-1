#!/usr/bin/env python

'''

docker.py: Docker helper functions for Singularity in Python

Copyright (c) 2016, Vanessa Sochat. All rights reserved. 

"Singularity" Copyright (c) 2016, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Dept. of Energy).  All rights reserved.
 
This software is licensed under a customized 3-clause BSD license.  Please
consult LICENSE file distributed with the sources of this project regarding
your rights to use or distribute this software.
 
NOTICE.  This Software was developed under funding from the U.S. Department of
Energy and the U.S. Government consequently retains certain rights. As such,
the U.S. Government has been granted for itself and others acting on its
behalf a paid-up, nonexclusive, irrevocable, worldwide license in the Software
to reproduce, distribute copies to the public, prepare derivative works, and
perform publicly and display publicly, and to permit other to do so. 

'''

from utils import api_get, write_file
import sys
import json

# Authentication not required ---------------------------------------------------------------------------------

def create_runscript(cmd,base_dir):
    '''create_runscript will write a bash script with command "cmd" into the base_dir
    :param cmd: the command to write into the bash script
    :param base_dir: the base directory to write the runscript to
    '''
    runscript = "%s/singularity" %(base_dir)
    content = "!#/bin/sh\n\n%s" %(cmd)
    output_file = write_file(runscript,content)
    return output_file


def list_images(repo_name,namespace="library",scope="repositories",content="images",return_response=False):
    '''get_images will use version 1.0 of Docker's service to return a list of images (no auth required)
    :param repo_name: the name of the repo, eg "ubuntu"
    :param namespace: the namespace to use, (collection/owner of repos), default is "library"
    :param scope: scope of the request, default is "repositories"
    '''
    base = "https://registry.hub.docker.com/v1/%s/%s/%s/%s" %(scope,namespace,repo_name,content)

    response = api_get(base)
    images = None
    try:
        images = json.loads(response)
    except:
        print("Error retrieving images.")
    return images     


def get_manifest(image_id,token,content="json"):
    '''get_manifest returns metadata about an image layer
    :param image_id: the (full) image id to get the manifest for, required
    :param token: the header token obtained from get_token
    '''
    base = "https://cdn-registry-1.docker.io/v1/images/%s/%s" %(image_id,content)

    # Token should come as a dictionary (meaning a header for requests) if not, put it into one
    if not isinstance(token,dict):
        token = {"Authentication":"Token %s" %(token)}

    response = api_get(base,headers=token)
    manifest = None
    try:
        manifest = json.loads(response)
    except:
        print("Error retrieving manifest.")
    return manifest


def get_layer(image_id,token,download_folder=None,content="layer"):
    '''get_layer will download an image layer (.tar.gz) to a specified download folder.
    :param image_id: the (full) image id to get the manifest for, required
    :param token: the token header obtained from get_token
    :param download_folder: if specified, download to folder. Otherwise return response with raw data (not recommended)
    '''
    base = "https://cdn-registry-1.docker.io/v1/images/%s/%s" %(image_id,content)

    # Token should come as a dictionary (meaning a header for requests) if not, put it into one
    if not isinstance(token,dict):
        token = {"Authentication":"Token %s" %(token)}

    if download_folder != None:
        download_folder = "%s/%s.tar.gz" %(download_folder,image_id)
  
        # Update user what we are doing
        print("Downloading layer %s.tar.gz to %s" %(image_id,download_folder))

    return api_get(base,headers=token,stream=download_folder)



def get_tags(repo_name,repo_tag=None,namespace="library",content="tags",scope="repositories"):
    '''get_tags will use version 1.0 of the api (registry.hub.docker.com) to return image ids (layers) associated with a tag
    :param repo_name: the name of the repo, required
    :param repo_tag: the repo tag, default tag None will return all tags.
    :param namespace: the namespace to use, (collection/owner of repos), default is "library"
    :param scope: the scope of the request, default is repositories
    :param content: the api call to make, default is "tags" to get tags
    # note that if you change v1 to v2 below, you get a different result, but doesn't include image ids
    '''

    # If the user wants all tags
    if repo_tag == None:
        base = "https://registry.hub.docker.com/v1/%s/%s/%s/%s" %(scope,namespace,repo_name,content)
    else:
        base = "https://registry.hub.docker.com/v1/%s/%s/%s/%s/%s" %(scope,namespace,repo_name,content,repo_tag)

    # The response is a string with json that needs to be read
    response = api_get(base)

    # Try to load the json, if it fails, then tell the user valid tags (given that a specific tag is wanted)
    try:
        tags = json.loads(response)
        print("Found %s tags for image %s/%s!" %(len(tags),namespace,repo_name))
        return tags

    except:

        # Have function call itself only if error is due to missing tag (otherwise loop)
        if repo_tag != None:
            tags = get_tags(repo_name=repo_name,
                           namespace=namespace,
                           repo_tag=None)        
            print("\n".join([x['name'] for x in tags]))
            print('Cannot find tag "%s" for repo %s/%s, valid tags are listed above.' %(repo_tag,namespace,repo_name))

        else:
            print("Error retrieving tags for repo %s/%s" %(namespace,repo_name))
        
        # Always exit with error    
        sys.exit(1)


def get_token(repo_name,namespace="library",scope="repositories",content="images",header=True):
    '''get_token will use version 1.0 of Docker's service to return a token with given permission and scope
    (this one seems to work)
    :param repo_name: the name of the repo, eg "ubuntu"
    :param namespace: the namespace to use, (collection/owner of repos), default is "library"
    :param scope: scope of the request, default is "repository"
    :param return_full: if False, will return only the token. If True, returns the entire response
    :param header: if True, will return a header object for requests module (default True)
    '''
    base = "https://registry.hub.docker.com/v1/%s/%s/%s/%s" %(scope,namespace,repo_name,content)

    headers = {"X-Docker-Token":True}
    response = api_get(base,
                       headers=headers,
                       return_response=True)
   
    token = response.info().getheader('x-docker-token',None)
    if token != None:
        if header == True:
            return {"Authorization":"Token %s" %(token)}
    return token


# Authentication required ---------------------------------------------------------------------------------



#####################################################################################
# NOT IN USE ------------------------------------------------------------------------
# Functions that should work, but don't, mostly for version 2.0 of the Docker API
# NOTE that these functions were written to use requests module, and need to be 
# updated to use urllib and urllib2 (@vsoch)
# https://docs.docker.com/registry/spec/api/#/detail
# -----------------------------------------------------------------------------------


def _get_token(repo_name,namespace="library",scope="repository",permission="push,pull"):
    '''get_token will use version 2.0 of Docker's service to return a token with given permission and scope - this
    function does work, but the token doesn't seem to work when used with other functions below for authentication
    :param repo_name: the name of the repo, eg "ubuntu"
    :param repo_tag: the name of a tag for the repo, default is "latest"
    :param scope: scope of the request, default is "repository"
    :param permission: permission for the request, default is "read"
    '''

    base = "https://auth.docker.io/token?service=registry.docker.io&scope=%s:%s/%s:%s" %(scope,
                                                                                          namespace,
                                                                                          repo_name,
                                                                                          permission)
    response = api_get(base,default_header=False)
    try:
        token = json.loads(response)["token"]
    except:
        print("Error retrieving token from Docker registry.")
        token = None
    return token


def _get_manifest(repo_name,namespace,repo_tag="latest"):
    '''get_manifest should return an image manifest for a particular repo and tag. The token is expected to
    be from version 2.0 (function above) but I never got it to work.
    :param repo_name: the name of the repo, eg "ubuntu"
    :param repo_tag: the repo tag, default is "latest"
    '''
    base = "https://registry.docker.io/v2/%s/manifests/%s" %(repo_name,repo_tag)
    
    # To get the image layers, we need a valid token to read the repo
    token = _get_token(repo_name=repo_name,permission="pull")

    # If the token function returns None, there was an error
    if token == None:
        print("Error getting read token for repository %s/%s, exiting." %(namespace,repo_name))
        sys.exit(1)

    # default headers docs say are required, doesn't seem to matter
    headers = {"Docker-Distribution-API-Version":"registry/2.0"}

    # Format the token, and prepare a header
    # https://docs.docker.com/registry/spec/auth/token/
    headers.update({"Authorization": "Bearer %s" %(token) })
    response = api_get(base,headers=headers)
    return response
    # u'{"errors":[{"code":"UNAUTHORIZED","message":"authentication required","detail":[{"Type":"repository","Name":"ubuntu","Action":"pull"}]}]}\n'
    
