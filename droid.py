import os
import time
import threading
import subprocess
from ppadb.client import Client as AdbClient


class AndroidADBClient:
    def __init__(self, host="127.0.0.1", port=5037):
        self.client = AdbClient(host=host, port=port)
        self.device = None

    def connect_device(self, max_attempts=30, delay=5):
        for attempt in range(1, max_attempts + 1):
            print(f"Попытка подключения ADB #{attempt}...")
            devices = self.client.devices()

            if devices:
                self.device = devices[0]
                print(f"Подключено к устройству: {self.device.serial}")
                return True

            # Если устройств нет, пробуем удалённое подключение
            try:
                self.client.remote_connect("localhost", 5555)
            except Exception as e:
                print(f"Ошибка remote_connect: {e}")

            time.sleep(delay)

        print("Не удалось подключиться к устройству после всех попыток")
        return False

    def wait_for_device_ready(self, timeout=300, check_interval=10):
        if not self.device:
            print("Устройство не подключено. Сначала подключитесь через connect_device()")
            return False

        start_time = time.time()
        print("Ожидание готовности Android системы...")

        while time.time() - start_time < timeout:
            try:
                # Проверяем статус загрузки системы
                boot_completed = self._get_prop("dev.bootcomplete")
                sys_booted = self._get_prop("sys.boot_completed")
                service_ready = self._check_service_status()

                print(f"Статус загрузки: bootcomplete={boot_completed}, "
                      f"sys.boot_completed={sys_booted}, service_ready={service_ready}")

                if boot_completed == "1" and sys_booted == "1" and service_ready:
                    print("Android система полностью загружена и готова к работе!")
                    return True

            except Exception as e:
                print(f"Ошибка при проверке готовности: {e}")

            time.sleep(check_interval)

        print(f"Таймаут ожидания готовности устройства ({timeout} сек)")
        return False

    def _get_prop(self, prop_name):
        """Получение значения системной свойства через getprop."""
        try:
            result = self.device.shell(f"getprop {prop_name}").strip()
            return result
        except Exception:
            return "none"

    def _check_service_status(self):
        """Проверка статуса ключевых сервисов (Package Manager и Activity Manager)."""
        try:
            pm_status = self.device.shell("service check package").strip()
            am_status = self.device.shell("service check activity").strip()

            # Сервисы считаются доступными, если в ответе нет "not found"
            return "not found" not in pm_status and "not found" not in am_status
        except Exception:
            return False

    def run_adb_command(self, command):
        """Выполнение произвольной ADB команды."""
        if self.device:
            result = self.device.shell(command)
            return result
        else:
            raise Exception("Устройство не подключено")

    def install_apk(self, apk_path):
        """Установка APK файла."""
        if self.device:
            self.device.install(apk_path)
            print(f"APK установлен: {apk_path}")

    def pull_file(self, remote_path, local_path):
        """Копирование файла с устройства."""
        if self.device:
            self.device.pull(remote_path, local_path)
            print(f"Файл скопирован: {remote_path} -> {local_path}")


class LogcatCollector:
    def __init__(self, adb_client):
        self.adb_client = adb_client
        self.logcat_process = None
        self.is_collecting = False
        self.log_file="logcat.log"
    
    def start_logcat(self, filters=None):
        """
        Запуск сбора логов Logcat в фоновом режиме
        filters: список фильтров, например ['*:E', 'MyApp:D']
        """
        if filters is None:
            filters = ['*:I']  # По умолчанию — все информационные сообщения
        
        filter_str = ' '.join(filters)
        logcat_cmd = f"logcat -v threadtime {filter_str}"
        
        def collect_logs():
            with open(self.log_file, 'w', encoding='utf-8') as f:
                self.is_collecting = True
                while self.is_collecting:
                    try:
                        output = self.adb_client.run_adb_command(logcat_cmd)
                        f.write(output)
                        f.flush()
                    except Exception as e:
                        print(f"Ошибка при сборе логов: {e}")
                        break
        
        self.logcat_thread = threading.Thread(target=collect_logs)
        self.logcat_thread.start()
        print(f"Сбор логов запущен. Вывод в файл: {self.log_file}")
    
    def stop_logcat(self):
        """Остановка сбора логов"""
        self.is_collecting = False
        try:
            if self.logcat_thread and self.logcat_thread.is_alive():
                self.logcat_thread.join(timeout=5)
        except AttributeError:
            pass
        print("Сбор логов остановлен")


class AndroidQEMUManager:
    def __init__(self, iso_path):
        self.iso_path = iso_path
        self.qemu_process = None
        self.adb_client = AndroidADBClient()
        self.logcat_collector = LogcatCollector(self.adb_client)

    def setup_and_run(self):
        # Шаг 1: Запуск QEMU
        print("Запуск QEMU...")
        cmd = f"qemu-system-i386 -cdrom {self.iso_path}"
        self.qemu_process = subprocess.Popen(cmd)
        time.sleep(10)

        # Шаг 2: Подключение ADB с повторными попытками
        if not self.adb_client.connect_device(max_attempts=20, delay=10):
            print("Критическая ошибка: не удалось подключиться через ADB")
            return False

        # Шаг 3: Ожидание полной готовности системы
        if not self.adb_client.wait_for_device_ready(timeout=600, check_interval=15):
            print("Ошибка: система не загрузилась в отведённое время")
            return False

        # Шаг 4: Запуск сбора логов
        self.logcat_collector.start_logcat()

        return True
    
    def execute_test_commands(self):
        """Выполнение тестовых ADB команд"""
        if not self.adb_client.device:
            print("ADB не подключён")
            return
        
        commands = [
            "getprop ro.build.version.release",  # Версия Android
            "dumpsys battery",  # Статус батареи
            "pm list packages -3",  # Список установленных приложений
        ]
        
        for cmd in commands:
            print(f"\nВыполняем команду: {cmd}")
            result = self.adb_client.run_adb_command(cmd)
            print(result)
    
    def cleanup(self):
        """Очистка: остановка логов, отключение ADB, завершение QEMU"""
        print("Очистка ресурсов...")
        self.logcat_collector.stop_logcat()
        
        if self.qemu_process:
            self.qemu_process.terminate()
            self.qemu_process.wait()
            print("QEMU остановлен")

if __name__ == "__main__":
    # Создаём менеджер
    manager = AndroidQEMUManager("android.iso")
    time.sleep(5)

    try:
        # Запускаем всю систему
        if manager.setup_and_run():
            print("Система запущена и готова к работе")
            
            # Выполняем тестовые команды
            manager.execute_test_commands()
            
            # Ждём некоторое время для сбора логов
            time.sleep(60)
    finally:
        # Всегда очищаем ресурсы
        manager.cleanup()
