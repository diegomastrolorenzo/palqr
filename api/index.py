import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from .qr_generator import qr_bp

load_dotenv()
app = Flask(__name__)
app.register_blueprint(qr_bp)


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


@app.route('/view/<int:patient_id>')
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    full_name = f"{patient.name} {patient.surname}"
    patient_records = patient.records

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <title>{{ full_name }} | Medical Record</title>
    </head>
    <body class="bg-[#f6f8fa] text-[#24292f] font-sans antialiased">
        <div class="max-w-2xl mx-auto md:mt-10 bg-white border border-[#d0d7de] md:rounded-lg shadow-sm">

            <div class="bg-[#24292f] p-6 text-white md:rounded-t-lg">
                <div class="flex items-center space-x-2 text-sm text-gray-400 mb-2 font-mono">
                    <span>Database</span>
                    <span>/</span>
                    <span class="text-white">PALQR_{{ patient.patient_id }}</span>
                </div>
                <h1 class="text-2xl font-bold">{{ full_name }}</h1>
            </div>

            <div class="p-6">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center">
                    <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"></path><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3z" clip-rule="evenodd"></path></svg>
                    Medical Records ({{ patient_records|length }})
                </h2>

                <div class="space-y-4">
                    {% for record in patient_records %}
                    <div class="border border-[#d0d7de] rounded-md p-4 hover:bg-gray-50 transition-colors">
                        <div class="flex flex-col space-y-2">
                            <div class="flex justify-between items-center">
                                <span class="text-[11px] font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100 uppercase font-bold">
                                    Entry #{{ record.record_id }}
                                </span>
                                <span class="text-[11px] font-mono text-gray-500">
                                    {{ record.timestamp.strftime('%Y-%m-%d %H:%M') if record.timestamp else "N/A" }}
                                </span>
                            </div>
                            <p class="text-sm text-gray-800 leading-relaxed">
                                {{ record.text }}
                            </p>
                        </div>
                    </div>
                    {% else %}
                    <div class="text-center py-10 bg-gray-50 border-2 border-dashed border-gray-200 rounded-md">
                        <p class="text-gray-400 text-sm italic font-mono">0 records found for this ID.</p>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="p-4 border-t border-gray-100 text-center bg-gray-50 md:rounded-b-lg">
                <p class="text-[10px] text-gray-400 font-mono tracking-tighter uppercase">
                    PALQR_SYSTEM_v3.2 // NODE_SECURE
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, patient=patient, full_name=full_name, patient_records=patient_records)

if __name__ == '__main__':
    app.run(debug=True)