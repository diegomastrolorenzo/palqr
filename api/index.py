import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Use the exact variable name you have in Vercel
raw_uri = os.environ.get('SUPABASE_POSTGRES_URL')

if raw_uri:
    # SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
    if raw_uri.startswith("postgres://"):
        uri = raw_uri.replace("postgres://", "postgresql://", 1)
    else:
        uri = raw_uri

    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    # This fallback prevents the 500 error during Vercel's build/import phase
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    print("WARNING: SUPABASE_POSTGRES_URL not found!")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Now initialize the DB
db = SQLAlchemy(app)


# Your routes go here...
@app.route('/')
def home():
    return "PalQR API is running and connected to Supabase!"