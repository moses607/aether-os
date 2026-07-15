# Aether OS — minimal, hardened container image.
# Slim base keeps the attack surface and image size small.
FROM python:3.12-slim

# Don't write .pyc files; stream stdout/stderr straight to the logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create an unprivileged user to run the agent (never run as root).
RUN useradd --create-home --shell /usr/sbin/nologin aether

WORKDIR /app

# Copy the project into the image.
COPY . /app

# Install the package. The base kernel is stdlib-only, so this stays light.
# --no-cache-dir avoids leaving pip's cache in the image layer.
RUN pip install --no-cache-dir . \
    && chown -R aether:aether /app

# Drop privileges for everything below this line.
USER aether

# Default to the Aether CLI; extra args are passed straight through.
ENTRYPOINT ["python", "-m", "aether.cli"]
CMD ["--help"]
