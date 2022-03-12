#!/bin/python3
# pruner.py
# Prune unwanted addons from currently activated Garry's Mod addons
import requests # Required to query steam api
import json     # Required to parse api results
import enum     # Used for input types
import re       # Used to check urls for ids
import vdf      # Used to parse valve install dirs
import winreg   # Used to determine Steam install dir
import struct   # Used to determine architecture
import os       # Used for paths
ARCH = struct.calcsize("P") * 8

# Constants
class InputType(enum.Enum):
    CLI_ARGS = enum.auto()
    CLI_INPUT = enum.auto()
    GUI_INPUT = enum.auto()

# Retrieve user input
#   Returns: int collection id
def request_user_data(p_inputType):
    if p_inputType == InputType.CLI_ARGS:
        print("Nil")
    elif p_inputType == InputType.CLI_INPUT:
        collection = input("The workshop collection: ")
        collection_search = re.search(r'\d+', collection)
        if collection_search != None:
            collection_id = int(collection_search.group())
            return collection_id
        else:
            print("Error finding collection id from %s" % collection)
            exit(1)
    elif p_inputType == InputType.GUI_INPUT: 
        print("Nil")

# Create a collection metadata request
def query_collection_metadata(p_collection_id):
    url = 'https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/?'
    params = {'itemcount': 1, 'publishedfileids[0]': p_collection_id}
    meta_req = requests.post(url, data=params)
    try:
        meta_req.raise_for_status()
    except HTTPError as e:
        print("HTTPError while retrieving collection metadata")
        print(e)
        exit(1)

    return meta_req

# Create a collection content request
def query_collection_content(p_collection_id):
    url = 'https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/?'
    params = {'collectioncount': 1, 'publishedfileids[0]': p_collection_id}
    content_req = requests.post(url, data=params)

    try:
        content_req.raise_for_status()
    except HTTPError as e:
        print("HTTPError while retrieving collection content")
        print(e)
        exit(1)

    return content_req

# Retrieve a list of workshop items from a workshop collection query
# Returns
# {
#   "id": collection id
#   "name": collection name
#   "content": list of item ids in thhe collection
# }
def get_workshop_info(p_collection_id):
    # Prep return data
    data = { "id": p_collection_id }

    # Get metadata of the collection itself for naming purposes
    meta_req = query_collection_metadata(p_collection_id)
    data["name"] = meta_req.json()["response"]["publishedfiledetails"][0]["title"]

    # Get Collection contents
    content_req = query_collection_content(p_collection_id)
    content_response = content_req.json()["response"]["collectiondetails"][0]
    collection = content_response["children"]
    content_ids = []
    for item in collection:
        content_ids.append(item["publishedfileid"])
    data["content"] = content_ids

    return data

# Get the path to the garrysmod directory
def get_gmod_dir():
    # Find Steam directory
    registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    steamdir_key = ""
    if ARCH == 64:
        steamdir_key = r"SOFTWARE\\WOW6432Node\\Valve\\Steam\\"
    elif ARCH == 32:
        steamdir_key = r"SOFTWARE\\Valve\\Steam\\"
    steamdir_subkey = r"InstallPath"
    steam_path = ""
    with winreg.OpenKeyEx(registry, steamdir_key) as handle:
        steam_path = winreg.QueryValueEx(handle, steamdir_subkey)[0]
    steam_path = os.path.normpath(steam_path)

    # Find Garrysmod directory
    libraryfolders_path = os.path.join(steam_path, r"steamapps\\libraryfolders.vdf")
    library_path = ""
    with open(libraryfolders_path, 'r') as library_file:
        parse = vdf.parse(library_file)["libraryfolders"]
        index = 0
        # Look for installations in the vdf
        while str(index) in parse.keys():
            inst = parse[str(index)]
            inst_path = inst["path"]
            inst_apps = inst["apps"]
            # Check apps in each installation
            if "4000" in inst_apps.keys():
                library_path = inst_path
            index += 1
    
    return os.path.join(library_path, r"steamapps\\common\\GarrysMod\\")

# Append to presets file
def append_preset(p_gmod_path, p_data):
    presets_path = os.path.join(p_gmod_path, r"garrysmod\\settings\\addonpresets.txt")
    print("path is", presets_path)
    
    # Read current file contents
    parse = dict()
    with open(presets_path, 'r') as presets_file:
        parse = json.load(presets_file)

    # Clobber existing preset definition
    parse[p_data["name"]] = dict()
    preset = parse[p_data["name"]]
    # Repopulate
    preset["disabled"] = []
    preset["enabled"] = p_data["content"]
    preset["name"] = p_data["name"]
    preset["newAction"] = ""
        
    # Overwrite file
    with open(presets_path, 'w+') as presets_file:
        json.dump(parse, presets_file, indent=4, ensure_ascii=True)

        

# Main
def main():
    collection_id = request_user_data(InputType.CLI_INPUT)
    data = get_workshop_info(collection_id)
    gmod_dir = get_gmod_dir()
    append_preset(gmod_dir, data)




if __name__=="__main__":
    main()
