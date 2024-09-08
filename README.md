# AudioCore API

## Descrição

AudioCore API é uma solução simples para conversão de arquivos de áudio para formatos compatíveis com a API do WhatsApp, especificamente o formato OGG. O projeto utiliza ffmpeg para converter áudios e opustags para ajustar as tags dos arquivos OGG, garantindo compatibilidade e otimização para uso em plataformas de mensagens.

### Funcionalidades

- Conversão de arquivos MP3 para OGG.
- Correção automática de arquivos MP3 antes da conversão.
- Suporte para entrada de arquivos em múltiplos formatos populares como WAV, AAC e FLAC.
- Opção para receber o arquivo convertido em formato binário ou codificado em base64.
- Tecnologias Utilizadas
- Flask: Framework web utilizado para criar a API.
- FFmpeg: Ferramenta para processamento de vídeo e áudio.
- OpusTags: Ferramenta para manipulação de tags em arquivos OGG.
- Instalação

## Pré-requisitos

#### Docker

- Python 3.9 ou superior
- Configuração com Docker
- Clone o repositório:

```bash
git clone https://github.com/tarcisoamorim/audiocore-api.git
```

#### Construa a imagem Docker:

```bash
docker build -t tarcisoamorim/audiocore-api .
```

#### Execute o container:

```bash
docker run -p 5000:5000 tarcisoamorim/audiocore-api
```

#### Uso:

Enviar um arquivo para conversão
Faça uma requisição POST para `'/convert'` com o arquivo de áudio como parte do corpo da requisição. Exemplo usando curl:

```bash
curl -X POST -F "file=@caminho_para_seu_arquivo.mp3" http://localhost:5000/convert
```

#### Receber arquivo em Base64

Para receber o arquivo convertido em formato Base64, adicione o parâmetro `'format=base64'` na URL:

```bash
curl -X POST -F "file=@caminho_para_seu_arquivo.mp3" http://localhost:5000/convert?format=base64
```

### Contribuições

Contribuições são bem-vindas! Para contribuir, por favor, faça um fork do repositório, crie uma branch para suas modificações e submeta um pull request.

### Licença

Distribuído sob a licença MIT. Veja LICENSE para mais informações.
