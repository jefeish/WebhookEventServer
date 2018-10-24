#!/bin/python
import importlib
import yaml
import json
import hmac
import sys
import os
from argparse import ArgumentParser
from hashlib import sha1
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from logging.handlers import RotatingFileHandler
import logging
import requests
from subprocess import call

# Github API - endpoint
github_api = ""

# global 'dict' variable
config = {}

# configure a basic logger
log = logging.getLogger(__name__)

# 
mode = 'prod'

# Web-Server class
class RequestHandler(BaseHTTPRequestHandler):
    global config

    #
    # Process Http GET requests
    #
    def do_GET(self):
        log.warning("Received GET request")
        log.warning("Request path: %s " % self.path)
        log.warning("Request headers: %s " % self.headers)
        # Not handling GET requests !
        self.send_response(404)

    #
    # Process Http POST requests
    # All GitHub events are of type 'Post'
    #
    def do_POST(self):
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        payload = self.rfile.read(length)

        log.debug("Request Header: %s" % request_headers)

        if mode == 'PROD':
            http_code = self.verify_secret(config['server']['secret'], payload)
        else:
            http_code = 0

        if http_code != 0:
            self.send_response(http_code)
            self.send_header("Content-type", "application/json; charset=utf8")
            self.end_headers()
            self.wfile.write(pretty_json('{"error":"secret verification failed"}'))
            return
        else:
            log.debug("payload: %s" % pretty_json(payload))
            response_payload = process_webhook_event(request_headers, payload)

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf8")
        self.end_headers()
        self.wfile.write(response_payload)

    #
    # Process Http PUT requests
    #
    def do_PUT(self):
        self.send_response(202)

    #
    # Process Http DELETE requests
    #
    def do_DELETE(self):
        self.send_response(202)

    #
    # This code is based on 'carlos-jenkins/python-github-webhooks'
    # Limit the incoming requests to only those from our GitHub organization.
    # This is done by comparing the 'secret' from the GitHub server with the local one.
    #
    def verify_secret(self, secret, payload):
        if secret:
            header_signature = self.headers.get('X-Hub-Signature')
            if header_signature is None:
                log.error("Authentication failure [403] - Request header contains no 'Signature'")
                return 403

            sha_name, signature = header_signature.split('=')
            if sha_name != 'sha1':
                log.error("Authentication failure [501] - Received a non 'SHA1' encrypted secret")
                return 501
            log.debug("Secret from 'webhook': %s" % signature )

            # HMAC requires the key to be bytes, but data is string
            secret_bytes = bytes(secret)

            # From Github docs 'Securing your webhooks':
            # "No matter which implementation you use, the hash signature starts with sha1=,
            #  using the key of your secret token and your payload body."
            mac = hmac.new(secret_bytes, payload, sha1)
            log.debug("Secret configured local: %s " % mac.hexdigest() )

            # compare both secret keys
            # check if python version is > 2.7.7 (required)
            if sys.version_info >= (2,7,7):
                if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
                    log.error("Authentication failure [403] - secrets don't match")
                    return 403
                else:
                    if not str(mac.hexdigest()) == str(signature):
                        log.error("Authentication failure [403] - secrets don't match")
                        return 403

        log.debug("'secrets' match, passed !")
        return 0


