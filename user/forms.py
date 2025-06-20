from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField

class SearchForm(FlaskForm):
    course = SelectField('Course')
    semester = SelectField('Semester')
    subject = SelectField('Subject')
    submit = SubmitField('Search')
