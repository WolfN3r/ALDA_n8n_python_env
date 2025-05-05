# Vycházející image s n8n a Pythonem (Debian)
FROM naskio/n8n-python:latest-debian

# Instalace nástrojů pro kompilaci a pyenv
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    zlib1g-dev \
    libssl-dev \
    libreadline-dev \
    libbz2-dev \
    libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Pyenv setup
ENV PYENV_ROOT="/root/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"
RUN curl https://pyenv.run | bash

# Výchozí verze Pythonu (možno přepsat při build)
ARG PYTHON_VERSION=3.12.3
RUN pyenv install $PYTHON_VERSION && pyenv global $PYTHON_VERSION

# Pracovní adresář
WORKDIR /home/node

# Kopíruj requirements a nainstaluj Python balíčky
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Globální instalace Python node pro n8n
RUN npm install -g n8n-nodes-python

# Spuštění n8n jako root
USER root
ENTRYPOINT ["n8n"]
CMD ["start"]