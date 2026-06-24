# syntax=docker/dockerfile:1

FROM golang:1.25 AS go-stage
FROM python:3.11.0

# General environment settings
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.0 \
    GOTOOLCHAIN=local

# Project settings
ENV user=vector \
    VECTOR_FOLDER=vector-project
    
ENV PROJECT_HOME=/home/${user}/${VECTOR_FOLDER}/

# Update dependencies
RUN apt update --fix-missing
RUN pip install --upgrade pip

# Install git and bsdmainutils, dnsutils for network tools and cloc for source code
RUN apt-get install -y git bsdmainutils dnsutils cloc unzip

# Copy Go from the golang image
COPY --from=go-stage /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/${user}/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Create non-root user
RUN useradd -ms /bin/bash ${user} && echo '${user} ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers

# NOTE: CodeQL CLI is only available for x86_64; installation is skipped on other architectures.
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        curl -L -o /tmp/codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip \
        && unzip /tmp/codeql-linux64.zip -d /opt \
        && rm /tmp/codeql-linux64.zip; \
    else \
        echo "Skipping CodeQL CLI installation: not supported on $(uname -m)"; \
    fi

ENV PATH="/opt/codeql:${PATH}"

RUN pip install npm

USER ${user}

# Install pipx and add to PATH
RUN python3 -m pip install pipx
ENV PATH="/home/${user}/.local/bin:${PATH}"

# Install Poetry
RUN pipx install "poetry==$POETRY_VERSION"
RUN poetry completions bash >> ~/.bash_completion

# Set working directory
WORKDIR ${PROJECT_HOME}

# Copy dependency files first 
COPY poetry.lock pyproject.toml ${PROJECT_HOME}

# Copy project files
COPY . ${PROJECT_HOME}

# Install network analysis tools and source code analysis tools in project directory
ENV TOOLS_DIR=/home/${user}/tools

RUN mkdir -p ${TOOLS_DIR}

RUN git clone --depth 1 https://github.com/testssl/testssl.sh.git --branch 3.3dev ${TOOLS_DIR}/testssl.sh \
    && chmod +x ${TOOLS_DIR}/testssl.sh/testssl.sh

RUN git clone https://github.com/zmap/zgrab2.git ${TOOLS_DIR}/zgrab2 \
    && cd ${TOOLS_DIR}/zgrab2 \
    && make

ENV PATH="${TOOLS_DIR}/zgrab2/cmd/zgrab2:${PATH}"

RUN git clone --depth 1 https://github.com/github/codeql.git ${TOOLS_DIR}/codeql-queries

# Clone a test project for VECTOR-Code demo
ENV TEST_PROJECT_DIR=/home/${user}/test-project
RUN mkdir -p ${TEST_PROJECT_DIR}
RUN git clone --depth 1 https://github.com/pyca/cryptography.git ${TEST_PROJECT_DIR}/cryptography

USER root
RUN wget -O ${TOOLS_DIR}/cryptobom_forge-1.1.0-py3-none-any.whl https://github.com/Santandersecurityresearch/cryptobom-forge/releases/download/1.1.0/cryptobom_forge-1.1.0-py3-none-any.whl
RUN pip install --break-system-packages --no-deps ${TOOLS_DIR}/cryptobom_forge-1.1.0-py3-none-any.whl
RUN pip install --break-system-packages git+https://github.com/pre-quantum-research/cyclonedx-python-lib.git@cbom
RUN pip install --break-system-packages jsonschema click pyyaml requests packageurl-python sortedcontainers
USER ${user}
# Install dependencies
RUN poetry install

# Cleanup
USER root
RUN apt-get autoclean -y

# Switch back to non-root user
USER ${user}

# Install Doorstop and organize-tool
RUN pipx install doorstop==3.0b10

WORKDIR ${PROJECT_HOME}

CMD ["/bin/bash", "-c", "while true; do sleep 1000; done"]
