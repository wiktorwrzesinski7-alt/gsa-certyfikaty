#!/usr/bin/env python3
"""
GSA Certificate Generator API - v3.0
Nakłada tekst na oficjalne szablony PDF (PERSONALTRAINER.pdf, GYMINSTRUCTOR.pdf).
Obsługuje polskie znaki, wektorowy PDF, jakość druku.
"""

from flask import Flask, request, jsonify
import base64
import os
import traceback

from generate_certificate import generate_certificate, generate_all_certificates

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'GSA Certificate Generator',
        'version': '3.0',
        'quality': 'vector PDF (print-ready)',
        'templates': ['PERSONALTRAINER.pdf', 'GYMINSTRUCTOR.pdf']
    })


@app.route('/generate_single', methods=['POST'])
def generate_single():
    """
    Generuje jeden certyfikat (TP lub GYM).

    Body JSON:
        cert_type: str — "TP" (Personal Trainer) lub "GYM" (Gym Instructor)
        full_name: str — Imię i nazwisko uczestnika
        cert_number: str — Numer certyfikatu (np. "11642/GSA/2026/TP")
        date_str: str (opcjonalnie) — Data w formacie YYYY-MM-DD lub DD.MM.YYYY

    Returns:
        JSON z pdf_base64, filename, size_bytes, success
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON body'}), 400

        cert_type = data.get('cert_type', '').strip().upper()
        full_name = data.get('full_name', '').strip()
        cert_number = data.get('cert_number', '').strip()
        date_str = data.get('date_str', None)

        if not full_name:
            return jsonify({'success': False, 'error': 'full_name is required'}), 400
        if cert_type not in ('TP', 'GYM'):
            return jsonify({'success': False, 'error': f'cert_type must be "TP" or "GYM", got: {cert_type}'}), 400
        if not cert_number:
            return jsonify({'success': False, 'error': 'cert_number is required'}), 400

        result = generate_certificate(
            cert_type=cert_type,
            full_name=full_name,
            cert_number=cert_number,
            date_str=date_str
        )

        pdf_base64 = base64.b64encode(result['pdf_bytes']).decode('utf-8')

        return jsonify({
            'success': True,
            'cert_type': cert_type,
            'filename': result['filename'],
            'full_name': full_name,
            'cert_number': cert_number,
            'date': result['date'],
            'size_bytes': len(result['pdf_bytes']),
            'size_kb': round(len(result['pdf_bytes']) / 1024, 1),
            'pdf_base64': pdf_base64
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate_both', methods=['POST'])
def generate_both():
    """
    Generuje oba certyfikaty (Personal Trainer + Gym Instructor) jednocześnie.

    Body JSON:
        full_name: str — Imię i nazwisko uczestnika
        cert_number_tp: str — Numer certyfikatu TP (np. "11642/GSA/2026/TP")
        cert_number_gym: str (opcjonalnie) — Numer certyfikatu GYM (domyślnie = cert_number_tp)
        date_str: str (opcjonalnie) — Data w formacie YYYY-MM-DD lub DD.MM.YYYY

    Returns:
        JSON z listą dwóch certyfikatów (tp i gym), każdy z pdf_base64 i filename
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON body'}), 400

        full_name = data.get('full_name', '').strip()
        cert_number_tp = data.get('cert_number_tp', '').strip()
        cert_number_gym = data.get('cert_number_gym', None)
        date_str = data.get('date_str', None)

        if not full_name:
            return jsonify({'success': False, 'error': 'full_name is required'}), 400
        if not cert_number_tp:
            return jsonify({'success': False, 'error': 'cert_number_tp is required'}), 400

        results = generate_all_certificates(
            full_name=full_name,
            cert_number_tp=cert_number_tp,
            cert_number_gym=cert_number_gym,
            date_str=date_str
        )

        certificates = []
        for r in results:
            certificates.append({
                'cert_type': r['cert_type'],
                'filename': r['filename'],
                'cert_number': r['cert_number'],
                'date': r['date'],
                'size_bytes': len(r['pdf_bytes']),
                'size_kb': round(len(r['pdf_bytes']) / 1024, 1),
                'pdf_base64': base64.b64encode(r['pdf_bytes']).decode('utf-8')
            })

        return jsonify({
            'success': True,
            'full_name': full_name,
            'certificates': certificates
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
