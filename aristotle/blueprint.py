__author__ = "Jeremy Nelson"

from flask import Blueprint

aristotle = Blueprint(
    "aristotle",
    __name__,
    template_folder="templates",
    static_folder="static")

from . import views
from . import filters
