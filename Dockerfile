ARG PYTHON_VERSION=3.9.1

# build stage
FROM python:${PYTHON_VERSION}
ARG PYTHON_VERSION
RUN echo "Building with Python version $PYTHON_VERSION"

WORKDIR /app
ENV PYTHONPATH=/app/deps

COPY requirements.txt /app/
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt -t /app/deps

COPY . /app
RUN chmod +x /app/container_start.sh && \
    python -m unittest discover -p '*_test.py'


# run stage
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app
ENV PYTHONPATH=/app/deps

RUN adduser -h /app -s /bin/false -D -H -u 1000 user

# Security context in k8s requires uid as user
USER 1000

COPY --chown=1000:1000 --from=0 /app /app

CMD ["/app/container_start.sh"]