FROM python:3.10.3-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends \
    automake \
    autoconf \
    build-essential \
    cmake \
    clang \
    curl \
    git \
    gdb \
    libboost-dev \
	libboost-filesystem-dev \
	libboost-iostreams-dev \
    libboost-thread-dev \
    libgmp-dev \
    libntl-dev \
    libsodium-dev \
    libssl-dev \
    libtool \
    libomp-dev \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*


RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"
RUN rustup install stable && \
    rustup component add rustfmt --toolchain stable-x86_64-unknown-linux-gnu


WORKDIR /root
RUN curl -L https://github.com/openssl/openssl/releases/download/openssl-3.0.17/openssl-3.0.17.tar.gz -o openssl-3.0.17.tar.gz && \
    tar -xzf openssl-3.0.17.tar.gz && \
    rm openssl-3.0.17.tar.gz

WORKDIR /root/openssl-3.0.17
RUN sed -i '211s/\<static\>//' crypto/ec/curve25519.c && \
    ./Configure no-shared enable-ec_nistp_64_gcc_128 no-ssl2 no-ssl3 no-comp --prefix=/usr/local/openssl && \
    make -j$(nproc) depend && make install

COPY ../requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt