FROM python:3.6.6

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -U -r /app/requirements.txt

CMD ["/app/dev.sh"]