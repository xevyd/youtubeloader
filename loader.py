import time
from datetime import datetime
import psycopg2
import os
from types import SimpleNamespace
import logging

import upload_video
from upload_thumbnail import upload_thumbnail
import config
import fs


def find_filename(filename):
    cursor.execute('SELECT * FROM uploaded WHERE filename = %s', (os.path.basename(filename), ))
    return cursor.fetchall()

def find_md5(filename):
    global filename_hash
    filename_hash = fs.md5(filename)
    cursor.execute('SELECT * FROM uploaded WHERE md5 = %s', (filename_hash, ))
    return cursor.fetchall()

def is_uploaded(filename):
    if find_filename(filename) != []:
        return True
    elif find_md5(filename) != []:
        return True
    return False

def db_connect():
    con = psycopg2.connect(user="postgres", password="postgres", host="db", port=5432)
    con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = con.cursor()
    return cursor

def upload(filename):
    args = SimpleNamespace(
        file = filename,
        title = os.path.splitext(os.path.basename(filename))[0],
        description = '',
        category = '22',
        keywords = '',
        privacyStatus = 'private',
    )
    youtube = upload_video.get_authenticated_service(args)

    try:
        youtube_id = upload_video.initialize_upload(youtube, args)
        thumbnail_file = fs.find_thumbnail(filename, thumbnails)
        if thumbnail_file:
            try:
                upload_thumbnail(youtube, youtube_id, thumbnail_file)

            except upload_video.HttpError as e:
                logging.error(filename + " An HTTP error %d occurred: %s" % (e.resp.status, e.content))
            

        cursor.execute("INSERT INTO uploaded (filename, md5, youtube_id, thumbnail, datatime) VALUES (%s, %s, %s, %s, %s)",
                        (filename, filename_hash, youtube_id, thumbnail_file, datetime.now()))

    except upload_video.HttpError as e:
        logging.error(filename + " An HTTP error %d occurred: %s" % (e.resp.status, e.content))


while True:
    conf = config.load_config('./upload.ini')

    logging.basicConfig(filename=conf['log']['filename'], level=logging.ERROR, format='%(asctime)s %(levelname)-8s %(message)s')
    folders_list = conf['watch_folders']['folders'].split('\n')
    thumbnails = { 'thumbnail_types': conf['default']['thumbnail_types'].split(','),
        'thumbnail_path_custom': conf['default']['thumbnail_path_custom'],
        'thumbnail_path': conf['default']['thumbnail_path'],
        'custom_thumbnails': conf['custom_thumbnails']['custom'].split('\n')
    }

    cursor = db_connect()
    cursor.execute("""CREATE TABLE IF NOT EXISTS uploaded 
                    (id SERIAL, filename varchar(512), md5 varchar(32), youtube_id varchar(15),
                     datatime timestamp, thumbnail varchar(512))""")

    for folder in folders_list:
        for filename in fs.files_list(folder, conf['default']['file_types']):
            filename_hash = ''
            if not is_uploaded(filename):
                upload(filename)
