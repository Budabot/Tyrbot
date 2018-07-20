FROM python:3.6.6

# Update Software repository
RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y upgrade

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install net-tools

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -U -r /app/requirements.txt

CMD ["/app/dev.sh"]