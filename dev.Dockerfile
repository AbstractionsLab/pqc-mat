# syntax=docker/dockerfile:1

# Build zgrab2 stage
FROM golang:1.25 AS go-stage
ENV GOTOOLCHAIN=local
# zgrab2 v1.0.0; fail if the tag is ever moved to a different commit (checkout step)
RUN git clone -q --depth 1 --branch v1.0.0 https://github.com/zmap/zgrab2.git /src/zgrab2 \
    && git -C /src/zgrab2 checkout -q ea734bcf60ef2921684cb522dfb87a07a322afa6 \
    && make -C /src/zgrab2

FROM python:3.12-slim-trixie

# General environment settings
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.3 \
    CODEQL_VERSION=2.26.2 \
    CODEQL_SHA256=f2a7f47f049b9de51977c02c7900b6e2af7587b50aef530a68975a97b136dfd4

# Project settings
ENV user=vector \
    VECTOR_FOLDER=vector-project
ENV PROJECT_HOME=/home/${user}/${VECTOR_FOLDER}/ \
    TOOLS_DIR=/home/${user}/tools

# Install git and bsdmainutils, dnsutils for network tools and cloc for source code
# libssl-dev provides the OpenSSL headers, so that CodeQL resolves <openssl/...> includes in --build-mode=none
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git bsdmainutils dnsutils cloc unzip curl ca-certificates procps libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -ms /bin/bash ${user} && echo "${user} ALL=(ALL) NOPASSWD:ALL" >>/etc/sudoers

# Install CodeQL CLI: only available for x86_64, skip on others.
# The CLI version must be the one used in the commit of the codeql-queries pinned further below. A way to check it:
# Open https://github.com/github/codeql/commit/<hash> and search for
# the earliest codeql-cli/v* tag under the commit message.
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        curl -fsSL -o /tmp/codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/download/v${CODEQL_VERSION}/codeql-linux64.zip \
        && echo "${CODEQL_SHA256}  /tmp/codeql-linux64.zip" | sha256sum -c - \
        && unzip -q /tmp/codeql-linux64.zip -d /opt \
        && rm /tmp/codeql-linux64.zip; \
    else \
        echo "Skipping CodeQL CLI installation: not supported on $(uname -m)"; \
    fi

ENV PATH="/opt/codeql:${PATH}"

# Install cryptobom-forge and its dependencies
COPY cryptobom-requirements.txt /tmp/
RUN pip install --break-system-packages --no-deps -r /tmp/cryptobom-requirements.txt \
    && pip check \
    && rm /tmp/cryptobom-requirements.txt

# Copy the zgrab2 binary and its default blocklist from the Go stage
COPY --from=go-stage /src/zgrab2/cmd/zgrab2/zgrab2 /usr/local/bin/zgrab2
COPY --from=go-stage --chown=${user}:${user} /src/zgrab2/conf/blocklist.conf /home/${user}/.config/zgrab2/blocklist.conf

USER ${user}

# Install pipx and add to PATH
RUN python3 -m pip install pipx==1.17.6
ENV PATH="/home/${user}/.local/bin:${PATH}"

# Install Poetry
RUN pipx install "poetry==$POETRY_VERSION"
RUN poetry completions bash >> ~/.bash_completion

# Install Doorstop
RUN pipx install doorstop==3.0b10 \
    && pipx inject doorstop "setuptools<71"

# Install network analysis tools and source code analysis tools in project directory
RUN mkdir -p ${TOOLS_DIR}

# Fetch a shallow copy of a pinned commit (no stable release exists yet)
RUN git init -q ${TOOLS_DIR}/testssl.sh \
    && git -C ${TOOLS_DIR}/testssl.sh remote add origin https://github.com/testssl/testssl.sh.git \
    && git -C ${TOOLS_DIR}/testssl.sh fetch -q --depth 1 origin 5296954a701dd00240bec32feadffaa7eacb2bba \
    && git -C ${TOOLS_DIR}/testssl.sh checkout -q FETCH_HEAD \
    && rm -rf ${TOOLS_DIR}/testssl.sh/.git \
    && chmod +x ${TOOLS_DIR}/testssl.sh/testssl.sh

RUN git init -q ${TOOLS_DIR}/codeql-queries \
    && git -C ${TOOLS_DIR}/codeql-queries remote add origin https://github.com/github/codeql.git \
    && git -C ${TOOLS_DIR}/codeql-queries fetch -q --depth 1 origin 5690ec71b0efb11fca5e5566b13e1d848b6d0381 \
    && git -C ${TOOLS_DIR}/codeql-queries checkout -q FETCH_HEAD \
    && rm -rf ${TOOLS_DIR}/codeql-queries/.git

# Precompile the inventory queries to avoid compilation by each scan;
# then, make them readable by the host user (by default CodeQL writes them to .codeql/precompiled/ readable only by its owner)
RUN if command -v codeql >/dev/null; then \
        codeql query compile --precompile --threads=0 \
            ${TOOLS_DIR}/codeql-queries/python/ql/src/experimental/cryptography/inventory \
            ${TOOLS_DIR}/codeql-queries/cpp/ql/src/experimental/cryptography/inventory \
        && chmod -R a+rX ${TOOLS_DIR}/codeql-queries; \
    fi

# Clone a test project for VECTOR-Code demo
ENV TEST_PROJECT_DIR=/home/${user}/test-project
RUN mkdir -p ${TEST_PROJECT_DIR}
RUN git clone --depth 1 https://github.com/pyca/cryptography.git --branch 49.0.0 ${TEST_PROJECT_DIR}/cryptography

# Set working directory
WORKDIR ${PROJECT_HOME}

# Copy dependency files first and install dependencies, so that source edits keep this layer cached
COPY poetry.lock pyproject.toml ${PROJECT_HOME}
RUN poetry install --no-root

# Copy project files
COPY . ${PROJECT_HOME}
RUN poetry install --only-root

CMD ["/bin/bash"]
