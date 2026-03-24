FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    portaudio19-dev \
    wmctrl \
    xdotool \
    xclip \
    pulseaudio-utils \
    libpulse-dev \
    libasound2-plugins \
    libglib2.0-bin \
    && rm -rf /var/lib/apt/lists/*

RUN echo 'pcm.default pulse\nctl.default pulse' > /root/.asoundrc

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
