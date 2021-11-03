ARG PYTHON_VERSION=3.9.1

FROM python:${PYTHON_VERSION}-alpine
ARG PYTHON_VERSION
RUN echo "Building with Python version $PYTHON_VERSION"

WORKDIR /app

COPY requirements.txt /app/

RUN adduser -h /app -s /bin/false -D -H -u 1000 user && \
    apk add --no-cache --virtual .build gcc musl-dev python3-dev libffi-dev openssl-dev cargo && \
    pip install --no-cache-dir --disable-pip-version-check -r requirements.txt && \
    apk del .build && \
    chown -R user:user /app

# Security context in k8s requires uid as user
USER 1000

COPY --chown=user:user . /app

RUN python -m unittest discover -p '*_test.py'

RUN chmod +x /app/container_start.sh

CMD ["/app/container_start.sh"]