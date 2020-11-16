from flask_wtf import Form
from wtforms import StringField, SubmitField, validators, PasswordField,ValidationError
from wtforms.fields.html5 import EmailField
from model import UserReister

class FormRegister(Form):
    """依照Model來建置相對應的Form

    password2: 用來確認兩次的密碼輸入相同
    """
    username = StringField('會員名字', validators=[
        validators.DataRequired(),
        validators.Length(10, 30)
    ])
    email = EmailField('電子信箱', validators=[
        validators.DataRequired(),
        validators.Length(1, 50),
        validators.Email()
    ])
    password = PasswordField('密碼', validators=[
        validators.DataRequired(),
        validators.Length(5, 10),
        validators.EqualTo('password2', message='PASSWORD NEED MATCH')
    ])
    password2 = PasswordField('再次確認密碼', validators=[
        validators.DataRequired()
    ])
    submit = SubmitField('確認送出')

    def validate_email(self, field):
        if UserReister.query.filter_by(email=field.data).first():
            raise ValidationError('電子信箱已經有人註冊')

    def validate_username(self, field):
        if UserReister.query.filter_by(username=field.data).first():
            raise ValidationError('UserName already register by somebody')