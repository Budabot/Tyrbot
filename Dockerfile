FROM python:3.9.1

WORKDIR /app

ADD . /app

RUN pip install  --no-cache-dir virtualenv && virtualenv .venv && . .venv/bin/activate && pip install  --no-cache-dir -r requirements.txt

# TODO run tests

FROM python:3.9.1-slim

RUN useradd -u 1000 user
COPY --chown=1000:1000 --from=0 /app /app
RUN pip install  --no-cache-dir virtualenv

# Security context in k8s requires uid as user
USER 1000

WORKDIR /app

CMD ["/app/prod-start.sh"]
