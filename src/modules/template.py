import json
import requests

global log

# implementing a command pattern

# Required class name: 'command'
class command():

    def __init__(self, logger, server_config, header, payload):
        global log
        # webhook actions might require this
        self.server_config = server_config
        self.header = header
        self.payload = payload
        log = logger

    # Required function name: 'execute'
    def execute(self):
        global log
        # TODO: implement the service
        # Your code goes here !
