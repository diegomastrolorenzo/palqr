import qrcode
import io
import os
from flask import Blueprint, send_file, request

qr_bp = Blueprint('qr_bp', __name__)


@qr_bp.route('/generate_qr/<int:patient_id>')
def generate_qr(patient_id):
    # 1. Try to get the Production URL from Env Vars
    # 2. If not found, fall back to the current host
    base_url = os.environ.get('PRODUCTION_URL')

    if not base_url:
        base_url = request.host_url.rstrip('/')
    else:
        base_url = base_url.rstrip('/')

    # 3. Create the production link
    target_link = f"{base_url}/view/{patient_id}"

    # 4. Generate the QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(target_link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # 5. Stream it back
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')