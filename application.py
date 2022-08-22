from flask import Flask, render_template, request, flash, session, redirect, url_for # Backend for application
import psycopg2 # Database adapter for Python to Postgres
import psycopg2.extras
import os
import boto3 # AWS Python SDK
from dotenv import load_dotenv, find_dotenv # Access .env files
import datetime # To record dates and times

application = Flask(__name__)

load_dotenv(find_dotenv())

dotenv_path = os.path.join(os.path.dirname(__file__), ".env_aws_flask_services") # Name of .env file
load_dotenv(dotenv_path)

application.secret_key = os.getenv("SECRET_KEY") # Flask secret key

DB_HOST = os.getenv("DB_HOST") # RDS Database endpoint
DB_NAME = os.getenv("DB_NAME") # RDS Database name
DB_USER = os.getenv("DB_USER") # RDS Database username
DB_PASS = os.getenv("DB_PASS") # RDS Database password

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'), # Access key for IAM user
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY') # Secret access key for IAM user

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST) # Establish connection to Postgres from Flask
cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) # Used to traverse records from the query

@application.route('/')
def sign_up():
    return render_template("sign_up.html") # Landing page

@application.route('/sign_up_submit', methods=['POST']) # Function to sign up
def sign_up_submit():
    try:
        email_sign_up = request.form.get("email_sign_up") # Input box in 'sign_up.html
        password_sign_up = request.form.get("password_sign_up") # Password box in 'sign_up.html

        client = boto3.client("cognito-idp", region_name="us-east-1") # Client for Boto3 Cognito
        client.sign_up(
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"), # Client ID for Cognito User Pool
            Username=email_sign_up,
            Password=password_sign_up,
            UserAttributes=[{"Name": "email", "Value": email_sign_up}], # Attributes sent to User Pool
        )

        session['loggedin'] = True # Establish a session to keep the user logged in and capable of accessing authentication page

        session['username'] = email_sign_up # Establish a username variable to query tables and render a HTML variable

        return redirect(url_for('authenticate_page')) # If initial sign up is successful, send user to the authentication page
    except:
        flash('Username or password incorrect, or user is not in the system.')
        return redirect(url_for('sign_up')) # Return user to sign up page if try block fails. This could be due to user already being in system.

@application.route('/authenticate_page', methods=['GET']) # Route user to authentication page
def authenticate_page():
    if 'loggedin' in session:
        return render_template('authenticate.html')

    return redirect(url_for('sign_up'))

@application.route('/authenticate', methods=['POST']) # Function for user to input authentication code
def authenticate():
    if 'loggedin' in session:
        authentication_code = request.form.get('authentication_code') # Input box on authenticate.html
        client = boto3.client("cognito-idp", region_name="us-east-1", use_ssl=True)

        client.confirm_sign_up( # Confirms user in Cognito user pool if the authentication code is valid
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"),
            Username=session['username'],
            ConfirmationCode=authentication_code,
            ForceAliasCreation=False
        )

        flash('You have authenticated!')

        date = datetime.date.today()

        format_code = '%m-%d-%Y'

        date_object = date.strftime(format_code) # Establish date to input into db

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute(
            "INSERT INTO username (username, overall_score, account_creation_date) VALUES (%s, %s, %s);",
            (session['username'], 0, date_object)) # Insert user, overall score, and registration date into db

        conn.commit() # Commit insert

        cursor.close() # Close cursor
        conn.close() # Close connection

        session.pop('username') # Remove session

        return redirect(url_for('sign_up')) # Return to sign up page

    return redirect(url_for('sign_up'))

@application.route('/login_page', methods=['POST', 'GET']) # Login page
def login_page():
    return render_template('sign_up.html')

@application.route('/login', methods=['POST', 'GET']) # Login function
def login():
    try:
        username = request.form.get('username')
        password = request.form.get('password')

        client = boto3.client("cognito-idp", region_name="us-east-1")

        client.initiate_auth( # Check if user in User Pool
            ClientId=os.getenv("COGNITO_USER_CLIENT_ID"),
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        session['loggedin'] = True

        session['username'] = username

        return redirect(url_for('home')) # Bring user to home page

    except:
        flash('Username or password incorrect, or user is not in the system.')
        return redirect(url_for('sign_up'))

@application.route('/home', methods=['GET']) # Send user to home page
def home():
    if 'loggedin' in session:

        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cursor.execute('SELECT overall_score FROM users WHERE username = %s;', [session['username']]) # Query for overall score

        overall_score = cursor.fetchone() # Query and fetch data

        session['overall_score'] = overall_score[0] # Remove brackets from fetched data

        cursor.close()
        conn.close()

        return render_template('home.html', username=session['username'], overall_score=session['overall_score'])

    return redirect(url_for('login'))

if __name__ == '__main__':
    application.run(debug=True) # Run Flask with the debugger
