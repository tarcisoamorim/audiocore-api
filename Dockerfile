# Use a imagem oficial do Python como base
FROM python:3.9-slim

# Definir o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libogg-dev \
    cmake \
    pkg-config \
    wget \
    build-essential \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Instalar opustags
RUN wget https://github.com/fmang/opustags/archive/refs/tags/1.10.0.tar.gz && \
    tar xvf 1.10.0.tar.gz && \
    cd opustags-1.10.0 && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local .. && \
    make && \
    make install && \
    cd /app && \
    rm -rf opustags-1.10.0 1.10.0.tar.gz

# Copiar requirements.txt e instalar dependências Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY app/ /app/

# Expor a porta
EXPOSE 5000

# Definir variável de ambiente para desativar buffer do stdout/stderr
ENV PYTHONUNBUFFERED=1

# Comando de inicialização
CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]
