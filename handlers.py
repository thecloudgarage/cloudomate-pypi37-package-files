#!/usr/bin/env python

import logging
import http.client
import json
import crypt
import base64
import difflib

from passlib.apache import HtpasswdFile
from tornado import gen
from tornado.web import RequestHandler, HTTPError, asynchronous

from cloudomate.config import config
from cloudomate.scripts import create_collection
from cloudomate.util import route

log = logging.getLogger(__name__)


class BaseHandler(RequestHandler):
    """ Contains helper methods for all request handlers """

    def prepare(self):
        self.handle_params()
        self.handle_auth()

    def handle_params(self):
        """ automatically parse the json body of the request """

        self.params = {}
        content_type = self.request.headers.get("Content-Type", 'application/json')

        if (content_type.startswith("application/json")) or (config['force_json']):
            if self.request.body in [None, ""]:
                return

            self.params = json.loads(self.request.body)
        else:
            # we only handle json, and say so
            raise HTTPError(400, "This application only support json, please set the http header Content-Type to application/json")

    def handle_auth(self):
        """ authenticate the user """

        # no passwords set, so they're good to go
        if config['passfile'] == None:
            return

        # grab the auth header, returning a demand for the auth if needed
        auth_header = self.request.headers.get('Authorization')
        if (auth_header is None) or (not auth_header.startswith('Basic ')):
            self.auth_challenge()
            return

        # decode the username and password
        auth_decoded = base64.decodestring(auth_header[6:])
        username, password = auth_decoded.split(':', 2)

        if not self.is_user_authenticated(username, password):
            self.auth_challenge()
            return

    def is_user_authenticated(self, username, password):
        passfile = HtpasswdFile(config['passfile'])

        # is the user in the password file?
        if not username in passfile.users():
            return False

        return passfile.check_password(username, password)

    def auth_challenge(self):
        """ return the standard basic auth challenge """

        self.set_header("WWW-Authenticate", "Basic realm=cloudomate")
        self.set_status(401)
        self.finish()

    def write(self, chunk):
        """ if we get a dict, automatically change it to json and set the content-type """

        if isinstance(chunk, dict):
            chunk = str(chunk)
            chunk = chunk.replace("b'", '"')
            chunk = chunk.replace("'", '"')
            chunk = json.dumps(chunk)
            chunk = json.loads(chunk.replace("\'", '"'))
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        super(BaseHandler, self).write(chunk)

    def write_error(self, status_code, **kwargs):
        """ return an exception as an error json dict """

        if kwargs['exc_info'] and hasattr(kwargs['exc_info'][1], 'log_message'):
            message = kwargs['exc_info'][1].log_message
        else:
            # TODO: What should go here?
            message = ''

        self.write({
            'error': {
                'code': status_code,
                'type': http.client.responses[status_code],
                'message': message
            }
        })


@route(r"/script_names/?")
class ScriptNamesCollectionHandler(BaseHandler):

    def get(self):
        """ get the requirements for all of the scripts """

        tags = {'tags': [], 'not_tags': [], 'any_tags': []}

        for tag_arg in ['tags', 'not_tags', 'any_tags']:
            try:
                tags[tag_arg] = self.get_arguments(tag_arg)[0].split(',')
                break
            except IndexError:
                continue

        self.finish({'script_names': self.settings['scripts'].name(tags)})


@route(r"/scripts/?")
class ScriptCollectionHandler(BaseHandler):

    def get(self):
        """ get the requirements for all of the scripts """

        tags = {'tags': [], 'not_tags': [], 'any_tags': []}

        for tag_arg in ['tags', 'not_tags', 'any_tags']:
            try:
                tags[tag_arg] = self.get_arguments(tag_arg)[0].split(',')
                break
            except IndexError:
                continue

        self.finish({'scripts': self.settings['scripts'].metadata(tags)})


@route(r"/scripts/([\w\-]+)/?")
class ScriptDetailsHandler(BaseHandler):

    def options(self, script_name):
        """ get the requirements for this script """

        script = self.get_script(script_name, 'options')
        self.finish({'script': script.metadata()})

    @asynchronous
    @gen.engine
    def get(self, script_name):
        """ run the script """

        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'get')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })

    @asynchronous
    @gen.engine
    def delete(self, script_name):
        """ run the script """

        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'delete')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })

    @asynchronous
    @gen.engine
    def put(self, script_name):
        """ run the script """

        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'put')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode,
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })

    @asynchronous
    @gen.engine
    def post(self, script_name):
        """ run the script """

        if config['force_json']:
            self.set_header("Content-Type", "application/json; charset=UTF-8")

        script = self.get_script(script_name, 'post')

        if script.output == 'combined':
            retcode, stdout = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })
        else:
            retcode, stdout, stderr = yield gen.Task(script.execute, self.params)
            self.finish({
                "stdout": stdout,
                "stderr": stderr,
                "return_values": self.find_return_values(stdout),
                "retcode": retcode
            })

    def get_script(self, script_name, http_method):
        script = self.settings['scripts'].get(script_name, None)

        if script is None:
            raise HTTPError(404, "Script with name '{0}' not found".format(script_name))

        if http_method == 'options':
            return script

        if script.http_method != http_method:
            raise HTTPError(405, "Wrong HTTP method for script '{0}'. Use '{1}'".format(script_name, script.http_method.upper()))

        return script

    def find_return_values(self, output):
        """ parse output array for return values """
        return_values = {}
        for line in output:
            lineone = line.decode()
            if lineone.startswith('cloudomatethecloudgarage_return_value'):
                temp = lineone.replace("cloudomatethecloudgarage_return_value","").strip()
                key, value = [item.strip() for item in temp.split('=')]
                return_values[key] = value

        return return_values


@route(r"/reload/?")
class ReloadHandler(BaseHandler):

    def post(self):
        """ reload the scripts from the script directory """
        self.settings['scripts'] = create_collection(config['directory'])
        self.finish({"status": "ok"})
