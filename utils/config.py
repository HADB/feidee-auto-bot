import json

config = {}
credentials = {}


def load_config():
    global config
    with open("config.json") as config_file:
        print("load_config")
        config = json.load(config_file)


def load_credentials():
    global credentials
    with open("credentials.json") as credentials_file:
        print("load_credentials")
        credentials = json.load(credentials_file)
