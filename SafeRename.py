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
import shlex
from subprocess import call, Popen

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PARCHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

if os.environ.has_key('NZBOP_SCRIPTDIR'):
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

    if status == 1:
        sys.exit(NZBGET_POSTPROCESS_NONE)

    dirname = os.path.normpath(os.environ['NZBPP_DIRECTORY'])

# SABnzbd
elif len(sys.argv) >= 8:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    clientAgent = 'sabnzbd'
    print "Script triggered from SABnzbd"
    dirname = sys.argv[1]
    status = sys.argv[7]

    if status == 1:
        sys.exit(0)

else:
    print "[ERROR] This script only supports NZBGet or SABnzbd. Exiting."
    sys.exit(0)

# All checks done, now launching the script.
def rename_script(dirname):
    rename_file = ""
    for dir, dirs, files in os.walk(dirname):
        for file in files:
            if re.search('(rename\S*\.(sh|bat)$)',file,re.IGNORECASE) or file == 'What.sh':
                rename_file = os.path.join(dir, file)
                dirname = dir
                break
    if rename_file: 
        rename_lines = [line.strip() for line in open(rename_file)]
        for line in rename_lines:
            if re.search('^(mv|Move)', line, re.IGNORECASE):
                rename_cmd(shlex.split(line)[1:], dirname)
            if re.search('^(unrar)', line, re.IGNORECASE):
                cmd = shlex.split(line)
                devnull = open(os.devnull, 'w')
                print "[INFO] Extracting file %s with command %s" % (rename_file, line)
                pwd = os.getcwd()  # Get our Present Working Directory
                os.chdir(dirname)  # Not all unpack commands accept full paths, so just extract into this directory
                p = Popen(cmd, stdout=devnull, stderr=devnull)  # should extract files fine.
                res = p.wait()
                devnull.close()
                os.chdir(pwd)
                if res == 0:
                    print "[INFO] Extraction was successfull"
                else:
                    print "[INFO] Extraction failed"
                    sys.exit(NZBGET_POSTPROCESS_ERROR)
                newfile = os.path.splitext(cmd[-1])[0] + '.sh'
                print "[INFO] Checking for file %s" % (os.path.join(dirname, newfile))
                if os.path.isfile(os.path.join(dirname, newfile)):
                    print "[INFO] Reading lines from %s" % (os.path.join(dirname, newfile)) 
                    rename_lines2 = [line2.strip() for line2 in open(os.path.join(dirname, newfile))]
                    print "[INFO] Parsing %s lines from %s" % (str(len(rename_lines2)), os.path.join(dirname, newfile))
                    for line2 in rename_lines2:
                        if re.search('^(mv|Move)', line2, re.IGNORECASE):
                            rename_cmd(shlex.split(line2)[1:], dirname)
                        if re.search('^(mkdir)', line2, re.IGNORECASE):
                            new_dir = os.path.join(dirname, shlex.split(line2)[-1])
                            print "[INFO] Creating directory %s" % (new_dir)
                            if os.path.isdir(new_dir):
                                continue
                            os.makedirs(new_dir)
                else:
                    print "[INFO] File %s not found" % (os.path.join(dirname, newfile))
            else:
                continue
def rename_cmd(cmd, dirname):
    if len(cmd) == 2 and os.path.isfile(os.path.join(dirname, cmd[0])):
        orig = os.path.join(dirname, cmd[0].replace('\\',os.path.sep).replace('/',os.path.sep))
        dest = os.path.join(dirname, cmd[1].replace('\\',os.path.sep).replace('/',os.path.sep))
        if os.path.isfile(dest):
            return
        print "[INFO] Renaming file %s to %s" % (orig, dest)
        try:
            os.rename(orig, dest)
        except Exception,e:
            print "[ERROR] Unable to rename file due to: %s" % (str(e))
            sys.exit(NZBGET_POSTPROCESS_ERROR)

rename_script(dirname)
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    sys.exit(NZBGET_POSTPROCESS_SUCCESS)
else:
    sys.exit(0)
