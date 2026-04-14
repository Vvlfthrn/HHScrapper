FROM python:slim
WORKDIR /

COPY requirements.txt requirements.txt
#RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*
RUN pip3 install -r requirements.txt
#RUN mkdir hhscraper
#WORKDIR /hhscrapper
