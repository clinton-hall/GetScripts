GetScripts
==========

A Collection of NZBGet Post-Process Scripts

1. flatten.py
    - This will remove subdirectories and put all downloaded files into the root download directory.
    - You can specify a unique directory and append category sub directory if wanted.
    
2. passwordList.py
    - This will attempt to extract archives using a list of possible passwords.
    
3. ResetDateTime.py
    - This will reset the file dates on downloaded/extracted files, replacing the dates set from within the archive.
    
4. DeleteSamples.py
    - This will delete "sample" files from Video Downloads.

5. SafeRename.py
    - This will parse the download for any "rename.sh" or "rename.bat" scripts and then determine the correct file renaming to be applied.
    - This removes the danger of running any downloaded .sh/.bat files.
