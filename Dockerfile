FROM python:3.14-slim

LABEL org.opencontainers.image.title="socmed-dl"
LABEL org.opencontainers.image.description="Download video/music from 10+ platforms, convert to x265"
LABEL org.opencontainers.image.source="https://github.com/Cefneal/socmed-dl"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update -qq && apt-get install -y -qq ffmpeg curl 2>&1 | tail -3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod +x /usr/local/bin/yt-dlp

COPY . /tmp/socmed-dl
RUN pip install --quiet /tmp/socmed-dl && rm -rf /tmp/socmed-dl

WORKDIR /downloads
VOLUME ["/downloads"]

ENTRYPOINT ["socmed-dl"]
CMD ["--help"]
