## python 3
# pip install plexapi
# pip install xmltodict

import requests
import http.client
import ssl
import xmltodict
import json
import urllib
import sys
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from plexapi.myplex import MyPlexDevice
from uuid import uuid3, NAMESPACE_URL
from config import ppTagConfig

class userData(object):
    """a simple class that holds some user data"""
    id = ""
    uuid = ""
    title = ""
    pin = ""
    token = ""

    def __init__(self, id, uuid, title, pin):
        self.id = id
        self.uuid = uuid
        self.title = title
        self.pin = pin

    def setToken(self, token):
        self.token = token

class plexUsers():
    """A class to get user data (token, library id) for plex"""

    def fetchPlexApi(self, path='', method='GET', getFormPlextv=False, token=ppTagConfig.PLEX_TOKEN, params=None):
        """a helper function that fetches data from and put data to the plex server"""
        headers = {'X-Plex-Token': token, 'Accept': 'application/json'}
        # headers = {'X-Plex-Token': token}
        if getFormPlextv:
            url = 'plex.tv'
            connection = http.client.HTTPSConnection(url)
        else:
            url = ppTagConfig.PLEX_URL.rstrip('/').replace('http://','').replace('https://','')
            connection = http.client.HTTPSConnection(url, context=ssl._create_unverified_context())

        try:
            if method.upper() == 'GET':
                pass
            elif method.upper() == 'POST':
                headers.update({'Content-type': 'application/x-www-form-urlencoded'})
                pass
            elif method.upper() == 'PUT':
                pass
            elif method.upper() == 'DELETE':
                pass
            else:
                print("Invalid request method provided: {method}".format(method=method))
                connection.close()
                return

            connection.request(method.upper(), path , params, headers)
            response = connection.getresponse()
            r = response.read()
            contentType = response.getheader('Content-Type')
            status = response.status
            connection.close()

            if response and len(r):
                if 'application/json' in contentType:
                    return json.loads(r)
                elif 'application/xml' in contentType:
                    return xmltodict.parse(r)
                else:
                    return r
            else:
                return r

        except Exception as e:
            connection.close()
            print("Error fetching from Plex API: {err}".format(err=e))

    def getAccessTokenForUser(self):
        for user in self.users:
            params = urllib.parse.urlencode({'pin': user.pin, 'X-Plex-Client-Identifier': self.clientId})
            data = self.fetchPlexApi('/api/v2/home/users/{uuid}/switch'.format(uuid=user.uuid), 'POST', True, ppTagConfig.PLEX_TOKEN, params)
            if 'authToken' in data:
                authToken = data['authToken']
                data = self.fetchPlexApi('/api/resources?includeHttps=1&includeRelay=1&X-Plex-Client-Identifier={clientid}'.format(clientid=self.clientId), 'GET', True, authToken)
                for device in data['MediaContainer']['Device']:
                    if isinstance(device, dict):
                        if device.get('@provides') == 'server' and device.get('@name') == ppTagConfig.SERVERNAME:
                            self.serverId = device.get('@clientIdentifier')
                            user.setToken(device.get('@accessToken'))
                            break

    def __init__(self):
        ## some initial tests
        if len(ppTagConfig.PLEX_TOKEN) == 0:
            # get a token
            try:
                account = MyPlexAccount(ppTagConfig.PLEX_LOGIN, ppTagConfig.PLEX_PASS)
            except Exception as e:
                raise("Error fetching from Plex API: {err}".format(err=e))
            # print the Token and message to enter it here
            print('use this token')
            print (account.authenticationToken)
            print('and put it into the file config.py after PLEX_TOKEN: ')
            raise

        # some lists for data
        self.users = list()
        self.photoSections = list()
        self.serverId = ''

        # creating the client id
        self.clientId = uuid3(NAMESPACE_URL, "pptag").hex

        session = requests.Session()
        session.verify = False
        self.plex = PlexServer(ppTagConfig.PLEX_URL, ppTagConfig.PLEX_TOKEN,session)


        apiUsers = self.fetchPlexApi("/api/home/users","GET",True)

        userList = apiUsers['MediaContainer']['User']

        if isinstance(userList, list):
            users = userList
        else:
            users = list()
            users.append(userList)

        for user in users:
            if isinstance(user, dict):
                if user['@title'] in ppTagConfig.USERDATA.keys():
                    pin = ppTagConfig.USERDATA.get(user['@title'])
                    u = userData(user['@id'],user['@uuid'],user['@title'], pin)
                    self.users.append(u)

        self.getAccessTokenForUser()

        for user in self.users:
            if user.token == '':
                print('no token found for user {user}'.format(user=user.title))
                self.users.remove(user)
            # else:
            #     print(user.title)
            #     print(user.token)

        # print (plex.machineIdentifier)
        for section in self.plex.library.sections():
            if section.type == 'photo':
                self.photoSections.append(section.key)

        # for playlist in self.plex.playlists():
        #     if playlist.isPhoto:
        #         print(playlist.smart)
