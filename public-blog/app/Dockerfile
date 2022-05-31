FROM python:3.10.4-slim

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
