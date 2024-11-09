# AudioCore API

## Descrição

AudioCore API é uma solução simples para conversão de arquivos de áudio para formatos compatíveis com a API do WhatsApp, especificamente o formato OGG. O projeto utiliza ffmpeg para converter áudios e opustags para ajustar as tags dos arquivos OGG, garantindo compatibilidade e otimização para uso em plataformas de mensagens.

Este projeto foi inspirado e segue padrões similares ao [Evolution Audio Converter](https://github.com/EvolutionAPI/evolution-audio-converter).

## 🚀 Funcionalidades

- Conversão de arquivos de áudio para formato OGG/Opus otimizado para WhatsApp
- Correção automática de arquivos de áudio antes da conversão
- Múltiplos formatos de entrada suportados (MP3, WAV, AAC, FLAC, etc.)
- Suporte para diferentes formatos de entrada de dados:
  - Upload de arquivo direto
  - Dados em base64
  - Dados binários
- Opções de resposta em formato binário ou base64
- Autenticação via API Key
- Configuração CORS flexível

## 🛠️ Tecnologias Utilizadas

- Flask: Framework web para a API
- FFmpeg: Processamento de áudio
- OpusTags: Manipulação de tags em arquivos OGG
- Python 3.9+

## 📋 Pré-requisitos

- Python 3.9 ou superior
- FFmpeg
- Opus Tools
- Docker (opcional)

## 🔧 Instalação

### Usando Docker (Recomendado)

1. Clone o repositório:

```bash
git clone https://github.com/tarcisoamorim/audiocore-api.git
cd audiocore-api
```

2. Construa a imagem Docker:

```bash
docker build -t tarcisoamorim/audiocore-api .
```

3. Execute o container:

```bash
docker run -p 5000:5000 tarcisoamorim/audiocore-api
```

### Instalação Local

1. Clone o repositório:

```bash
git clone https://github.com/tarcisoamorim/audiocore-api.git
cd audiocore-api
```

2. Instale as dependências do sistema:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg opus-tools

# CentOS/RHEL
sudo yum install -y ffmpeg opus-tools
```

3. Configure o ambiente:

```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

4. Instale as dependências Python:

```bash
pip install -r requirements.txt
```

5. Execute o servidor:

```bash
python app.py
```

## 🎯 Uso

### Endpoint: POST /convert

Converte um arquivo de áudio para o formato OGG/Opus otimizado para WhatsApp.

#### Métodos de Envio

1. **Upload de Arquivo**:

```bash
curl -X POST -F "file=@seu_audio.mp3" http://localhost:5000/convert
```

2. **Dados em Base64**:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"audio":"base64_do_audio"}' \
  http://localhost:5000/convert
```

3. **Dados Binários**:

```bash
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@seu_audio.mp3" \
  http://localhost:5000/convert
```

#### Formatos de Resposta

1. **Binário** (padrão):

```bash
curl -X POST -F "file=@seu_audio.mp3" http://localhost:5000/convert
```

2. **Base64**:

```bash
curl -X POST \
  -H "Accept: application/json" \
  -F "file=@seu_audio.mp3" \
  http://localhost:5000/convert
```

## ⚙️ Configuração

Copie o arquivo `.env.example` para `.env` e configure as variáveis necessárias:

```bash
cp .env.example .env
```

Variáveis disponíveis:

- `API_KEY`: Chave de autenticação
- `CORS_ALLOW_ORIGINS`: Origens permitidas
- `PORT`: Porta do servidor (padrão: 5000)
- `MAX_FILE_SIZE`: Tamanho máximo do arquivo (padrão: 20MB)

## 📝 Formatos de Entrada Suportados

- MP3 (.mp3)
- WAV (.wav)
- AAC (.aac)
- FLAC (.flac)
- OGG (.ogg)
- WebM (.webm)
- 3GPP (.3gp)
- MP4 (.mp4, .m4a)

## 🤝 Contribuições

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/NovaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/NovaFeature`)
5. Abra um Pull Request

## 📜 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## 📌 Notas

Este projeto segue padrões similares ao [Evolution Audio Converter](https://github.com/EvolutionAPI/evolution-audio-converter), adaptando suas funcionalidades para um serviço mais específico e otimizado para conversão de áudio para WhatsApp.
