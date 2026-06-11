# CTF Solver Sandbox — base image (binary/pwn/web categories)
# Heavy tools (SageMath, Podman, PyTorch) are deferred to a separate image.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm

RUN apt-get update && apt-get install -y \
    netcat-openbsd curl wget nmap \
    binutils file xxd bsdmainutils binwalk \
    gdb ltrace strace \
    exiftool steghide pngcheck imagemagick \
    foremost dcfldd testdisk \
    ffmpeg sox \
    tesseract-ocr tesseract-ocr-eng \
    openssl libssl-dev \
    gcc g++ make cmake \
    python3 python3-pip python3-dev \
    ruby ruby-dev \
    git jq zip unzip ca-certificates ncurses-term \
    && rm -rf /var/lib/apt/lists/*

# radare2
RUN git clone --depth=1 https://github.com/radareorg/radare2 /tmp/r2 \
    && cd /tmp/r2 && bash sys/install.sh --install \
    && ldconfig && rm -rf /tmp/r2

# zsteg
RUN gem install zsteg

# Python CTF libraries
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir \
    pwntools pycryptodome sympy gmpy2 requests \
    Pillow z3-solver pytesseract scipy numpy \
    angr capstone unicorn ropgadget tqdm flask \
    PyJWT pyghidra volatility3 pycryptodome

# RsaCtfTool
RUN git clone --depth=1 https://github.com/RsaCtfTool/RsaCtfTool /opt/RsaCtfTool \
    && pip3 install --no-cache-dir /opt/RsaCtfTool

COPY sandbox/sandbox-tools.txt /tools.txt
WORKDIR /challenge
