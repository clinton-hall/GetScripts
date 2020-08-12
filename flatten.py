#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Flatten all downloaded files into the root download directory.
#
# This removes all of the sub-folders created by the unpack process.
# This should run before other scripts.
#
# NOTE: This script requires Python to be installed on your system.
##############################################################################
### OPTIONS                                                                ###

# Destination Directory.
#
# Set the directory where you want all files to be moved to.
# Use this if you want all downloaded files in a single "root" directory.
# If left blank, files will all be "flattened" into the individual download's sub-directory.
#DestinationDirectory=

# Append Categories (yes, no).
# 
# If using the Destination Directory above, then this option will append the download category.
#AppendCategories=no


### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################
import os
import sys
import shutil

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PARCHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

if 'NZBOP_SCRIPTDIR' not in os.environ:
    print("This script can only be called from NZBGet (11.0 or later).")
    sys.exit(0)

if os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print("[ERROR] NZBGet Version %s is not supported. Please update NZBGet." % (str(os.environ['NZBOP_VERSION'])))
    sys.exit(0)

print("Script triggered from NZBGet Version %s." % (str(os.environ['NZBOP_VERSION'])))
status = 0
if 'NZBPP_TOTALSTATUS' in os.environ:
    if not os.environ['NZBPP_TOTALSTATUS'] == 'SUCCESS':
        print("[ERROR] Download failed with status %s." % (os.environ['NZBPP_STATUS']))
        status = 1

else:
    # Check par status
    if os.environ.get('NZBPP_PARSTATUS') == '1' or os.environ.get('NZBPP_PARSTATUS') == '4':
        print("[ERROR] Par-repair failed, setting status \"failed\".")
        status = 1

    # Check unpack status
    if os.environ.get('NZBPP_UNPACKSTATUS') == '1':
        print("[ERROR] Unpack failed, setting status \"failed\".")
        status = 1

    if os.environ.get('NZBPP_UNPACKSTATUS') == '0' and os.environ.get('NZBPP_PARSTATUS') == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ.get('NZBPP_HEALTH') < 1000:
            print("[ERROR] Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\".")
            print("[ERROR] Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            print("[ERROR] Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful.")
            print("[WARNING] Please check your Par-check/repair settings for future downloads.")

# Check if destination directory exists (important for reprocessing of history items)
if not os.path.isdir(os.environ.get('NZBPP_DIRECTORY')):
    print("[ERROR] Nothing to post-process: destination directory", os.environ['NZBPP_DIRECTORY'], "doesn't exist. Setting status \"failed\".")
    status = 1

# All checks done, now launching the script.
if status == 1:
    sys.exit(NZBGET_POSTPROCESS_NONE)

def removeEmptyFolders(path, removeRoot=True):
    #Function to remove empty folders
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    print("[INFO] Checking for empty folders in:%s" % path)
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                removeEmptyFolders(fullpath)

    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and removeRoot:
        print("[INFO] Removing empty folder:%s" % path)
        os.rmdir(path)

directory = os.path.normpath(os.environ.get('NZBPP_DIRECTORY'))
if os.environ.get('NZBPO_DESTINATIONDIRECTORY', False) and os.path.isdir(os.environ.get('NZBPO_DESTINATIONDIRECTORY')):
    destination = os.environ.get('NZBPO_DESTINATIONDIRECTORY')
    if os.environ.get('NZBPO_APPENDCATEGORIES') == 'yes':
        destination = os.path.join(destination, os.environ.get('NZBPP_CATEGORY'))
else:
    destination = directory
print("Flattening directory: %s" % (directory))
for dirpath, dirnames, filenames in os.walk(directory):
    for fileName in filenames:
        outputFile = os.path.join(dirpath, fileName)
        if dirpath == destination:
            continue
        target = os.path.join(destination, fileName)
        try:
            shutil.move(outputFile, target)
        except:
            print("[ERROR] Could not flatten %s" % outputFile)
removeEmptyFolders(directory)  # Cleanup empty directories
sys.exit(NZBGET_POSTPROCESS_SUCCESS)
