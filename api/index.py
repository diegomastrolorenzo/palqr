import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, template_folder='../templates')

# Vercel provides POSTGRES_URL.
# SQLAlchemy requires the prefix 'postgresql://' instead of 'postgres://'
db_url = os.environ.get('POSTGRES_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class DataEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/add', methods=['POST'])
def add_data():
    data = request.json
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content"}), 400

    entry = DataEntry(content=data['content'])
    db.session.add(entry)
    db.session.commit()
    return jsonify({"message": "Success"}), 201


@app.route('/view', methods=['GET'])
def view_data():
    entries = DataEntry.query.all()
    return jsonify([{"id": e.id, "content": e.content} for e in entries])


app_handle = app