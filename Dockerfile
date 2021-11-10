ARG PYTHON_VERSION=3.9.1

FROM python:${PYTHON_VERSION}-slim
RUN echo "Building with Python version $PYTHON_VERSION"

ENV PYTHONPATH=/app/deps

RUN adduser --no-create-home --disabled-login --disabled-password --shell /bin/false --gecos "" --uid 1000 user

# Security context in k8s requires uid as user
USER user

WORKDIR /app

COPY --chown=user:user requirements.txt /app
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt -t /app/deps

COPY --chown=user:user . /app
RUN python -m unittest discover -p '*_test.py' && \
    chmod +x /app/container_start.sh

CMD ["/app/container_start.sh"]