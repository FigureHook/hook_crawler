FROM python:3.9-buster

EXPOSE 6800

ENV POETRY_VERSION=1.1.8

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /workspace

COPY poetry.lock .
COPY pyproject.toml .
COPY hook_crawlers hook_crawlers/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

WORKDIR /workspace/hook_crawlers

CMD /bin/bash scrapyd_start.sh run
