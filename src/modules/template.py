import json
import requests


global log

# Required class name: 'command'
class command():

    def __init__(self, logger, server_config, header, payload):
        global log
        # webhook actions might require this
        self.server_config = server_config
        self.header = header
        self.payload = payload
        log = logger

    # Required name: 'execute'
    # implementing a command pattern
    def execute(self):
        global log
        # TODO: implement the service
