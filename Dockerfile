FROM python:3.11-slim
LABEL authors="halone AKA kirill"
RUN pip install -r req.t

ENTRYPOINT ["python", "main.py"]