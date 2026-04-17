import os
import time
import pytest
from droid import AndroidADBClient, LogcatCollector, AndroidQEMUManager

# Фикстура для создания ADB клиента
@pytest.fixture(scope="session")
def adb_client():
    client = AndroidADBClient()
    client.connect_device(max_attempts=10, delay=5)
    yield client
    client.device = None

# Фикстура для менеджера QEMU
@pytest.fixture(scope="session")
def qemu_manager(iso_path="android.iso"):
    manager = AndroidQEMUManager(iso_path)
    yield manager
    manager.cleanup()

# TC001: Проверка базового подключения ADB
def test_adb_connection(adb_client):
    assert adb_client.device is not None
    assert adb_client.device.serial is not None
    print("ADB успешно подключено")

# TC002: Проверка выполнения базовой команды
def test_execute_basic_command(adb_client):
    version = adb_client.run_adb_command("getprop ro.build.version.release")
    assert version.strip() != ""
    print(f"Версия Android: {version.strip()}")

# TC003: Проверка копирования файла
def test_pull_file(adb_client):
    remote_path = "/data/local/tmp/testfile.txt"
    local_path = "file.txt"
    try:
        adb_client.pull_file(remote_path, local_path)
        assert os.path.exists(local_path)
        print("Файл успешно скопирован")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

# TC004: Проверка работы Logcat
def test_logcat_collection(adb_client):
    log_collector = LogcatCollector(adb_client)
    try:
        log_collector.start_logcat()
        time.sleep(5)  # даем время на сбор логов
        assert os.path.exists(log_collector.log_file)
        assert os.path.getsize(log_collector.log_file) > 0
        print("Logcat успешно собирает логи")
    finally:
        log_collector.stop_logcat()
        if os.path.exists(log_collector.log_file):
            os.remove(log_collector.log_file)

# TC005: Проверка базовых системных свойств
def test_system_properties(adb_client):
    boot_completed = adb_client._get_prop("sys.boot_completed")
    assert boot_completed == "1"
    runtime = adb_client._get_prop("ro.product.cpu.abi")
    assert runtime != ""
    print("Системные свойства корректны")

# TC006: Проверка обработки ошибок
def test_error_handling(adb_client):
    with pytest.raises(Exception):
        adb_client.run_adb_command("non_existent_command")
    print("Обработка ошибок работает корректно")

# TC007: Проверка очистки ресурсов
def test_cleanup(qemu_manager):
    qemu_manager.cleanup()
    time.sleep(32)  # ждем завершения процессов
    assert qemu_manager.qemu_process is None
    print("Очистка ресурсов выполнена успешно")
