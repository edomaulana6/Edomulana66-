FROM python:3.12-slim

# Instal FFmpeg di sistem
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

WORKDIR /app
COPY . .

# Instal library python
RUN pip install --no-cache-dir -r requirements.txt

# Perintah menjalankan bot
CMD ["python", "bot.py"]
