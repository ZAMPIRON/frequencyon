"""
FrequencyON - Aplicação Principal Flask
Ativa HTTPS automático para compatibilidade com iPhone/iOS.
"""

from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import base64
import os
import sys
from datetime import datetime

from database import DatabaseManager
from facial_recognition import FacialRecognitionService

app = Flask(__name__)
db_manager = DatabaseManager()
face_service = FacialRecognitionService()

last_recognition_result = {
    'aluno_id': None,
    'aluno_nome': None,
    'timestamp': None
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    """Recebe o quadro do navegador/celular via HTTP POST (Base64) e processa."""
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'success': False, 'message': 'Imagem não fornecida'}), 400

    try:
        # Decodifica a string base64 enviada pelo celular
        image_data = data['image'].split(',')[1] if ',' in data['image'] else data['image']
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'success': False, 'message': 'Falha ao decodificar frame'}), 400

        # Reconhece a face na imagem
        recognition_result = face_service.recognize_face(frame)

        if recognition_result:
            aluno_id, aluno_nome = recognition_result
            hora_atual = datetime.now().strftime("%H:%M:%S")

            # Checa se é hora de gravar presença no Banco de Dados
            if face_service.should_register_attendance(aluno_id):
                db_manager.register_attendance(aluno_id, aluno_nome)
                status = "registrado"
                
                # 📢 IMPRIME O REGISTRO NO TERMINAL DO SERVIDOR
                print(f"[{hora_atual}] ✅ PRESENÇA CONFIRMADA: {aluno_nome} ({aluno_id})")
            else:
                status = "ja_registrado"

            global last_recognition_result
            last_recognition_result = {
                'aluno_id': aluno_id,
                'aluno_nome': aluno_nome,
                'timestamp': hora_atual
            }

            return jsonify({
                'success': True,
                'recognized': True,
                'aluno_nome': aluno_nome,
                'status': status
            })

        return jsonify({'success': True, 'recognized': False})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/attendance/history')
def get_attendance_history():
    limit = request.args.get('limit', default=50, type=int)
    return jsonify(db_manager.get_attendance_history(limit))

@app.route('/api/attendance/last')
def get_last_attendance():
    global last_recognition_result
    return jsonify(last_recognition_result)

if __name__ == '__main__':
    print("=" * 50)
    print("FrequencyON - Sistema de Controle de Frequência")
    print("=" * 50)

    if not os.path.exists("alunos_cadastrados"):
        os.makedirs("alunos_cadastrados")

    # Tenta usar SSL Adhoc (HTTPS necessário para iOS/Safari liberar a câmera)
    try:
        print("\n🚀 Servidor iniciando em modo HTTPS seguro...")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, ssl_context='adhoc')
    except Exception as e:
        print(f"\n⚠️ Não foi possível iniciar com ssl_context ('pyopenssl' não instalado?): {e}")
        print("Iniciando em modo HTTP simples...")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)