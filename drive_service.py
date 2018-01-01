import json
import sys
import uuid
import requests
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_oauthlib.client import OAuth
import msgraph
from drive import FileItem

client_id, client_secret, *_ = open('_PRIVATE.txt').read().split('\n')
if (client_id.startswith('*') and client_id.endswith('*')) or \
    (client_secret.startswith('*') and client_secret.endswith('*')):
    print('MISSING CONFIGURATION: the _PRIVATE.txt file needs to be edited ' + \
        'to add client ID and secret.')
    sys.exit(1)


# Create Flask instance
app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

# since this sample runs locally without HTTPS, disable InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

msgraphapi = oauth.remote_app( \
    'microsoft',
    consumer_key=client_id,
    consumer_secret=client_secret,
    request_token_params={'scope': 'User.Read Mail.Send Files.Read'},
    base_url='https://graph.microsoft.com/v1.0/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
    authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
                             )

@app.route('/')
def index():
    """Handler for home page."""
    return render_template('connect.html')

@app.route('/login')
def login():
    print('*** Login')
    """Handler for login route."""
    guid = uuid.uuid4() # guid used to only accept initiated logins
    session['state'] = guid
    return msgraphapi.authorize(callback=url_for('authorized', _external=True), state=guid)

@app.route('/logout')
def logout():
    """Handler for logout route."""
    session.pop('microsoft_token', None)
    session.pop('state', None)
    return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
    print('*** Authorized')
    """Handler for login/authorized route."""
    response = msgraphapi.authorized_response()

    print('*** Got response')

    if response is None:
        return "Access Denied: Reason={0}\nError={1}".format( \
            request.args['error'], request.args['error_description'])

    # Check response for state
    if str(session['state']) != str(request.args['state']):
        raise Exception('State has been messed with, end authentication')

    print('*** Reset state')
    session['state'] = '' # reset session state to prevent re-use

    # Okay to store this in a local variable, encrypt if it's going to client
    # machine or database. Treat as a password.
    session['microsoft_token'] = (response['access_token'], '')
    # Store the token in another session variable for easy access
    session['access_token'] = response['access_token']
    me_response = msgraphapi.get('me')
    me_data = json.loads(json.dumps(me_response.data))
    username = me_data['displayName']
    email_address = me_data['userPrincipalName']
    session['alias'] = username
    session['userEmailAddress'] = email_address

    return redirect('main')

@app.route('/items')
def get_items():
    print('/items')
    
    url = 'https://graph.microsoft.com/v1.0/me/drive/root/children' 
    _id = '511F789DEE892FBD!47017'           
    url2 = get_url(_id)    
    items = get_drive_items(session['access_token'], url2)

    return jsonify({'value' : [x.serialize() for x in items], 'code' : 200})

def get_drive_items(access_token, drive_url):
    print('get_drive_items')

    headers = {'User-Agent' : 'python_tutorial/1.0',
               'Authorization' : 'Bearer {0}'.format(access_token),
               'Accept' : 'application/json',
               'Content-Type' : 'application/json'}

    files = []
    try:
        response = requests.get(url=drive_url, headers=headers)
        print(response.status_code)
        print('\r\n***Response: ')

        data = response.json()
        for item in data['value']:
            print('\n\n{}'.format(item))
            #tags = item['parentReference']['name']
            tags = get_tags(item['parentReference']['path'])
            if 'file' in item:
                files.append(
                    FileItem(
                        item['id'],
                        item['name'], 
                        item['createdBy']['user']['displayName'],
                        item['createdDateTime'], 
                        'summary here',
                        item['file']['mimeType'],
                        [tags]))
            else:
                _id = item['id']
                _files = get_drive_items(access_token, get_url(_id))
                for _f in _files:
                    files.append(_f)

        return files


    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)


# If library is having trouble with refresh, uncomment below and implement
# refresh handler see https://github.com/lepture/flask-oauthlib/issues/160 for
# instructions on how to do this. Implements refresh token logic.
# @app.route('/refresh', methods=['POST'])
# def refresh():
@msgraphapi.tokengetter
def get_token():
    """Return the Oauth token."""
    return session.get('microsoft_token')

def get_url(_id):
    return 'https://graph.microsoft.com/v1.0/me/drive/items/{}/children'.format(_id)

def get_tags(path):
    tags = []

    found = False
    for t in path.split('/'):
        if found:
            tags.append(t)

        if ':' in t:
            found = True

    return tags