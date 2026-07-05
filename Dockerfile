# bookworm pin: distro python3 must be 3.11 so apt's python3-gi (_gi.so) matches
# the app's 3.11 ABI. trixie ships python3.13 and the compiled _gi won't import.
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
    gcc \
    ffmpeg \
    portaudio19-dev \
    wmctrl \
    xdotool \
    xclip \
    wl-clipboard \
    pulseaudio-utils \
    libpulse-dev \
    libasound2-plugins \
    libglib2.0-bin \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    gir1.2-ayatanaappindicator3-0.1 \
    && rm -rf /var/lib/apt/lists/*

# Heavy layer first: depends only on requirements*, so editing config below
# (asound/ENV/source) never re-downloads torch + CUDA.
WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# system-wide (not /root/.asoundrc) so it applies when the app runs as uid 1000
RUN printf 'pcm.default pulse\nctl.default pulse\n' > /etc/asound.conf

# The tray uses pystray's AppIndicator backend, which needs PyGObject (gi).
# python3-gi installs into the system dist-packages; expose it to the image's
# Python (same 3.11 ABI) instead of building PyGObject from source via pip.
ENV PYTHONPATH=/usr/lib/python3/dist-packages
ENV PYSTRAY_BACKEND=appindicator

# Optional Codex agent backend: drop a static (musl) codex binary at vendor/codex
# to bake it in. A glibc-linked build will NOT run here (bookworm ships glibc
# 2.36); build with `cargo build --release --target x86_64-unknown-linux-musl`.
# Absent -> only the default "tusk" backend is available.
COPY vendor/ /opt/codex-vendor/
RUN if [ -f /opt/codex-vendor/codex ]; then \
        install -m 0755 /opt/codex-vendor/codex /usr/local/bin/codex; \
    fi

COPY . .

# Prepare a container-local codex home before launching (no-op for the tusk backend).
ENTRYPOINT ["/app/docker/codex-entrypoint.sh"]
CMD ["python", "main.py"]
