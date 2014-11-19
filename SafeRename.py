#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Safely parse any "Rename.sh" or "Rename.bat" files for renaming rules.
#
# This removes the risk of running downloaded .sh/.bat files.
#
# NOTE: This script requires Python to be installed on your system.
##############################################################################
#
#

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################
import os
import sys
import re

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PARCHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

if not os.environ.has_key('NZBOP_SCRIPTDIR'):
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)

if os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "[ERROR] NZBGet Version %s is not supported. Please update NZBGet." % (str(os.environ['NZBOP_VERSION']))
    sys.exit(0)

print "Script triggered from NZBGet Version %s." % (str(os.environ['NZBOP_VERSION']))
status = 0
if os.environ.has_key('NZBPP_TOTALSTATUS'):
    if not os.environ['NZBPP_TOTALSTATUS'] == 'SUCCESS':
        print "[ERROR] Download failed with status %s." % (os.environ['NZBPP_STATUS'])
        status = 1

else:
    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print "[ERROR] Par-repair failed, setting status \"failed\"."
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "[ERROR] Unpack failed, setting status \"failed\"."
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            print "[ERROR] Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"."
            print "[ERROR] Please check your Par-check/repair settings for future downloads."
            status = 1

        else:
            print "[ERROR] Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful."
            print "[WARNING] Please check your Par-check/repair settings for future downloads."

# Check if destination directory exists (important for reprocessing of history items)
if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
    print "[ERROR] Nothing to post-process: destination directory", os.environ['NZBPP_DIRECTORY'], "doesn't exist. Setting status \"failed\"."
    status = 1

# All checks done, now launching the script.
if status == 1:
    sys.exit(NZBGET_POSTPROCESS_NONE)

def rename_script(dirname):
    rename_file = ""
    for dir, dirs, files in os.walk(dirname):
        for file in files:
            if re.search('(rename\S*\.(sh|bat))',file):
                rename_file = os.path.join(dir, file)
                dirname = dir
                break
    if rename_file: 
        rename_lines = [line.strip() for line in open(rename_file)]
        for line in rename_lines:
            cmd = filter(None, re.split('mv|Move\s(\S*)\s(\S*)',line))
            if len(cmd) == 2 and os.path.isfile(os.path.join(dirname, cmd[0])):
                orig = os.path.join(dirname, cmd[0])
                dest = os.path.join(dirname, cmd[1].split('\\')[-1].split('/')[-1])
                if os.path.isfile(dest):
                    continue
                print "[INFO] Renaming file %s to %s" % (orig, dest)
                try:
                    os.rename(orig, dest)
                except Exception,e:
                    print "[ERROR] Unable to rename file due to: %s" % (str(e))
                    sys.exit(NZBGET_POSTPROCESS_ERROR)

rename_script(os.path.normpath(os.environ['NZBPP_DIRECTORY']))
sys.exit(NZBGET_POSTPROCESS_SUCCESS)