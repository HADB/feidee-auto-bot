import json

config = {}

with open("config.json") as config_file:
    config = json.load(config_file)

credentials = config["credentials"]
app = config["app"]
