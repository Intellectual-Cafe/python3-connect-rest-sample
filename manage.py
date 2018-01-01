"""Main program for Microsoft Graph Connect sample.
To run the app, execute the command "python manage.py runserver" and then
open a browser and go to http://localhost:5000/
"""
import flask_script
import connectsample
import drive_service

#MANAGER = flask_script.Manager(connectsample.app)
MANAGER = flask_script.Manager(drive_service.app)
MANAGER.add_command('runserver', flask_script.Server(host='localhost'))
MANAGER.run()
