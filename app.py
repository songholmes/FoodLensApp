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

# from dotenv import load_dotenv
#
# load_dotenv()  # Load environment variables from .env file

def query_email_to_list():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('foodlens-gmail-whitelist-dev')

    response = table.scan()

    items = response['Items']
    user_id_list = [item['user_id'] for item in items]

    return user_id_list

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
    username = email.split("@")[0] if email else None

    if not email:
        return redirect("/login")

    if request.method == "POST":
        answer = request.form.get("answer")

        # Write to DynamoDB whitelist
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('foodlens-gmail-whitelist-dev')
        table.put_item(Item={"user_id": email,
                             'timestamp': str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+'|'+answer})
        return redirect("/")

    return render_template_string("""
    <h3>Welcome {{ username }}, how did you find this website?</h3>
    <form method="POST">
        Your Answer: <input type="text" name="answer" />
        <input type="submit" />
    </form>
""")
