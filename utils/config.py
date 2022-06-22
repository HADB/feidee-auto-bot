from configparser import ConfigParser

config = ConfigParser()
config.read("config.ini", "UTF-8")

credentials = config["credentials"]


def getint(section, option):
    return config.getint(section, option)
