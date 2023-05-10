FROM ubuntu:latest

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev

COPY ./requirements.txt /requirements.txt
COPY ./uboot /uboot
COPY ./config.ini /config.ini

WORKDIR /

RUN mkdir -p dbs && mkdir -p images && mkdir -p configs && pip3 install -r requirements.txt

ENTRYPOINT [ "python3" ]

CMD [ "uboot/core.py" ]
