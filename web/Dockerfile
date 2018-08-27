FROM python:3.7

WORKDIR /usr/src/web

COPY ./web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY utils.py web/ ./

CMD [ "python", "./web.py" ]
