#!/usr/bin/python3.5
#
# Autoupload videos to Youtube
#

import argparse
import http.client
import httplib2
import os
import random
import sys
import time
import logging
from datetime import datetime

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
    http.client.IncompleteRead, http.client.ImproperConnectionState,
    http.client.CannotSendRequest, http.client.CannotSendHeader,
    http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

CLIENT_SECRETS_FILE = "/mnt/scripts/youtubeupload/client_secret.json"
#CLIENT_SECRETS_FILE = "C:\\ServerCmd\\uploadToYoutube\\autoupload\\client_secret_2.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

#------------------------------------------------------------------------

def get_authenticated_service(args):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
        scope=YOUTUBE_UPLOAD_SCOPE,
        message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
        http=credentials.authorize(httplib2.Http()))

#------------------------------------------------------------------------

def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            #channelId="UCSbicIwBeeBxwQNEf7eJWJg",
            categoryId=options.category
        ),
        status=dict(
            privacyStatus=options.privacyStatus
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)

#------------------------------------------------------------------------
# This method implements an exponential backoff strategy to resume a
# failed upload.
#------------------------------------------------------------------------
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            # print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    # print("Video id '%s' was successfully uploaded." % response['id'])
                    return response['id']

                else:
                    logging.error("The upload failed with an unexpected response: %s" % response)
                    exit("The upload failed with an unexpected response: %s" % response)
					
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)

            else:
                logging.error(e)
                raise

        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            # print(error)
            logging.error(error)
            retry += 1
            if retry > MAX_RETRIES:
                logging.error("No longer attempting to retry.")
                exit("No longer attempting to retry.")

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            # print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)

#------------------------------------------------------------------------
# Call the API's thumbnails.set method to upload the thumbnail image and
# associate it with the appropriate video.
#------------------------------------------------------------------------
def upload_thumbnail(youtube, video_id, file):
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=file
    ).execute()

#------------------------------------------------------------------------
# find thumbnail
#------------------------------------------------------------------------
def find_thumbnail(file):
    for fileType in THUMBNAILTYPES:
        # if exists custom thumbnail for program
        if os.path.dirname(file) in THUMBNAILCUSTOM and os.path.exists(os.path.join(THUMBNAILCUSTOMFOLDER, os.path.dirname(file).split('/')[-1] + fileType)):
            return os.path.join(THUMBNAILCUSTOMFOLDER, os.path.dirname(file).split('/')[-1] + fileType)

        #if os.path.dirname(file) in THUMBNAILCUSTOM and os.path.exists(os.path.join(THUMBNAILFOLDER, os.path.dirname(file).split('\\')[-1] + fileType)):
        #    return os.path.join(THUMBNAILFOLDER, os.path.dirname(file).split('\\')[-1] + fileType)


        # if exists custom thumbnail in thumbnails folder
        elif os.path.exists(os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0] + fileType)):
            return os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0] + fileType)

        # if exists custom thumbnail in thumbnails folder ignore sound
        elif os.path.exists(os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0].replace('+', '-') + fileType)):
            return os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0].replace('+', '-') + fileType)

        # if exists custom thumbnail in thumbnails folder ignore sound and version
        elif any(os.path.exists(os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0].replace('+', '-')[0:-1] + str(version) + fileType)) for version in range(1, 10)):
            for version in range(1, 10):
                if os.path.exists(os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0].replace('+', '-')[0:-1] + str(version) + fileType)):
                    return os.path.join(THUMBNAILFOLDER, os.path.splitext(os.path.basename(file))[0].replace('+', '-')[0:-1] + str(version) + fileType)

        # if exists custom thumbnail in program folder
        elif os.path.exists(os.path.splitext(file)[0] + fileType):
            return os.path.splitext(file)[0] + fileType

        # if exists custom thumbnail in program folder ignore sound
        elif os.path.exists(os.path.splitext(file)[0].replace('+', '-') + fileType):
            return os.path.splitext(file)[0].replace('+', '-') + fileType

        # if exists custom thumbnail in program folder ignore sound and version
        elif any(os.path.exists(os.path.splitext(file)[0].replace('+', '-')[0:-1] + str(version) + fileType) for version in range(1, 10)):
            for version in range(1, 10):
                if os.path.exists(os.path.splitext(file)[0].replace('+', '-')[0:-1] + str(version) + fileType):
                    return os.path.splitext(file)[0].replace('+', '-')[0:-1] + str(version) + fileType

        else:
            pass

    # if nothing found
    return ''

