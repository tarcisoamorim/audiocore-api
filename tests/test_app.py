import io
from app.app import app
import pytest
from flask_testing import TestCase


class TestAudioConversionAPI(TestCase):
    def create_app(self):
        # Configure your Flask application for testing
        app.config['TESTING'] = True
        return app

    def test_audio_conversion_no_file(self):
        # Teste para verificar a resposta quando nenhum arquivo é enviado
        response = self.client.post('/convert')
        self.assertEqual(response.status_code, 400)
        self.assertIn('No file provided', response.json['error'])

    def test_audio_conversion_wrong_format(self):
        # Teste para verificar a resposta quando o formato do arquivo não é suportado
        data = {'file': (io.BytesIO(b'my file contents'), 'test.txt')}
        response = self.client.post(
            '/convert', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 415)
        self.assertIn('Unsupported file format', response.json['error'])

    def test_audio_conversion_success_binary(self):
        # Teste para verificar a resposta de sucesso em formato binário
        with open('tests/test.mp3', 'rb') as audio:
            data = {'file': (audio, 'test.mp3')}
            response = self.client.post(
                '/convert', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)  # Verifica se algum dado foi retornado

    def test_audio_conversion_success_base64(self):
        # Teste para verificar a resposta de sucesso em formato base64
        with open('tests/test.mp3', 'rb') as audio:
            data = {'file': (audio, 'test.mp3')}
            response = self.client.post(
                '/convert?format=base64', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        # Verifica se a chave base64Audio está na resposta JSON
        self.assertIn('base64Audio', response.json)


# Configura o ambiente de teste para usar pytest
if __name__ == '__main__':
    pytest.main()
