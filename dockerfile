FROM python:3.12.4-slim

# Установка необходимых системных зависимостей
RUN apt-get update && \
    apt-get install -y \
    qemu \
    qemu-system-x86 \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-net-dev \
    libsdl2-ttf-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libsdl1.2-dev \
    libsdl-image1.2-dev \
    libsdl-mixer1.2-dev \
    libsdl-net1.2-dev \
    libsdl-ttf2.0-dev

# Установка необходимых Python-пакетов
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходные файлы
COPY . /app
WORKDIR /app

# Устанавливаем Android ISO образ (build-аргумент)
ARG ANDROID_ISO
ENV ANDROID_ISO_PATH=/app/android-x86.iso

# Копируем ISO образ
COPY ${ANDROID_ISO} ${ANDROID_ISO_PATH}

# Экспозиция портов для ADB
EXPOSE 5037
EXPOSE 5555

# Определяем точку входа
CMD ["python", "droid.py"]
