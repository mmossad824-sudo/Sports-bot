FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

# Hugging Face Spaces require running as a non-root user (UID 1000)
# We also grant write permissions to the user for SQLite matches.db creation
RUN useradd -m -u 1000 user && \
    chown -R user:user /code

USER user

ENV PORT=7860

CMD ["python", "main.py"]
