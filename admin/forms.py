from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from wtforms import FieldList, FormField, MultipleFileField
from wtforms import SelectMultipleField, widgets

class YouTubeLinkForm(FlaskForm):
    youtube_link = StringField('YouTube Link')

class MaterialForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    course = StringField('Course', validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired()])
    semester = SelectField('Semester', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6')], validators=[DataRequired()])
    
    # Changing material_type to SelectMultipleField to use checkboxes
    material_type = SelectMultipleField(
        'Material Type',
        choices=[('Notes', 'Notes'), ('Previous Years Papers', 'Previous Years Papers'), ('YouTube Playlist', 'YouTube Playlist')],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    
    description = TextAreaField('Description')
    files = MultipleFileField('Upload Files')  # Accept multiple files
    youtube_links = FieldList(FormField(YouTubeLinkForm), min_entries=1)
    submit = SubmitField('Upload')

