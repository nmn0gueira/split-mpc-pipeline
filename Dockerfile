FROM ubuntu:24.04 AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    automake \
    autoconf \
    build-essential \
    ca-certificates \
    cmake \
    clang \
    curl \
    git \
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
    pkg-config \
    python3 \
    python3-pip \
    python3-venv \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip3 install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip3 install --no-cache-dir -r /tmp/requirements.txt
RUN echo "source /opt/venv/bin/activate" >> ~/.bashrc

SHELL ["/bin/bash", "--login", "-c"]
WORKDIR /workspace


FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdb \
    && rm -rf /var/lib/apt/lists/*


FROM base AS runtime

COPY . .

RUN bash scripts/install.sh
RUN cd MP-SPDZ && Scripts/setup-ssl.sh 3 && Scripts/setup-clients.sh 3

ARG modules=
RUN bash scripts/build_submodules.sh --modules "$modules"
