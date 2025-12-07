FROM python:3.11-slim-buster

WORKDIR /Auto-Filter-Bot

# निर्भरताएँ कॉपी करें और इंस्टॉल करें
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# बाकी कोड कॉपी करें
COPY . .

# कंटेनर के पोर्ट 80 को दर्शाता है
EXPOSE 80

# बॉट चलाएँ
CMD ["python", "bot.py"]
