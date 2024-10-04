FROM python:3.11-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH="/"

COPY ./poetry.lock /
COPY ./pyproject.toml /

RUN apt-get update -y && apt-get install curl -y \
&& apt install cmake -y \
&& curl -sSL https://install.python-poetry.org | python3 - \
&& poetry config virtualenvs.create false \
&& poetry install \
&& apt-get remove curl -y
# O RUN ACIMA CONFIGURA NOSSO SISTEMA, INSTALA OCURL, INSTALA E CONFIGURA O POETRY e DEPOIS REMOVE O CURL

COPY ./app /app
WORKDIR /app
