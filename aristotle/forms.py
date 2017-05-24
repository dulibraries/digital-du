from flask_wtf import FlaskForm as Form
from wtforms import SelectField, StringField

SEARCH_TYPES = (
    ("kw", "Keyword"),
    ("creator", "Creator"),
    ("title", "Title"),
    ("subject", "Subject"),
    ("number", "Number")
)
    

class SimpleSearch(Form):
    mode = SelectField("Mode",
        choices=SEARCH_TYPES)
    q = StringField("Search")
