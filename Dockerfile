FROM python:3.12-slim

WORKDIR /app

# зависимости (кэшируются отдельным слоем)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# код бота
COPY bot.py storage.py ./

# БД живёт в примонтированном томе, а не в образе
ENV DB_PATH=/data/bot.db
VOLUME ["/data"]

# -u: логи сразу видны в docker logs
CMD ["python", "-u", "bot.py"]
