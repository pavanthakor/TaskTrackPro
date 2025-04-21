from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, TextAreaField, FloatField, FileField, BooleanField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange
from flask_wtf.file import FileRequired, FileAllowed

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class SportForm(FlaskForm):
    name = StringField('Sport Name', validators=[DataRequired(), Length(min=2, max=50)])
    submit = SubmitField('Add Sport')

class ProfileForm(FlaskForm):
    age = IntegerField('Age', validators=[Optional(), NumberRange(min=5, max=100)])
    height = FloatField('Height (cm)', validators=[Optional(), NumberRange(min=50, max=250)])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=20, max=250)])
    primary_sport = SelectField('Primary Sport', coerce=int, validators=[Optional()])
    experience_level = SelectField('Experience Level', 
                                  choices=[('', 'Select...'), 
                                           ('Beginner', 'Beginner'), 
                                           ('Intermediate', 'Intermediate'), 
                                           ('Advanced', 'Advanced')],
                                  validators=[Optional()])
    submit = SubmitField('Update Profile')

class TrainingLogForm(FlaskForm):
    sport = SelectField('Sport', coerce=int, validators=[DataRequired()])
    date = StringField('Date', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=1, max=1440)])
    intensity = SelectField('Intensity (1-10)', choices=[(str(i), str(i)) for i in range(1, 11)], validators=[DataRequired()])
    symptoms = TextAreaField('Any Pain or Symptoms?', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Training Log')

class VideoUploadForm(FlaskForm):
    sport = SelectField('Sport', coerce=int, validators=[DataRequired()])
    video = FileField('Video File', validators=[
        FileRequired(),
        FileAllowed(['mp4', 'mov', 'avi', 'webm'], 'Videos only!')
    ])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Upload for Analysis')

class ProgressForm(FlaskForm):
    sport = SelectField('Sport', coerce=int, validators=[DataRequired()])
    metric_name = SelectField('Metric', choices=[
        ('Speed', 'Speed'),
        ('Accuracy', 'Accuracy'),
        ('Endurance', 'Endurance'),
        ('Strength', 'Strength'),
        ('Flexibility', 'Flexibility'),
        ('Technique', 'Technique')
    ], validators=[DataRequired()])
    metric_value = FloatField('Value', validators=[DataRequired(), NumberRange(min=0)])
    unit = SelectField('Unit', choices=[
        ('km/h', 'km/h'),
        ('%', 'Percentage'),
        ('minutes', 'Minutes'),
        ('kg', 'Kilograms'),
        ('cm', 'Centimeters'),
        ('points', 'Points')
    ], validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Progress')
