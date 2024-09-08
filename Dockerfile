FROM python:3.9-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libogg-dev \
    cmake \
    pkg-config \
    wget \
    build-essential

RUN wget https://github.com/fmang/opustags/archive/refs/tags/1.10.0.tar.gz && \
    tar xvf 1.10.0.tar.gz && \
    cd opustags-1.10.0 && \
    mkdir build && cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local .. && \
    make && \
    make install

FROM python:3.9-slim

COPY --from=builder /usr/local /usr/local

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000

CMD ["python", "app.py"]