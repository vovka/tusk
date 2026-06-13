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
    libgirepository1.0-dev \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-ayatanaappindicator3-0.1 \
    && rm -rf /var/lib/apt/lists/*

RUN echo 'pcm.default pulse\nctl.default pulse' > /root/.asoundrc

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

CMD ["python", "main.py"]
