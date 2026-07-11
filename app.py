#!/usr/bin/env python3
"""
GSA Certificate Generator API - v2.0 (300 DPI, print quality)
"""

from flask import Flask, request, jsonify
import base64
import os
import traceback

from generate_certificate import generate_certificate, CERT_CONFIGS

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'GSA Certificate Generator',
        'version': '2.0',
        'quality': '300 DPI (print-ready)'
    })


@app.route('/generate_single', methods=['POST'])
def generate_single():
    """
    Generuje jeden certyfikat.
    
    Body JSON:
        imie_nazwisko: str
        nazwa_kursu: str
        miasto: str
        data_ukonczenia: str (np. "11.07.2026")
        cert_type: str ('1', '2', '3' lub '4')
    
    Returns:
        JSON z pdf_base64, cert_name, filename, size_bytes, success
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON body'}), 400

        imie_nazwisko = data.get('imie_nazwisko', '').strip()
        nazwa_kursu = data.get('nazwa_kursu', '').strip()
        miasto = data.get('miasto', '').strip()
        data_ukonczenia = data.get('data_ukonczenia', '').strip()
        cert_type = str(data.get('cert_type', '1'))

        if not imie_nazwisko:
            return jsonify({'success': False, 'error': 'imie_nazwisko is required'}), 400
        if cert_type not in CERT_CONFIGS:
            return jsonify({'success': False, 'error': f'cert_type must be 1-4, got: {cert_type}'}), 400

        pdf_bytes = generate_certificate(
            cert_type=cert_type,
            imie_nazwisko=imie_nazwisko,
            nazwa_kursu=nazwa_kursu,
            miasto=miasto,
            data_ukonczenia=data_ukonczenia
        )

        cert_name = CERT_CONFIGS[cert_type]['name']
        safe_name = imie_nazwisko.replace(' ', '_').replace('/', '-')
        filename = f"{safe_name}_{cert_name}.pdf"

        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return jsonify({
            'success': True,
            'cert_name': cert_name,
            'filename': filename,
            'size_bytes': len(pdf_bytes),
            'size_mb': round(len(pdf_bytes) / 1024 / 1024, 2),
            'pdf_base64': pdf_base64
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate_all', methods=['POST'])
def generate_all():
    """
    Generuje wszystkie 4 certyfikaty dla jednego uczestnika.
    
    Body JSON:
        imie_nazwisko: str
        nazwa_kursu: str
        miasto: str
        data_ukonczenia: str
    
    Returns:
        JSON z listą certyfikatów (cert_name, filename, pdf_base64, size_bytes)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON body'}), 400

        imie_nazwisko = data.get('imie_nazwisko', '').strip()
        nazwa_kursu = data.get('nazwa_kursu', '').strip()
        miasto = data.get('miasto', '').strip()
        data_ukonczenia = data.get('data_ukonczenia', '').strip()

        if not imie_nazwisko:
            return jsonify({'success': False, 'error': 'imie_nazwisko is required'}), 400

        certificates = []
        for cert_type, config in CERT_CONFIGS.items():
            pdf_bytes = generate_certificate(
                cert_type=cert_type,
                imie_nazwisko=imie_nazwisko,
                nazwa_kursu=nazwa_kursu,
                miasto=miasto,
                data_ukonczenia=data_ukonczenia
            )
            cert_name = config['name']
            safe_name = imie_nazwisko.replace(' ', '_').replace('/', '-')
            filename = f"{safe_name}_{cert_name}.pdf"

            certificates.append({
                'cert_type': cert_type,
                'cert_name': cert_name,
                'filename': filename,
                'size_bytes': len(pdf_bytes),
                'size_mb': round(len(pdf_bytes) / 1024 / 1024, 2),
                'pdf_base64': base64.b64encode(pdf_bytes).decode('utf-8')
            })

        return jsonify({
            'success': True,
            'imie_nazwisko': imie_nazwisko,
            'certificates': certificates
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
