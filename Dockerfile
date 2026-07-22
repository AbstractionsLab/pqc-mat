# syntax=docker/dockerfile:1

FROM golang:1.25 AS go-stage
FROM python:3.11.0

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.0 \
    GOTOOLCHAIN=local

ENV user=vector \
    VECTOR_FOLDER=vector-project
ENV PROJECT_HOME=/home/${user}/${VECTOR_FOLDER}/
ENV TOOLS_DIR=/home/${user}/tools

RUN apt-get update --fix-missing \
    && apt-get install -y --no-install-recommends \
        git bsdmainutils dnsutils cloc unzip curl wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY --from=go-stage /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/${user}/go"
ENV PATH="${GOPATH}/bin:${PATH}"

RUN useradd -ms /bin/bash ${user}


RUN if [ "$(uname -m)" = "x86_64" ]; then \
        curl -L -o /tmp/codeql-linux64.zip https://github.com/github/codeql-cli-binaries/releases/latest/download/codeql-linux64.zip \
        && unzip /tmp/codeql-linux64.zip -d /opt \
        && rm /tmp/codeql-linux64.zip; \
    else \
        echo "Skipping CodeQL CLI installation: not supported on $(uname -m)"; \
    fi
ENV PATH="/opt/codeql:${PATH}"

RUN pip install --break-system-packages git+https://github.com/pre-quantum-research/cyclonedx-python-lib.git@3efcbb9a22ed4235ebb126ad80836deb2a27d25f
RUN pip install --break-system-packages jsonschema click pyyaml requests packageurl-python sortedcontainers

USER ${user}
RUN python3 -m pip install pipx
ENV PATH="/home/${user}/.local/bin:${PATH}"
RUN pipx install "poetry==$POETRY_VERSION"

WORKDIR ${PROJECT_HOME}
COPY --chown=${user}:${user} poetry.lock pyproject.toml ${PROJECT_HOME}
COPY --chown=${user}:${user} . ${PROJECT_HOME}

RUN mkdir -p ${TOOLS_DIR}

RUN git clone --depth 1 https://github.com/testssl/testssl.sh.git --branch 3.3dev ${TOOLS_DIR}/testssl.sh \
    && git -C ${TOOLS_DIR}/testssl.sh checkout 5296954a701dd00240bec32feadffaa7eacb2bba \
    && chmod +x ${TOOLS_DIR}/testssl.sh/testssl.sh

RUN git clone --depth 1 https://github.com/zmap/zgrab2.git --branch v1.0.0 ${TOOLS_DIR}/zgrab2 \
    && git -C ${TOOLS_DIR}/zgrab2 checkout ea734bcf60ef2921684cb522dfb87a07a322afa6 \
    && cd ${TOOLS_DIR}/zgrab2 \
    && make
ENV PATH="${TOOLS_DIR}/zgrab2/cmd/zgrab2:${PATH}"

RUN git clone --depth 1 https://github.com/github/codeql.git ${TOOLS_DIR}/codeql-queries \
    && git -C ${TOOLS_DIR}/codeql-queries checkout 5690ec71b0efb11fca5e5566b13e1d848b6d0381

RUN poetry install
RUN poetry env info --path > /home/${user}/.vector-venv-path

USER root
RUN wget -O ${TOOLS_DIR}/cryptobom_forge-1.1.0-py3-none-any.whl \
        https://github.com/Santandersecurityresearch/cryptobom-forge/releases/download/1.1.0/cryptobom_forge-1.1.0-py3-none-any.whl
RUN pip install --break-system-packages --no-deps ${TOOLS_DIR}/cryptobom_forge-1.1.0-py3-none-any.whl
RUN ln -s "$(cat /home/${user}/.vector-venv-path)/bin/vector" /usr/local/bin/vector \
    && rm /home/${user}/.vector-venv-path
RUN apt-get autoclean -y

USER ${user}
WORKDIR ${PROJECT_HOME}
RUN mkdir -p /tmp/.config \
    && ln -s /home/${user}/.config/zgrab2 /tmp/.config/zgrab2
ENV HOME=/tmp

ENTRYPOINT ["vector"]
CMD ["--help"]