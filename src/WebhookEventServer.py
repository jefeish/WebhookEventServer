#!/bin/python
import importlib
import yaml
import json
import hmac
import sys
from argparse import ArgumentParser
from hashlib import sha1
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from logging.handlers import RotatingFileHandler
import logging
import requests

# Github API - endpoint
github_api = ""

# global 'dict' variable
config = {}

# configure a basic logger
log = logging.getLogger(__name__)

# these are all the events available in GitHub
events=('check_run','check_suite','commit_comment','create','delete','deployment','deployment_status','fork','github_app_authorization','gollum','installation','installation_repositories','issue_comment','issues','label','marketplace_purchase','member','membership','milestone','organization','org_block','page_build','project_card','project_column','project','public','pull_request_review_comment','pull_request_review','pull_request','push','repository','repository_vulnerability_alert','release','status','team','team_add','watch')

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
        request_path = self.path
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        payload = self.rfile.read(length)

        log.debug("Request Header: %s" % request_headers)

        http_code = self.verify_secret(config['server']['secret'], payload)

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
    log.info("\n process_webhook_event \n")

    server_config = config['server']
    yml_webhooks = config['webhooks']
    n = 0
    event_match = False
    # get 'X-GitHub-Event' from 'headers', this is the 'Webhook event name'
    webhook_event = headers['X-GitHub-Event']

    # trigger all registered actions for the webhook event
    # check each event listed in yaml
    for hook in yml_webhooks:
        yml_event = hook['event']
        yml_description = hook['description']
        # does the event, received from Github, match a yaml event ?
        if yml_event == webhook_event:
            log.info("Found event in yaml: %s" % yml_event)
            # do we have 'payload_data' to filter on ?
            if hook['payload_attrs']:
                yml_payload_attrs = hook['payload_attrs']
                for data in yml_payload_attrs:
                    log.debug("yml attr data %s: " % data)
                    # does the data from yaml completely match the webhook payload ?
                    for key in data:
                        payload_json = json.loads(payload)
                        if data[key] == payload_json[key]:
                            log.info("event: '%s' has matching data point: '%s' " % (yml_event, key))
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
                     log.debug("Webhook actions found for event '%s': %s " % (hook, actions))

                     if actions and len(actions) > 0:
                         # execute all 'actions' for the event, listed in yaml
                         for action in actions:
                             n += 1
                             log.info("action %s : %s" % (n,action))

                             module_name = action
                             clazz = 'command'
                             module = __import__(module_name)
                             my_class = getattr(module, clazz)
                             instance = my_class(log, server_config, headers, payload )
                             instance.execute()

    return 0


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
    args = parser.parse_args()
    level = args.log_level.upper()

    # setup logger
    init_logger(config['server']['log'], level)

    # start Webhook listener
    main()
