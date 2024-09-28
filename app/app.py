import logging
from flask import Flask, request, send_file
import os
import subprocess
import base64
from werkzeug.utils import secure_filename
import contextlib

# Configuração de Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Formatos de entrada suportados
SUPPORTED_FORMATS = {'audio/mpeg', 'audio/wav',
                     'audio/aac', 'audio/flac', 'audio/ogg'}
DEFAULT_CONVERSION_FORMAT = 'audio/ogg'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def fix_audio(input_path, fixed_input_path):
    ffmpeg_fix_command = [
        'ffmpeg',
        '-y',  # Sobrescreve arquivos sem perguntar
        '-i', input_path,
        '-acodec', 'libmp3lame',
        '-ar', '44100',
        '-ab', '192k',
        fixed_input_path
    ]
    result = subprocess.run(ffmpeg_fix_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Erro no ffmpeg (fix_audio): {result.stderr}")
    logging.info("Arquivo de áudio corrigido.")


def convert_audio(fixed_input_path, output_path):
    ffmpeg_command = [
        'ffmpeg',
        '-y',
        '-i', fixed_input_path,
        '-c:a', 'libopus',
        '-b:v', '18.9k',
        '-b:a', '18.9k',
        '-ar', '16000',
        '-ac', '1',
        output_path
    ]
    result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Erro no ffmpeg (convert_audio): {result.stderr}")
    logging.info("Conversão de áudio bem-sucedida.")


def set_opus_tags(output_path):
    opustags_command = [
        'opustags',
        '-i', output_path,
        '--delete-all',
        '--set-vendor', 'WhatsApp'
    ]
    result = subprocess.run(opustags_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise Exception(f"Erro no ffprobe: {result.stderr}")
    duration_sec = float(result.stdout.strip())
    duration_ms = round(duration_sec * 1000)
    return duration_ms


@app.route('/convert', methods=['POST'])
def convert():
    response_format = request.args.get('format', 'binary')  # 'binary' ou 'base64'

    # Adicionando logs para depuração
    logging.info(f"Chaves em request.files: {request.files.keys()}")
    logging.info(f"Dados do formulário: {request.form}")
    logging.info(f"Dados brutos da solicitação: {request.data}")

    if 'file' not in request.files:
        logging.error("Nenhum arquivo fornecido na solicitação.")
        return {'error': 'Nenhum arquivo fornecido'}, 400

    file = request.files['file']
    if file.filename == '':
        logging.error("Nenhum arquivo selecionado na solicitação.")
        return {'error': 'Nenhum arquivo selecionado'}, 400

    content_type = file.content_type
    if content_type not in SUPPORTED_FORMATS:
        logging.error(f"Formato de arquivo não suportado: {content_type}")
        return {'error': 'Formato de arquivo não suportado'}, 415

    # Validando o tamanho do arquivo
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0, 0)
    if file_length > MAX_FILE_SIZE:
        logging.error("Arquivo excede o tamanho máximo permitido.")
        return {'error': 'Arquivo muito grande'}, 413

    filename = secure_filename(file.filename)
    input_path = os.path.join("/tmp", filename)

    try:
        file.save(input_path)
        logging.info(f"Arquivo salvo em {input_path}")

        fixed_input_path = input_path.rsplit('.', 1)[0] + '_fixed.mp3'
        fix_audio(input_path, fixed_input_path)

        output_path = fixed_input_path.rsplit('.', 1)[0] + '.ogg'
        convert_audio(fixed_input_path, output_path)

        set_opus_tags(output_path)
        duration_ms = get_audio_duration(output_path)

        if response_format == 'base64':
            with open(output_path, "rb") as audio_file:
                base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')
            response = {'base64Audio': base64_audio, 'duration_ms': duration_ms}
        else:
            response = send_file(output_path, as_attachment=True)
            response.headers['Duration'] = duration_ms

        return response

    except Exception as e:
        logging.error(f"Erro durante o processamento: {e}")
        return {'error': f'Erro durante o processamento: {str(e)}'}, 500

    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(input_path)
            os.remove(fixed_input_path)
            os.remove(output_path)
        logging.info("Arquivos temporários removidos.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
