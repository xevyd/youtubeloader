import configparser
import os


def write_default_config(config_file):
    config = {}
    config['default'] = {
        'file_types': '.mp4',
        'thumbnail_types': '.jpg'
    }
    config['log'] = {
        'filename': './error.log'
    }
    config['watch_folders'] = {
        'folders': ''
    }
    with open('upload.ini', 'w') as configfile:
        configfile.write(configfile)

def load_config(config_file):
    config = configparser.ConfigParser()
    if os.path.exists(config_file):
        try:
            config.read(config_file)

        except:
            pass

    else:
        write_default_config(config_file)

    return config
