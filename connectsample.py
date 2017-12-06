# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
"""Main program for Microsoft Graph API Connect demo."""
import json
import sys
import uuid

# un-comment these lines to suppress the HTTP status messages sent to the console
#import logging
#logging.getLogger('werkzeug').setLevel(logging.ERROR)

import requests
from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauthlib.client import OAuth
import msgraph

# read private credentials from text file
client_id, client_secret, *_ = open('_PRIVATE.txt').read().split('\n')
if (client_id.startswith('*') and client_id.endswith('*')) or \
    (client_secret.startswith('*') and client_secret.endswith('*')):
    print('MISSING CONFIGURATION: the _PRIVATE.txt file needs to be edited ' + \
        'to add client ID and secret.')
    sys.exit(1)

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

@app.route('/main')
def main():
    """Handler for main route."""
    if session['alias']:
        username = session['alias']
        email_address = session['userEmailAddress']
        return render_template('main.html', name=username, emailAddress=email_address)
    else:
        return render_template('main.html')

@app.route('/send_mail')
def send_mail():
    """Handler for send_mail route."""
    email_address = request.args.get('emailAddress') # get email address from the form
    response = call_sendmail_endpoint(session['access_token'], session['alias'], email_address)
    if response == 'SUCCESS':
        show_success = 'true'
        show_error = 'false'
    else:
        print(response)
        show_success = 'false'
        show_error = 'true'

    session['pageRefresh'] = 'false'
    return render_template('main.html', name=session['alias'],
                           emailAddress=email_address, showSuccess=show_success,
                           showError=show_error)

@app.route('/get_folders')
def get_folders():
    print('get_folders')
    email_address = 'dries.cronje@outlook.com'
    
    data = get_drive_items(session['access_token'])

    if data:
        show_success = 'true'
        show_error = 'false'
    else:
        show_success = 'false'
        show_error = 'true'

    session['pageRefresh'] = 'false'
    return render_template('main.html', name=session['alias'],
                           emailAddress=email_address, showSuccess=show_success,
                           showError=show_error)

def get_drive_items(access_token):
    print('get_drive')

    url = 'https://graph.microsoft.com/v1.0/me/drive/root/children'            

    headers = {'User-Agent' : 'python_tutorial/1.0',
               'Authorization' : 'Bearer {0}'.format(access_token),
               'Accept' : 'application/json',
               'Content-Type' : 'application/json'}
    #headers = {'Authorization' : 'Bearer {0}'.format(access_token),
    #           'Accept' : 'application/json'}

    files = []
    folders = []
    try:
        response = requests.get(url=url, headers=headers)
        print('***Status: ')
        print(response.status_code)
        print('\r\n***Response: ')
        #print(response.json())

        data = response.json()
        for item in data['value']:
            print('\r\n**** ITEM ****\r\n')
            print(item['name'])
            print(item['parentReference']['path'])
            print(item['webUrl'])
            if 'file' in item:
                print(item['file']['mimeType'])
            else:
                print('FOLDER')

        return data['value']


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
