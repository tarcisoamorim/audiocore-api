# app/app.py

import logging
import os
import subprocess
import base64
import uuid
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge


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
        'application/octet-stream': ''  # Caso especial
    }

    # Extensões permitidas
    ALLOWED_EXTENSIONS = set(SUPPORTED_FORMATS.values())

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_extension(mime_type):
        return SUPPORTED_FORMATS.get(mime_type, '')

    def generate_temp_filename(extension):
        return secure_filename(f"{uuid.uuid4()}.{extension}")

    def fix_audio(input_path, fixed_input_path):
        ffmpeg_fix_command = [
            'ffmpeg',
            '-y',  # Sobrescrever arquivos sem perguntar
            '-i', input_path,
            '-vn',  # Sem processamento de vídeo
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

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(error):
        logging.error("Arquivo excede o tamanho máximo permitido.")
        return jsonify({'error': 'Arquivo muito grande'}), 413

    @app.route('/convert', methods=['POST'])
    def convert():
        # Determina o formato de resposta com base no header 'Accept'
        accept_header = request.headers.get('Accept', '')
        if 'application/json' in accept_header:
            response_format = 'base64'
        else:
            response_format = 'binary'

        # Determina o tipo de conteúdo da requisição
        content_type = request.content_type
        logging.info(f"Tipo de conteúdo recebido: {content_type}")

        if content_type == 'application/octet-stream':
            # Lê dados binários diretamente do corpo da requisição
            audio_data = request.data
            if not audio_data:
                logging.error("Nenhum dado fornecido na solicitação.")
                return jsonify({'error': 'Nenhum dado fornecido'}), 400
            extension = 'wav'  # Extensão padrão
            filename = generate_temp_filename(extension)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(input_path, 'wb') as f:
                f.write(audio_data)
            logging.info(f"Arquivo salvo em {input_path}")

        elif content_type == 'application/json':
            # Lê dados de áudio codificados em base64 do JSON
            json_data = request.get_json()
            if not json_data or 'audio' not in json_data:
                logging.error(
                    "Nenhum dado de áudio fornecido na solicitação JSON.")
                return jsonify({'error': 'Nenhum dado de áudio fornecido'}), 400
            base64_audio = json_data['audio']
            try:
                audio_data = base64.b64decode(base64_audio)
            except Exception as e:
                logging.error(f"Erro ao decodificar áudio base64: {e}")
                return jsonify({'error': 'Erro ao decodificar áudio base64'}), 400
            extension = 'wav'  # Extensão padrão
            filename = generate_temp_filename(extension)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(input_path, 'wb') as f:
                f.write(audio_data)
            logging.info(f"Arquivo salvo em {input_path}")

        elif 'file' in request.files:
            # Processa arquivo enviado via multipart/form-data
            file = request.files['file']
            if file.filename == '':
                logging.error("Nenhum arquivo selecionado na solicitação.")
                return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

            content_type = file.content_type
            logging.info(f"Tipo de conteúdo recebido: {content_type}")

            extension = get_extension(content_type)
            if not extension:
                # Tenta adivinhar a extensão a partir do nome do arquivo
                if allowed_file(file.filename):
                    extension = file.filename.rsplit('.', 1)[1].lower()
                else:
                    logging.error(
                        f"Formato de arquivo não suportado: {content_type}")
                    return jsonify({'error': 'Formato de arquivo não suportado'}), 415

            filename = generate_temp_filename(extension)
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)
            logging.info(f"Arquivo salvo em {input_path}")

        else:
            logging.error("Tipo de conteúdo não suportado.")
            return jsonify({'error': 'Tipo de conteúdo não suportado'}), 415

        try:
            fixed_filename = generate_temp_filename('mp3')
            fixed_input_path = os.path.join(UPLOAD_FOLDER, fixed_filename)
            fix_audio(input_path, fixed_input_path)

            output_filename = generate_temp_filename('ogg')
            output_path = os.path.join(UPLOAD_FOLDER, output_filename)
            convert_audio(fixed_input_path, output_path)

            set_opus_tags(output_path)
            duration_ms = get_audio_duration(output_path)

            if response_format == 'base64':
                with open(output_path, "rb") as audio_file:
                    base64_audio = base64.b64encode(
                        audio_file.read()).decode('utf-8')
                response = jsonify(
                    {'base64Audio': base64_audio, 'duration_ms': duration_ms})
            else:
                response = send_file(
                    output_path,
                    as_attachment=True,
                    download_name='converted_audio.ogg',
                    mimetype='audio/ogg'
                )
                response.headers['Duration'] = str(duration_ms)

            return response

        except Exception as e:
            logging.error(f"Erro durante o processamento: {e}")
            return jsonify({'error': f'Erro durante o processamento: {str(e)}'}), 500

        finally:
            # Remover arquivos temporários
            for path in [input_path, fixed_input_path, output_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logging.info(f"Arquivo temporário removido: {path}")
                    except Exception as e:
                        logging.warning(
                            f"Não foi possível remover {path}: {e}")

    return app

# Remover o bloco abaixo para evitar que o app seja executado diretamente
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=False)
