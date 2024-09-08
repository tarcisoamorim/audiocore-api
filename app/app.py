import logging
from flask import Flask, request, send_file
import os
import subprocess
import base64

# Configuração de Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Formatos de entrada suportados
SUPPORTED_FORMATS = {'audio/mpeg', 'audio/wav',
                     'audio/aac', 'audio/flac', 'audio/ogg'}
DEFAULT_CONVERSION_FORMAT = 'audio/ogg'


@app.route('/convert', methods=['POST'])
def convert():
    response_format = request.args.get(
        'format', 'binary')  # 'binary' ou 'base64'
    if 'file' not in request.files:
        logging.error("No file provided in the request.")
        return {'error': 'No file provided'}, 400

    file = request.files['file']
    if file.filename == '':
        logging.error("No selected file in the request.")
        return {'error': 'No selected file'}, 400

    content_type = file.content_type
    if content_type not in SUPPORTED_FORMATS:
        logging.error(f"Unsupported file format: {content_type}")
        return {'error': 'Unsupported file format'}, 415

    input_path = f"/tmp/{file.filename}"
    file.save(input_path)
    logging.info(f"File saved at {input_path}")

    # Corrigindo o áudio antes da conversão final
    fixed_input_path = input_path.rsplit('.', 1)[0] + '_fixed.mp3'
    ffmpeg_fix_command = [
        'ffmpeg',
        '-i', input_path,
        '-acodec', 'libmp3lame',  # Reencodar para corrigir possíveis problemas de metadados
        '-ar', '44100',  # Manter a taxa de amostragem
        '-ab', '192k',  # Usar uma taxa de bits constante para melhorar a qualidade e consistência
        fixed_input_path
    ]
    subprocess.run(ffmpeg_fix_command, check=True)
    logging.info("Audio file fixed.")

    output_path = fixed_input_path.rsplit('.', 1)[0] + '.ogg'

    try:
        # Comando ffmpeg para conversão
        ffmpeg_command = [
            'ffmpeg',
            '-i', fixed_input_path,
            '-c:a', 'libopus',
            '-b:v', '18.9k',
            '-b:a', '18.9k',
            '-ar', '16000',
            '-ac', '1',
            output_path
        ]
        subprocess.run(ffmpeg_command, check=True)
        logging.info("Audio conversion successful.")

        # Seta o vendor tag com o opustags
        opustags_command = [
            'opustags',
            '-i', output_path,
            '--delete-all',
            '--set-vendor', 'WhatsApp'
        ]
        subprocess.run(opustags_command, check=True)
        logging.info("Opus tags set successfully.")

        # Obtem a duração do arquivo de áudio de saída em milissegundos
        ffprobe_command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            output_path
        ]
        result = subprocess.run(
            ffprobe_command, stdout=subprocess.PIPE, text=True)
        # Obtem duração em segundos
        duration_sec = float(result.stdout.strip())
        # Converte segundos em milissegundos inteiros
        duration_ms = round(duration_sec * 1000)

        if response_format == 'base64':
            with open(output_path, "rb") as audio_file:
                base64_audio = base64.b64encode(
                    audio_file.read()).decode('utf-8')
            # Retorno da duração em milissegundos
            response = {'base64Audio': base64_audio,
                        'duration_ms': duration_ms}
        else:
            response = send_file(output_path, as_attachment=True)
            # Adicionar duração em milissegundos aos cabeçalhos
            response.headers['Duration'] = duration_ms

        return response

    except subprocess.CalledProcessError as e:
        logging.error(f"Error during conversion: {e}")
        return {'error': f'Error during conversion: {str(e)}'}, 500
    finally:
        os.remove(input_path)
        if os.path.exists(fixed_input_path):
            os.remove(fixed_input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
        logging.info("Temporary files removed.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
