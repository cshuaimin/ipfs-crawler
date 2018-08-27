FROM python:3.7

WORKDIR /usr/src/crawler

COPY ./crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY utils.py crawler/ ./

CMD [ "python", "./crawler.py" ]
