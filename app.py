# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import os
import dash_bootstrap_components as dbc
from dash import Dash, html, Input, Output, dcc, no_update
from dash_auth import OIDCAuth
from flask import session, redirect, url_for, request, render_template, render_template_string
import boto3
from datetime import datetime
import sqlite3 as sl
import pandas as pd

# from dotenv import load_dotenv
#
# load_dotenv()  # Load environment variables from .env file

WHITE_LIST_DB_PATH = r'data\foodlens_gmail_whitelist_dev.db'


def create_initial_whitelist_db():
    con = sl.connect(WHITE_LIST_DB_PATH)
    cur = con.cursor()

    # Email White List Table
    cur.execute("""
    CREATE TABLE foodlens_gmail_whitelist_dev (
        user_id TEXT,
        timestamp TEXT
    )
    """)

    res = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='foodlens_gmail_whitelist_dev'")
    assert res.fetchone() is not None, "foodlens_gmail_whitelist_dev Table is not created correctly"

    con.commit()


def query_email_to_list():
    con = sl.connect(WHITE_LIST_DB_PATH)

    response = pd.read_sql(""" SELECT * FROM foodlens_gmail_whitelist_dev """, con)
    user_id_list = list(response['user_id'].unique())

    return user_id_list

if not os.path.exists(WHITE_LIST_DB_PATH):
    print(f'Create new db file in {WHITE_LIST_DB_PATH}')
    create_initial_whitelist_db()

FA = "https://use.fontawesome.com/releases/v5.12.1/css/all.css"

app = Dash(__name__,
                external_stylesheets=[dbc.themes.BOOTSTRAP, FA],
                suppress_callback_exceptions=True)

app.title = 'Food-Lens-App'
server = app.server
# Secret key for session management
app.server.secret_key = os.urandom(24)

# Configure OIDC Authentication
auth = OIDCAuth(
    app,
    secret_key=app.server.secret_key,
    idp_selection_route="/login",
    # If you want a different URL prefix for the auth routes, specify here, e.g. url_prefix="/auth"
)

## if should be mentioned that in OIDCAuth.login_request, there is logic:
# 'if len(self.oauth._registry) == 1: idp = next(iter(self.oauth._clients))', which means if only one provider is
# set, then will skip the login selection part

# Provider 1: Google
google_client_id = os.getenv("GOOGLE_CLIENT_ID")  # Reads from system environment variables
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
# Register Google as the Identity Provider (IdP)
auth.register_provider(
    idp_name="Google",
    client_id=google_client_id,  # Replace with your Google Client ID
    client_secret=google_client_secret,  # Replace with your Google Client Secret
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    authorize_params={"scope": "openid email profile"},
    token_endpoint_auth_method="client_secret_post",
)

@app.server.route("/login", methods=["GET", "POST"])
def login_handler():
    """Handles the /login route for IDP selection."""
    if request.method == "POST":
        idp = request.form.get("idp")
    else:
        idp = request.args.get("idp")

    if idp is not None:
        # This calls the OIDCAuth-generated endpoint named "oidc_login"
        return redirect(url_for("oidc_login", idp=idp))

    return render_template('oidc_login_page.html')


# -------------------------------------------------
# Callback to Enforce Whitelist Check
# -------------------------------------------------
def register_auth_app(app):
    @app.callback(
        Output("url", "pathname"),
        Output("username", "children"),
        Input("placeholder", "children")
    )
    def check_user(_):
        user_info = session.get("user")
        email = user_info.get("email") if user_info else None

        if not email:
            return "/login", no_update

        whitelist = set(query_email_to_list())
        # whitelist.remove("songyangholmes@gmail.com")

        if email in whitelist:
            return no_update, email.split('@')[0]
        else:
            # Redirect to password challenge if not whitelisted
            return "/password_challenge", no_update


@app.server.route("/password_challenge", methods=["GET", "POST"])
def password_challenge():
    user_info = session.get("user")
    email = user_info.get("email") if user_info else None

    if not email:
        return redirect("/login")

    if request.method == "POST":
        answer = request.form.get("answer")

        # Write to DynamoDB whitelist
        con = sl.connect(WHITE_LIST_DB_PATH)
        cur = con.cursor()
        timestamped_answer = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "|" + answer
        cur.execute("INSERT INTO foodlens_gmail_whitelist_dev VALUES (?, ?)",
                    (email, timestamped_answer))
        con.commit()
        return redirect("/")

    return render_template_string("""
    <h3>Welcome {{ username }}, how did you find this website?</h3>
    <form method="POST">
        Your Answer: <input type="text" name="answer" />
        <input type="submit" />
    </form>
""")
