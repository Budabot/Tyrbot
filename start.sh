#!/usr/bin/env bash

set -e

UV_VERSION=$(cat UV_VERSION | tr -d '\r')
PYTHON_VERSION=$(cat PYTHON_VERSION | tr -d '\r')
UV_BIN="./uv"

if [ ! -f "$UV_BIN" ]; then
    echo "Downloading uv $UV_VERSION..."
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    if [ "$OS" = "linux" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            TARGET="x86_64-unknown-linux-gnu"
        elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
            TARGET="aarch64-unknown-linux-gnu"
        fi
    elif [ "$OS" = "darwin" ]; then
        if [ "$ARCH" = "x86_64" ]; then
            TARGET="x86_64-apple-darwin"
        elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
            TARGET="aarch64-apple-darwin"
        fi
    fi
    
    if [ -z "$TARGET" ]; then
        echo "Unsupported OS/Arch: $OS / $ARCH"
        exit 1
    fi
    
    URL="https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-$TARGET.tar.gz"
    TMP_DIR=$(mktemp -d)
    curl -sSL -o "$TMP_DIR/uv.tar.gz" "$URL"
    curl -sSL -o "$TMP_DIR/uv.tar.gz.sha256" "$URL.sha256"
    
    EXPECTED_HASH=$(cat "$TMP_DIR/uv.tar.gz.sha256" | awk '{print $1}')
    if command -v sha256sum >/dev/null; then
        ACTUAL_HASH=$(sha256sum "$TMP_DIR/uv.tar.gz" | awk '{print $1}')
    elif command -v shasum >/dev/null; then
        ACTUAL_HASH=$(shasum -a 256 "$TMP_DIR/uv.tar.gz" | awk '{print $1}')
    else
        echo "Cannot find sha256sum or shasum to verify checksum"
        exit 1
    fi
    
    if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
        echo "ERROR: Checksum mismatch"
        rm -rf "$TMP_DIR"
        exit 1
    fi
    
    tar -xzf "$TMP_DIR/uv.tar.gz" -C "$TMP_DIR"
    mv "$TMP_DIR/uv-$TARGET/uv" "$UV_BIN"
    chmod +x "$UV_BIN"
    rm -rf "$TMP_DIR"
fi

if [ -f "venv/pyvenv.cfg" ]; then
    if ! grep -q "uv =" "venv/pyvenv.cfg"; then
        echo "Detected legacy venv. Removing old venv..."
        rm -rf venv
    fi
fi

if [ ! -f "venv/pyvenv.cfg" ]; then
    echo "venv/pyvenv.cfg not found. Creating virtual environment..."
    rm -rf venv
    $UV_BIN venv venv --python $PYTHON_VERSION
fi

$UV_BIN pip install --python venv/bin/python -r requirements.txt

set +e
set -o pipefail -o errexit

while true; do
    venv/bin/python bootstrap.py && exit
    sleep 1
done

