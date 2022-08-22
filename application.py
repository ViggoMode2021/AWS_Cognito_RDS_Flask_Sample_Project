from flask import Flask, render_template, request, flash, session, redirect, url_for
import psycopg2
import psycopg2.extras
import os
import boto3
from dotenv import load_dotenv, find_dotenv
import datetime

application = Flask(__name__)

load_dotenv(find_dotenv())

dotenv_path = os.path.join(os.path.dirname(__file__), ".env_aws_flask_services")
load_dotenv(dotenv_path)

application.secret_key = os.getenv("SECRET_KEY")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

@application.route('/')
def sign_up():
    return render_template("sign_up.html")

@application.route('/sign_up_submit', methods=['POST'])
def sign_up_submit():
    try:
        email_sign_up = request.form.get("email_sign_up")
        password_sign_up = request.form.get("password_sign_up")

        client = boto3.client("cognito-idp", region_name="us-east-1")
        client.sign_up(
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"),
            Username=email_sign_up,
            Password=password_sign_up,
            UserAttributes=[{"Name": "email", "Value": email_sign_up}],
        )

        session['loggedin'] = True

        session['username'] = email_sign_up

        return redirect(url_for('authenticate_page'))
    except:
        return redirect(url_for('authenticate_page'))

@application.route('/authenticate_page', methods=['GET'])
def authenticate_page():
    if 'loggedin' in session:
        return render_template('authenticate.html')

    return redirect(url_for('sign_up'))

@application.route('/authenticate', methods=['POST'])
def authenticate():
    if 'loggedin' in session:
        authentication_code = request.form.get('authentication_code')
        client = boto3.client("cognito-idp", region_name="us-east-1", use_ssl=True)

        client.confirm_sign_up(
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"),
            Username=session['username'],
            ConfirmationCode=authentication_code,
            ForceAliasCreation=False
        )

        flash('You have authenticated!')

        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code)

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute(
            "INSERT INTO username (username, overall_score, account_creation_date) VALUES (%s, %s, %s);",
            (session['username'], 0, date_object))

        conn.commit()

        cursor.close()
        conn.close()

        session.pop('username')

        return redirect(url_for('sign_up'))

    return redirect(url_for('sign_up'))

@application.route('/login_page', methods=['POST', 'GET'])
def login_page():
    return render_template('sign_up.html')

@application.route('/login', methods=['POST', 'GET'])
def login():
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        client = boto3.client("cognito-idp", region_name="us-east-1")

        client.initiate_auth(
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        session['loggedin'] = True

        session['username'] = username

        return redirect(url_for('level_selector'))

    except:
        flash('Username or password incorrect, or user is not in the system.')
        return redirect(url_for('sign_up'))

@application.route('/home', methods=['GET'])
def home():
    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT overall_score FROM users WHERE username = %s;', [session['username']])

        overall_score = cursor.fetchone()

        session['overall_score'] = overall_score[0]

        cursor.close()
        conn.close()

        return render_template('level_selector.html', username=session['username'], overall_score=session['overall_score'])

    return redirect(url_for('login'))

if __name__ == '__main__':
    application.run(debug=True)
