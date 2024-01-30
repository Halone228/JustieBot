FROM python:3.11-slim
LABEL authors="halone AKA kirill"
WORKDIR /app/
COPY req.t .
RUN pip install -r req.t


ENTRYPOINT ["python", "main.py"]
