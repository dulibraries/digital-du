"""Port of Aristotle for use as a Digital Archives of Colorado College 
front-end"""
__author__ = "Jeremy Nelson"

from flask import Flask

app = Flask(__name__,  instance_relative_config=True)
app.config.from_pyfile('config.py')

from .views import *
from .filters import *
