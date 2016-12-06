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
### OPTIONS                                                                ###

# CHMOD.
#
# Enter the octal permissions to be applied to extracted/created directories.
#CHMOD=0775

# CleanUp.
# Enter the comma separated extensions of files to be removed after successful extraction/rename.
# e.g. .sh,.rar,.zip,.bat
#CleanUp=.sh,.bat

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################
import os
import sys
import re
import shlex
import platform
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

    CHMOD = int(str(os.environ["NZBPO_CHMOD"]), 8)
    CLEANUP = os.environ["NZBPO_CLEANUP"].split(',')

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

    CHMOD = int("0775", 8)
    CLEANUP = [".sh", ".bat"]

    if status == 1:
        sys.exit(0)

else:
    print "[ERROR] This script only supports NZBGet or SABnzbd. Exiting."
    sys.exit(0)

# All checks done, now launching the script.
def rename_script(dirname):
    rename_file = ""
    new_dir = ""
    new_dir2 = ""
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
                new_dir2 = rename_cmd(shlex.split(line)[1:], dirname)
            if re.search('^(unrar)', line, re.IGNORECASE):
                cmd = extract_command(shlex.split(line), dirname)
                devnull = open(os.devnull, 'w')
                print "[INFO] Extracting file %s with command %s" % (rename_file, cmd)
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
                newfile = os.path.splitext(cmd[-1])[0] + os.path.splitext(rename_file)[1]
                print "[INFO] Checking for file %s" % (os.path.join(dirname, newfile))
                if os.path.isfile(os.path.join(dirname, newfile)):
                    print "[INFO] Reading lines from %s" % (os.path.join(dirname, newfile)) 
                    rename_lines2 = [line2.strip() for line2 in open(os.path.join(dirname, newfile))]
                    print "[INFO] Parsing %s lines from %s" % (str(len(rename_lines2)), os.path.join(dirname, newfile))
                    for line2 in rename_lines2:
                        if re.search('^(mv|Move)', line2, re.IGNORECASE):
                            new_dir2 = rename_cmd(shlex.split(line2)[1:], dirname)
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

    for dir, dirs, files in os.walk(dirname):
        for file in files:
            filepath = os.path.join(dir, file)
            if os.path.splitext(file)[1] in CLEANUP:
                try:
                    os.unlink(filepath)
                except:
                    print "Error: unable to delete file", filePath

    if not new_dir and new_dir2:
        if os.path.split(new_dir2)[0] == dirname:
            new_dir = os.path.splitext(new_dir2)[0]
        else:
            new_dir = os.path.split(new_dir2)[0]
    if new_dir:
        if CHMOD:
            logger.log("Changing file mode of {0} to {1}".format(new_dir, oct(CHMOD)))
            os.chmod(new_dir, CHMOD)
            for dir, dirs, files in os.walk(new_dir):
                for dirname in dirs:
                    os.chmod(os.path.join(dir, dirname), CHMOD)
                for file in files:
                    os.chmod(os.path.join(dir, file), CHMOD)

        out_dir = os.path.join(os.path.split(dirname)[0], os.path.split(new_dir)[1])
        if not os.path.exists(out_dir):
            os.rename(dirname, out_dir)
            print "[NZB] DIRECTORY=%s" % (out_dir)

def rename_cmd(cmd, dirname):
    if len(cmd) == 2 and os.path.exists(os.path.join(dirname, cmd[0])):
        orig = os.path.join(dirname, cmd[0].replace('\\',os.path.sep).replace('/',os.path.sep))
        dest = os.path.join(dirname, cmd[1].replace('\\',os.path.sep).replace('/',os.path.sep))
        if os.path.isfile(dest):
            return
        print "[INFO] Renaming file %s to %s" % (orig, dest)
        try:
            if not os.path.exists(os.path.split(dest)[0]):
                os.makedirs(os.path.split(dest)[0])
            os.rename(orig, dest)
            return dest
        except Exception,e:
            print "[ERROR] Unable to rename file due to: %s" % (str(e))
            sys.exit(NZBGET_POSTPROCESS_ERROR)

def extract_command(cmdin, dir):
    # Using Windows
    if platform.system() == 'Windows':
        if not os.path.exists(SEVENZIP):
            print(" Could not find 7-zip, Exiting")
            sys.exit(NZBGET_POSTPROCESS_ERROR)
        else:
            cmd_7zip = [SEVENZIP, "x", "-y"]
            ext_7zip = [".rar", ".zip", ".tar.gz", "tgz", ".tar.bz2", ".tbz", ".tar.lzma", ".tlz", ".7z", ".xz"]
            EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds = ["unrar", "unzip", "tar", "unxz", "unlzma", "7zr", "bunzip2"]
        EXTRACT_COMMANDS = {
            ".rar": ["unrar", "x", "-o+", "-y"],
            ".tar": ["tar", "-xf"],
            ".zip": ["unzip"],
            ".tar.gz": ["tar", "-xzf"], ".tgz": ["tar", "-xzf"],
            ".tar.bz2": ["tar", "-xjf"], ".tbz": ["tar", "-xjf"],
            ".tar.lzma": ["tar", "--lzma", "-xf"], ".tlz": ["tar", "--lzma", "-xf"],
            ".tar.xz": ["tar", "--xz", "-xf"], ".txz": ["tar", "--xz", "-xf"],
            ".7z": ["7zr", "x"],
        }    # Test command exists and if not, remove
        devnull = open(os.devnull, 'w')
        for cmd in required_cmds:
            if call(['which', cmd], stdout=devnull,
                    stderr=devnull):  # note, returns 0 if exists, or 1 if doesn't exist.
                for k, v in EXTRACT_COMMANDS.items():
                    if cmd in v[0]:
                        if not call(["which", "7zr"], stdout=devnull, stderr=devnull):  # we do have "7zr"
                            EXTRACT_COMMANDS[k] = ["7zr", "x", "-y"]
                        elif not call(["which", "7z"], stdout=devnull, stderr=devnull):  # we do have "7z"
                            EXTRACT_COMMANDS[k] = ["7z", "x", "-y"]
                        elif not call(["which", "7za"], stdout=devnull, stderr=devnull):  # we do have "7za"
                            EXTRACT_COMMANDS[k] = ["7za", "x", "-y"]
                        else:
                            print("%s not found, disabling support for %s" % (cmd, k))
                            del EXTRACT_COMMANDS[k]
        devnull.close()

        if not EXTRACT_COMMANDS:
            print("No archive extracting programs found, plugin will be disabled")
            sys.exit(NZBGET_POSTPROCESS_ERROR)

    ext = os.path.splitext(cmdin[-1])[1]
    if not os.path.exists(cmdin[-1]):
        newpath = os.path.join(dir, cmdin[-1])
    else:
        newpath = cmdin[-1]

    newcmd = EXTRACT_COMMANDS[ext]
    newcmd.extend(cmdin[2:-1])
    newcmd.append(newpath)
    return newcmd

rename_script(dirname)
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    sys.exit(NZBGET_POSTPROCESS_SUCCESS)
else:
    sys.exit(0)
