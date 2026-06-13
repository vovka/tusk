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
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-ayatanaappindicator3-0.1 \
    && rm -rf /var/lib/apt/lists/*

RUN echo 'pcm.default pulse\nctl.default pulse' > /root/.asoundrc

# The tray uses pystray's AppIndicator backend, which needs PyGObject (gi).
# python3-gi installs into the system dist-packages; expose it to the image's
# Python (same 3.11 ABI) instead of building PyGObject from source via pip.
ENV PYTHONPATH=/usr/lib/python3/dist-packages
ENV PYSTRAY_BACKEND=appindicator

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

CMD ["python", "main.py"]