#------------------------------------------------------------------------
# Upload files from folder
#------------------------------------------------------------------------
def uploadFolder(watchFolder):
    published = readFileContent(LOGFILE)
    for root, dirs, files in os.walk(watchFolder):
        for file in files:
            #if file.endswith(fileType) and (file) not in published:
            if (os.path.splitext(file)[1] in FILETYPES) and not any (os.path.splitext(file)[0] + fileType in published for fileType in FILETYPES) and checkfile(os.path.join(root, file)):
                arguments = argparse.ArgumentParser()
                arguments.add_argument("--file", help="Video file to upload", default=os.path.join(root, file))
                arguments.add_argument("--title", help="Video title", default=os.path.splitext(file)[0])
                arguments.add_argument("--description", help="Video description", default="")
                arguments.add_argument("--category", default="22", help="Numeric video category. " + "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
                arguments.add_argument("--keywords", help="Video keywords, comma separated", default="")
                arguments.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES, default=VALID_PRIVACY_STATUSES[1], help="Video privacy status.")
                args = arguments.parse_args()

                if not os.path.exists(args.file):
                    logging.error("Not valid file " + file)
                    exit("Please specify a valid file using the --file= parameter.")

                youtube = get_authenticated_service(args)

                try:
                    print(file + '\n')
                    videoID = initialize_upload(youtube, args)

                    # if exist thmbnail file load it
                    if find_thumbnail(args.file):
                        try:
                            upload_thumbnail(youtube, videoID, find_thumbnail(args.file))
                            # print("The custom thumbnail was successfully set.")

                        except HttpError as e:
                            logging.error(file + " An HTTP error %d occured: %s" % (e.resp.status, e.content))
                            # print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

                    writelog(file + '\n', LOGFILE)
                    logging.info(file + " " + videoID)

                except HttpError as e:
                    logging.error(file + "An HTTP error %d occurred: %s" % (e.resp.status, e.content))
                    # print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

#------------------------------------------------------------------------
# check file
#------------------------------------------------------------------------

def checkexists(file, srcDir, dstDir):
    return os.path.isfile(os.path.join(os.path.dirname(file), os.path.splitext(file)[0] + OUT_FILETYPE).replace(srcDir, dstDir))

#------------------------------------------------------------------------

def checknotcopying(file):
    size0 = os.path.getsize(file)
    time.sleep(5)
    size1 = os.path.getsize(file)
    return size0 == size1

#------------------------------------------------------------------------

def checkfile(file):
    return os.path.getsize(file) > 0 and checknotcopying(file) and os.access(file, os.R_OK)

#------------------------------------------------------------------------

def readFileContent(file):
    try:
        readfile = open(file)
        content = readfile.readlines()
        readfile.close()
        content = [w.rstrip() for w in content]
        return content

    except:
        return ''

#------------------------------------------------------------------------

def writelog(msg, file):
    try:
        logfile = open(file, 'a')
        logfile.write(str(msg))
        logfile.close()

    except (IOError, os.error):
        raise

#------------------------------------------------------------------------

FILETYPES = ['.flv', '.mp4']
# SRCDIR = '/mnt/ready_proxy'
SRCDIR = '/mnt/ready'
WATCHDIRS = '/mnt/scripts/youtubeupload/watch.conf'
LOGFILE = '/mnt/scripts/youtubeupload/upload.log'
ERRLOG = '/mnt/scripts/youtubeupload/err.log'
THUMBNAILTYPES = ['.jpg', '.png']
THUMBNAILFOLDER = '/mnt/ready/Скриншоты'
#THUMBNAILCUSTOM = ['/mnt/ready_proxy/ТВ Реальность']
THUMBNAILCUSTOM = ['/mnt/ready/ТВ Реальность']
THUMBNAILCUSTOMFOLDER = '/mnt/scripts/youtubeupload/custom'

logging.basicConfig(filename=ERRLOG, level=logging.ERROR, format='%(asctime)s %(levelname)-8s %(message)s')

#------------------------------------------------------------------------

while True:
    try:
        watch = readFileContent(WATCHDIRS)
        if watch:
            for watchdir in watch:
                watchsrc = os.path.join(SRCDIR, watchdir)
                if os.path.isdir(watchsrc):
                    uploadFolder(watchsrc)

    except:
        pass

    # print("Pause 1 minute...\n")
    time.sleep(60)
