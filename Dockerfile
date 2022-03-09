ARG PYTHON_VERSION=3.9.10

FROM python:${PYTHON_VERSION}-slim
RUN echo "Building with Python version $PYTHON_VERSION"

ENV PYTHONPATH=/app/deps

RUN apt update && apt upgrade -y

RUN adduser --no-create-home --disabled-login --disabled-password --shell /bin/false --gecos "" --uid 1001 user && \
    mkdir /app && \
    chown user:user /app

USER user

WORKDIR /app

COPY --chown=user:user requirements.txt /app
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt -t /app/deps

COPY --chown=user:user . /app
RUN python -m unittest discover -p '*_test.py' && \
    chmod +x /app/container_start.sh

CMD ["/app/container_start.sh"]