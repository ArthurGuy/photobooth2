#!/usr/bin/env python

import os
import glob
import sys
import dropbox

from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# Access token
TOKEN = 'TKwbt9fdwwsAAAAAAABVANP1ggLNtwAw-_joRFTntvrOZGmgSVYR2sFZwtp0R7rH'

LOCALFILE = '/home/pi/Pictures/*-combined.jpg'
BACKUPPATH = '/photobooth' # Keep the forward slash before destination filename



def backup():
    for photo in glob.glob(LOCALFILE):
        path, file_name = os.path.split(photo)
        # We use WriteMode=overwrite to make sure that the settings in the file
        # are changed on upload
        print("Uploading " + photo + " to Dropbox as " + BACKUPPATH + "/" + file_name)
        try:
            f = open(photo, 'r')
            dbx.files_upload(f.read(), BACKUPPATH + "/" + file_name, mode=WriteMode('overwrite'))
        except ApiError as err:
            if err.error.is_path() and err.error.get_path().error.is_insufficient_space():
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()


# Adding few functions to check file details
def checkFileDetails():
    print("Checking file details")

    for entry in dbx.files_list_folder('').entries:
        print("File list is : ")
        print(entry.name)


# Run this script independently
if __name__ == '__main__':
    print("Creating a Dropbox object...")
    dbx = dropbox.Dropbox(TOKEN)

    # Check that the access token is valid
    try:
        dbx.users_get_current_account()
    except AuthError as err:
        sys.exit("ERROR: Invalid access token; try re-generating an access token from the app console on the web.")

    try:
        checkFileDetails()
    except Error as err:
        sys.exit("Error while checking file details")

    print("Creating backup...")

    backup()

    print("Done!")
