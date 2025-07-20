FROM ubuntu:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    automake \
    autoconf \
    build-essential \
    ca-certificates \
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
    pkg-config \
    python3 \
python3-pip \
		python3-venv \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*


RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Need to use venv here
COPY ../requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv
RUN /opt/venv/bin/pip3 install --no-cache-dir --upgrade pip
RUN /opt/venv/bin/pip3 install --no-cache-dir -r /tmp/requirements.txt
RUN echo "source /opt/venv/bin/activate" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]