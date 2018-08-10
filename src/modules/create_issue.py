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
        '''Create an issue on github.com using the given parameters.'''
        global log
        log.info("executing 'create_issue' module")

        github_api_url = self.server_config['github_api']
        repo_name = 'issue-repo'
        repo_owner = self.server_config['organization']
        repo_full_name = json.loads(self.payload)['repository']['full_name']
        # GitHub API URL
        url = '%s/repos/%s/%s/issues' % (github_api_url, repo_owner, repo_name)
        headers = {'x-webhook-action': 'create_issue'}

        # prepare issue payload
        title = "Repository was removed"
        body = "@jefeish The repository "+ repo_full_name +" was deleted"
        assignees = ["jefeish"]
        labels = ["bug"]
        data = {
                "title": title,
                 "body": body,
                 "assignees": assignees,
                 "labels": labels
            }

        # create an issue in the repository
        if 'proxies' in self.server_config:
            log.debug(self.server_config['proxies'])
            log.info("making the GitHub API call (with proxy)")
            r = requests.post(url, proxies= self.server_config['proxies'], auth=(repo_owner, self.server_config['token']), data=json.dumps(data), headers=headers)
        else:
            log.debug("no proxies")
            log.info("making the GitHub API call (without proxy)")
            r = requests.post(url, auth=(repo_owner, self.server_config['token']), data=json.dumps(data), headers=headers)

        if r.status_code == 201:
            log.info("Created Issue '%s' in repository '%s'" % (title, repo_name))
            log.debug("Response: %s" % r.content)
        else:
            log.error("Failed to create Issue: '%s'" % title)
            log.error("Response: %s" % r.content)
            log.error("Request Data: %s" % data)


# For testing
if __name__ == "__main__":

    global log
    server_config = {
            'token': '...',
            'github_api': 'https://api.github.com',
            'owner': 'jefeish',
            'organization': 'jchallenge1',
        }

    payload = '{"repository": {"full_name": "test"}}'

    log = logging.getLogger(__name__)
    hdlr = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    log.setLevel(logging.DEBUG)
    c = command(log, server_config, '', payload )
    c.execute()
