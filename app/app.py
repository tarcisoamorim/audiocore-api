import logging
import os
import subprocess
import base64
import uuid
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from functools import wraps
from flask_cors import CORS
import tempfile


def create_app():
    app = Flask(__name__)

    # Configurações
    app.config['MAX_CONTENT_LENGTH'] = 20 * \
        1024 * 1024  # Limite de 20 MB para uploads
    UPLOAD_FOLDER = '/tmp/uploads'
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Configuração de Logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Configurações de CORS e API Key do código Go
    api_key = os.getenv('API_KEY')
    allowed_origins = os.getenv('CORS_ALLOW_ORIGINS', '*').split(',')

    # Configurar CORS
    cors = CORS(app, resources={
        r"/*": {
            "origins": allowed_origins,
            "methods": ["POST", "GET", "OPTIONS"],
            "allow_headers": ["Origin", "Content-Type", "Accept", "Authorization", "apikey"]
        }
    })

    # Formatos de entrada suportados (MIME types)
    SUPPORTED_FORMATS = {
        'audio/mpeg': 'mp3',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/aac': 'aac',
        'audio/x-aac': 'aac',
        'audio/flac': 'flac',
        'audio/x-flac': 'flac',
        'audio/ogg': 'ogg',
        'audio/opus': 'opus',
        'audio/webm': 'webm',
        'video/webm': 'webm',
        'audio/3gpp': '3gp',
        'audio/3gpp2': '3g2',
        'audio/mp4': 'm4a',
        'video/mp4': 'mp4',
        'application/octet-stream': ''
    }

    def validate_api_key(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not api_key:
                return jsonify({'error': 'API key não configurada no servidor'}), 500

            request_api_key = request.headers.get('apikey')
            if not request_api_key:
                return jsonify({'error': 'API key não fornecida'}), 401

            if request_api_key != api_key:
                return jsonify({'error': 'API key inválida'}), 401

            return f(*args, **kwargs)
        return decorated_function

    def fix_audio(input_path, fixed_input_path):
        ffmpeg_fix_command = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-vn',
            '-acodec', 'libmp3lame',
            '-ar', '44100',
            '-ab', '192k',
            '-f', 'mp3',
            fixed_input_path
        ]
        result = subprocess.run(
            ffmpeg_fix_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no ffmpeg (fix_audio): {result.stderr}")
        logging.info("Arquivo de áudio corrigido.")

    def convert_audio(fixed_input_path, output_path):
        ffmpeg_command = [
            'ffmpeg',
            '-y',
            '-i', fixed_input_path,
            '-c:a', 'libopus',
            '-b:a', '18.9k',
            '-ar', '16000',
            '-ac', '1',
            output_path
        ]
        result = subprocess.run(
            ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no ffmpeg (convert_audio): {result.stderr}")
        logging.info("Conversão de áudio bem-sucedida.")

    def set_opus_tags(output_path):
        opustags_command = [
            'opustags',
            '--overwrite',
            '--delete-all',
            '--set-vendor', 'WhatsApp',
            output_path
        ]
        result = subprocess.run(
            opustags_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no opustags: {result.stderr}")
        logging.info("Tags Opus definidas com sucesso.")

    def get_audio_duration(output_path):
        ffprobe_command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            output_path
        ]
        result = subprocess.run(
            ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"Erro no ffprobe: {result.stderr}")
        duration_sec = float(result.stdout.strip())
        duration_ms = round(duration_sec * 1000)
        return duration_ms

    def generate_temp_filename(extension=''):
        return os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{f'.{extension}' if extension else ''}")

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(error):
        logging.error("Arquivo excede o tamanho máximo permitido.")
        return jsonify({'error': 'Arquivo muito grande'}), 413

    @app.route('/process-audio', methods=['POST'])
    @validate_api_key
    def process_audio():
        try:
            # Determina o formato de resposta com base no header 'Accept'
            accept_header = request.headers.get('Accept', '')
            response_format = 'base64' if 'application/json' in accept_header else 'binary'

            # Determina o tipo de conteúdo da requisição
            content_type = request.content_type or ''
            logging.info(f"Tipo de conteúdo recebido: {content_type}")

            input_path = None
            fixed_input_path = None
            output_path = None

            try:
                # Processar diferentes tipos de entrada (como no código Go)
                if content_type == 'application/octet-stream':
                    audio_data = request.get_data()
                    input_path = generate_temp_filename('wav')
                    with open(input_path, 'wb') as f:
                        f.write(audio_data)

                elif content_type == 'application/json':
                    json_data = request.get_json()
                    if not json_data or 'audio' not in json_data:
                        return jsonify({'error': 'Dados de áudio não fornecidos'}), 400

                    audio_data = base64.b64decode(json_data['audio'])
                    input_path = generate_temp_filename('wav')
                    with open(input_path, 'wb') as f:
                        f.write(audio_data)

                elif 'file' in request.files:
                    file = request.files['file']
                    if file.filename == '':
                        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

                    extension = SUPPORTED_FORMATS.get(file.content_type, '')
                    if not extension and '.' in file.filename:
                        extension = file.filename.rsplit('.', 1)[1].lower()

                    input_path = generate_temp_filename(extension or 'wav')
                    file.save(input_path)

                else:
                    return jsonify({'error': 'Tipo de conteúdo não suportado'}), 415

                # Processar o áudio
                fixed_input_path = generate_temp_filename('mp3')
                fix_audio(input_path, fixed_input_path)

                output_path = generate_temp_filename('ogg')
                convert_audio(fixed_input_path, output_path)

                set_opus_tags(output_path)
                duration_ms = get_audio_duration(output_path)

                # Retornar resposta no formato apropriado
                if response_format == 'base64':
                    with open(output_path, "rb") as audio_file:
                        base64_audio = base64.b64encode(
                            audio_file.read()).decode('utf-8')
                    return jsonify({
                        'audio': base64_audio,
                        'duration': duration_ms,
                        'format': 'ogg'
                    })
                else:
                    response = send_file(
                        output_path,
                        mimetype='audio/ogg',
                        as_attachment=True,
                        download_name='converted_audio.ogg'
                    )
                    response.headers['Duration'] = str(duration_ms)
                    return response

            finally:
                # Limpar arquivos temporários
                for path in [input_path, fixed_input_path, output_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                            logging.info(
                                f"Arquivo temporário removido: {path}")
                        except Exception as e:
                            logging.warning(
                                f"Não foi possível remover {path}: {e}")

        except Exception as e:
            logging.error(f"Erro durante o processamento: {e}")
            return jsonify({'error': str(e)}), 500

    return app


# Configuração para execução do app
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=False)
