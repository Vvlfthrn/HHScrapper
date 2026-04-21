FROM selenium/standalone-chrome:latest
WORKDIR /

RUN sudo apt-get update
RUN sudo apt-get install -y python3.14-tk python3.14-dev
RUN sudo apt-get clean
RUN sudo rm -rf /var/lib/apt/lists/*

#COPY requirements.txt requirements.txt
RUN pip3 install django telethon psycopg-binary psycopg httpx pytz seleniumbase