def process_webhook_event(headers, payload):
    server_config = config['server']
    yml_webhooks = config['webhooks']
    num = 0
    event_match = False
    # get 'X-GitHub-Event' from 'headers', this is the 'Webhook event name'
    webhook_event = headers['X-GitHub-Event']
    log.info("Received Webhook event: %s " % webhook_event)
    log.debug("Event headers: %s" % headers)
    log.debug("Event payload: %s" % payload)
    payload_json = json.loads(payload)

    # trigger all registered actions for the webhook event
    # check each event listed in yaml
    for hook in yml_webhooks:
        yml_event = hook['event']
        yml_description = hook['description']
        # does the event, received from Github, match a yaml event ?
        if yml_event == webhook_event:
            log.debug("Found event in yaml: %s" % yml_event)
            # do we have 'payload_data' to filter on ?
            if hook['payload_attrs']:
                yml_payload_attrs = hook['payload_attrs']
                log.debug("payload_attrs: %s " % yml_payload_attrs)

                for data in yml_payload_attrs:
                    log.debug("yml attr data %s: " % data)
                    key = data.keys()[0]
                    val = find(payload_json, key.split('.'))

                    if data[key] == val:
                        log.debug("event: '%s' has matching data point: '%s' " % (yml_event, key))
                        event_match = True
                    else:
                        event_match = False
                        break

                # we quit the loop
                if event_match:
                    log.info("Found fully matching event: '%s' (%s) " % (yml_event, yml_description))
                    event_match = False # reset
                    # check if the event has 'actions' registered
                    actions = hook['actions']
                    log.debug("actions: %s " % actions)

                    if 'task' in actions:
                        tasks = actions['task']
                        log.debug("Webhook tasks found for event '%s': %s " % (hook, tasks))

                        if tasks and len(tasks) > 0:
                            # execute all 'actions' listed in yaml for event
                            for action in tasks:
                                num += 1
                                log.debug("action %s : %s" % (num,action))

                                module_name = action
                                clazz = 'command'
                                module = __import__(module_name)
                                my_class = getattr(module, clazz)
                                instance = my_class(log, server_config, headers, payload )
                                instance.execute()

                    if 'cmd' in actions:
                        cmds = actions['cmd']
                        log.info("Webhook cmd's found for event ")

                        if cmds and len(cmds) > 0:    
                            # execute all 'commands' listed in yaml for event
                            for cmd in cmds:   
                                log.info("Executing command: %s " % cmd)               
                                os.system(cmd)

    return 0

# -------------------------------------------------------
# Description: A poorman's xPath 
#               Find the provided Path and it's value
# Params: 
#   data - json
#   path - String []
# 
# Return:
#   val - String (if found / nil if not found)
# -------------------------------------------------------  
def find(data, path):
    try:
        if len(path) > 1:
            e = path.pop(0)
            if e.isdigit():
                e = int(e)
            val = find(data[e], path)
        else: # last element
            e = path[0]
            if e.isdigit():
                e = int(e)
            val = (data[e])
    except:
        val = 'nil' # path not found

    return val


def main():
    global config
    port = config['server']['port']
    bind = config['server']['bind']
    server = HTTPServer((bind, port), RequestHandler)
    print("Start listening on %s:%i" % (bind, port))
    log.info("Start listening on %s:%i" % (bind, port))
    # run the Webhook listener
    server.serve_forever()


def pretty_json(data):
    parsed = json.loads(data)
    return json.dumps(parsed, indent=4, sort_keys=True)


def init_logger(log_file, level):
    global log
    log.setLevel(level)
    handler = RotatingFileHandler(log_file, maxBytes=2560000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    # based on the log level, show what's being logged
    log.debug("Enabled")
    log.info("Enabled")
    log.warning("Enabled")
    log.error("Enabled")
    log.critical("Enabled")


if __name__ == "__main__":
    sys.path.append("modules/")
    # load the yaml configuration
    ymlDoc = open("config.yml", "r")
    config = yaml.load(ymlDoc)
    # setup command line arguments - only one right now is 'log level'
    parser = ArgumentParser()
    parser.add_argument('--loglevel','-l', dest='log_level', default='INFO', help='LOG_LEVEL: <debug|info|warning|error|critical> (default: INFO)')
    parser.add_argument('--mode','-m', dest='mode', default='prod', help='Running mode, "DEV" mode = ignore security validation  (default mode=PROD)' )
    args = parser.parse_args()
    level = args.log_level.upper()
    mode = args.mode.upper()

    # setup logger
    init_logger(config['server']['log'], level)

    # start Webhook listener
    main()
