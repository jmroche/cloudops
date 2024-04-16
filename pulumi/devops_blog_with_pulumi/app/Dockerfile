FROM python:3.11.5-slim-bookworm

RUN apt-get update && apt-get dist-upgrade -y
# RUN apt-get install -y sqlite3 --no-install-recommends && rm -rf /var/lib/apt/lists/*

RUN useradd flaskblog

WORKDIR /home/flaskblog

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql cryptography

COPY application application
COPY migrations migrations
COPY wsgi.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP wsgi.py

RUN  chown -R flaskblog:flaskblog ./

USER flaskblog

EXPOSE 5000
ENTRYPOINT [ "./boot.sh" ]
