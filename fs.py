import hashlib
import os
import time


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()

def checknotcopying(file):
    size0 = os.path.getsize(file)
    time.sleep(5)
    size1 = os.path.getsize(file)

    return size0 == size1

def check_file(file, file_types):
    not_empty = os.path.getsize(file) > 0
    not_in_use = checknotcopying(file) and os.access(file, os.R_OK)
    type_ok = os.path.splitext(file)[1] in file_types

    return not_empty and type_ok and is_last_version(file)
    
def is_last_version(filename):
    return last_version(filename) == filename

def last_version(filename):
    dirname = os.path.dirname(filename)
    file_basename = os.path.basename(filename)
    name, ext = os.path.splitext(file_basename)
    filename_without_version = name.rsplit(' ', 1)[0]

    for vers in reversed(range(1, 10)):
        file_vers = os.path.join(dirname, filename_without_version + ' {:02d}'.format(vers) + ext)
        if os.path.exists(file_vers):
            return file_vers


def files_list(watch_folder, file_types):
    list = []
    for root, dirs, files in os.walk(watch_folder):
        for file in files:
            if check_file(os.path.join(root, file), file_types):
                list.append(os.path.join(root, file))

    return list


def find_thumbnail(filename, thumbnails):
    basename = os.path.splitext(os.path.basename(filename))[0]
    dirname = os.path.dirname(filename).split('/')[-1]

    if os.path.dirname(filename) in thumbnails['custom_thumbnails']:
        thumb_file = os.path.join(thumbnails['thumbnail_path_custom'], dirname)
        for ext in thumbnails['thumbnail_types']:
            if os.path.exists(thumb_file + ext):
                return thumb_file + ext

    for ext in thumbnails['thumbnail_types']:
        for version in range(1, 10):
            name = basename[0:-1] + str(version) + ext
            for path in [thumbnails['thumbnail_path'], os.path.dirname(filename) ]:
                vers = os.path.join(path, name)
                if os.path.exists(vers):
                    return vers

                elif os.path.exists(vers.replace('+', '-')):
                    return vers.replace('+', '-')

    return ''
