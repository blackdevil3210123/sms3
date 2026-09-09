FROM python:3.11-slim

WORKDIR /app

# Install pip and procps (for pkill command)
RUN apt-get update && apt-get install -y \
    python3-pip \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY . .

RUN touch bot.log

CMD ["python3", "launcher.py"]
