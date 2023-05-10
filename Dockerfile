FROM ubuntu:latest

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev

COPY ./requirements.txt /requirements.txt
COPY ./uboot /uboot
COPY ./config.ini /config.ini

VOLUME dbs configs images
COPY dbs/uboot.sqlite3 /dbs/uboot.sqlite3
COPY ./images /images
COPY ./configs /configs

WORKDIR /

RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3" ]

CMD [ "uboot/core.py" ]
