import os
import json
import requests
import yaml
from requests.packages.urllib3.exceptions import InsecurePlatformWarning

requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)

class ApiReq(object):

    DEFAULT_HEADERS = {
        'Accepts': 'application/json',
        'Content-type': 'application/json'
    }

    def __init__(self, user, api_key, identity_url, datacenter, debug=False):

        self.identity_url = identity_url
        self.user = user
        self.api_key = api_key
        self.datacenter = datacenter

        self.token = None
        self.endpoints = None

        self.debug = debug

        if not self.identity_url.endswith('tokens'):
            self.identity_url = os.path.join(self.identity_url, 'tokens')

        self.auth()

    def auth(self):
        """
        Authenticate, returns the authentication token
        """
        body = {
            'auth': {
                'RAX-KSKEY:apiKeyCredentials': {
                    'username': self.user,
                    'apiKey': self.api_key
                }
            }
        }

        auth = requests.post(self.identity_url,
                             data=json.dumps(body),
                             headers=self.DEFAULT_HEADERS).json()

        self.token = auth['access']['token']['id']
        self.endpoints = auth['access']['serviceCatalog']

        # print json.dumps(auth, sort_keys=True, indent=4)

    def find_endpoint(self, type):
        """
        Lookup an endpoint
        :param type: the name of the endpoint
        :return: an endpoint url
        """
        for service in self.endpoints:
            if service['name'] == type:
                for endpoint in service['endpoints']:
                    if endpoint['region'] == self.datacenter:
                        return endpoint['publicURL']
        raise Exception('Could not find endpoint %s in %s' % (type, self.datacenter))

    def api_req(self, http_type, url, endpoint_type, params=None):
        """
        General purpose api request
        :param http_type: POST, PUT, GET, or DELETE
        :param url: the url for the command
        :param params: any arguments needed for the command
        :param endpoint_type: the name of the endpoint.  e.g. cloudServersOpenStack or cloudDatabases
        :return: the return value of the request
        """

        endpoint = self.find_endpoint(endpoint_type)
        if url[0] != '/':
            url = '/' + url
        url = '{b}{p}'.format(b=endpoint,
                              p=url)
        if self.debug:
            if params is None:
                print http_type + ' ' + url
            else:
                print http_type + ' ' + url + ' -- ' + str(params)

        headers = self.DEFAULT_HEADERS
        headers['X-Auth-Token'] = self.token

        http_type = http_type.upper()
        if http_type in ('POST', 'PUT'):
            if not params:
                params = {}
            params = json.dumps(params)
            rep = requests.post(url, data=params, headers=headers)
        elif http_type == 'PATCH':
            if not params:
                params = {}
            params = json.dumps(params)
            rep = requests.patch(url, data=params, headers=headers)
        elif http_type == 'GET':
            if not params:
                params = ''
            rep = requests.get(url, params=params, headers=headers)
        elif http_type == 'DELETE':
            rep = requests.delete(url, headers=headers)
        else:
            print 'Unknown request type!'
            exit()

        if self.debug:
            print rep

        try:
            return rep.json()
        except Exception as e:
            return None
            # print 'Invalid json response'
            # print e

    def image_list(self):
        url = 'images/detail'
        return self.api_req('GET', url, 'cloudServersOpenStack')

    def flavor_list(self):
        url = 'flavors/detail'
        return self.api_req('GET', url, 'cloudServersOpenStack')

    def boot(self, name, image, flavor):
        url = 'servers'
        params = {'server': {'name': name, 'imageRef': image, 'flavorRef': flavor}}
        return self.api_req('POST', url, 'cloudServersOpenStack', params=params)

    def show_server(self, server_id):
        url = 'servers/' + server_id
        return self.api_req('GET', url, 'cloudServersOpenStack')

    def delete_server(self, server_id):
        url = 'servers/' + server_id
        return self.api_req('DELETE', url, 'cloudServersOpenStack')

    def build_mysql(self, flavor, size, name, database_name, user, password, version, configuration=None):
        url = 'instances'
        params = {
            'instance': {
                'databases': [
                    {
                        'name': database_name
                    }
                ],
                'volume': {
                    'size': size
                },
                'flavorRef': flavor,
                'name': name,
                'users': [
                    {
                        'databases': [
                            {
                                'name': database_name
                            }
                        ],
                        'name': user,
                        'password': password
                    }
                ],
                'datastore': {
                    'type': 'mysql',
                    'version': version
                }

            }
        }
        if configuration is not None:
            params['instance']['configuration'] = configuration
        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def build_ha_mysql(self, flavor, size, name, database_name, user, password, version, nodes):
        url = 'ha'
        params = {
            'ha': {
                'name': name,
                'acls': [
                    {
                        'address': '0.0.0.0/0'
                    }
                ],
                'datastore': {
                    'type': 'mysql',
                    'version': version
                },
                'replica_source': [
                    {
                        'volume': {'size': size},
                        'flavorRef': flavor,
                        'name': name + '_0'
                    }
                ],
                'replicas': [],
                'databases': [
                    {
                        'name': database_name
                    }
                ],

                'users': [
                    {
                        'databases': [
                            {
                                'name': database_name
                            }
                        ],
                        'name': user,
                        'password': password
                    }
                ]

            }
        }

        for node in range(1, nodes):

            params['ha']['replicas'].append({
                'volume': {'size': size},
                'flavorRef': flavor,
                'name': name + '_' + str(node)
            })


        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def attach_ha_mysql_configuration(self, instance_id, configuraiton):
        url = 'ha/' + instance_id
        params = {
            'ha_instance': {
                'configuration': configuraiton
            }
        }
        self.api_req('PATCH', url, 'cloudDatabases', params=params)

    def build_redis(self, flavor, name, version):
        url = 'instances'
        params = {
            'instance': {
                'flavorRef': flavor,
                'name': name,
                'datastore': {
                    'type': 'redis',
                    'version': version
                }
            }
        }
        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def build_ha_redis(self, flavor, name, version, nodes):
        url = 'ha_instances'
        params = {
            'ha_instance': {
                'name': name,
                'flavor': flavor,
                'nodes': nodes,
                'datastore': {
                    'type': 'redis',
                    'version': version
                },
                'acls': [
                    {
                        'address': '0.0.0.0/0'
                    }
                ]
            }
        }

        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def create_mysql_database(self, datastore_id, user):
        url = 'instances/' + datastore_id + '/databases'
        params = {
            'databases': [{'name': user}]
        }
        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def create_mysql_user(self, datastore_id, user, password, database_name):
        url = 'instances/' + datastore_id + '/users'
        params = {
            'users': [
                {
                    'databases': [{'name': database_name}],
                    'name': user,
                    'password': password
                }
            ]
        }
        return self.api_req('POST', url, 'cloudDatabases', params=params)

    def show_database(self, database_id):
        url = 'instances/' + database_id
        return self.api_req('GET', url, 'cloudDatabases')

    def show_ha_database(self, database_id):
        url = 'ha_instances/' + database_id
        return self.api_req('GET', url, 'cloudDatabases')

    def delete_database(self, server_id):
        url = 'instances/' + server_id
        return self.api_req('DELETE', url, 'cloudDatabases')

    def delete_ha_database(self, server_id):
        url = 'ha_instances/' + server_id
        return self.api_req('DELETE', url, 'cloudDatabases')
