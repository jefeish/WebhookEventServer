import json
import requests

global log

# Required class name: 'command'
class command():

    def __init__(self, logger, server_config, header, payload):
        global log
        # webhook action requires this
        self.server_config = server_config
        self.header = header
        self.payload = payload
        log = logger

    # Required name: 'execute'
    # implementing a command pattern
    def execute(self):
        '''Create a notification on github.com using the given parameters.'''
        global log
        log.info("executing 'create_notification' module")

        github_api_url = self.server_config['github_api']
        headers = {'x-webhook-action': 'create_notification'}
        
        # TODO - implement some notification code...
