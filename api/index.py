import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

raw_uri = os.environ.get('SUPABASE_POSTGRES_URL')

if raw_uri:
    # 1. Clean whitespace
    uri = raw_uri.strip()

    # 2. FORCE REMOVE the "supa=" part if it exists
    if "&supa=" in uri:
        uri = uri.split("&supa=")[0]

    # 3. Ensure SQLAlchemy-friendly prefix
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- MODELS ---
class Patient(db.Model):
    __tablename__ = 'patients'
    patient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    records = db.relationship('Record', backref='patient', lazy=True)


class Record(db.Model):
    __tablename__ = 'records'
    record_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    text = db.Column(db.Text, nullable=False)


# This creates the tables in Supabase automatically
with app.app_context():
    db.create_all()


# --- ENDPOINTS ---

@app.route('/')
def home():
    return jsonify({"status": "online", "message": "PalQR API is running"})


# GET all patients
@app.route('/patients', methods=['GET'])
def get_all_patients():
    patients = Patient.query.all()
    return jsonify([
        {"id": p.patient_id, "name": p.name, "surname": p.surname}
        for p in patients
    ])


# POST a new patient
@app.route('/patients', methods=['POST'])
def create_patient():
    data = request.get_json()
    if not data or 'name' not in data or 'surname' not in data:
        return jsonify({"error": "Missing data"}), 400

    new_p = Patient(name=data['name'], surname=data['surname'])
    db.session.add(new_p)
    db.session.commit()
    return jsonify({"id": new_p.patient_id, "message": "Patient created"}), 201


# POST a new record for a patient
@app.route('/records', methods=['POST'])
def create_record():
    data = request.get_json()
    # Basic validation
    if not data or 'patient_id' not in data or 'text' not in data:
        return jsonify({"error": "Missing patient_id or text"}), 400

    new_r = Record(patient_id=data['patient_id'], text=data['text'])
    db.session.add(new_r)
    db.session.commit()
    return jsonify({"id": new_r.record_id, "timestamp": new_r.timestamp}), 201


# 4. GET: Retrieve a specific patient and ALL their records
@app.route('/patients/<int:id>', methods=['GET'])
def get_patient_details(id):
    # Find the patient or return 404 if they don't exist
    patient = Patient.query.get_or_404(id)

    # Format the records list
    records_list = []
    for r in patient.records:
        records_list.append({
            "record_id": r.record_id,
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "text": r.text
        })

    return jsonify({
        "patient_id": patient.patient_id,
        "name": patient.name,
        "surname": patient.surname,
        "history": records_list
    })

if __name__ == '__main__':
    app.run(debug=True)