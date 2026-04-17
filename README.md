# QDroid
Android ADB-клиент на Python3 для QEMU

<img src="img/screen1" alt="" width="50%">

## Пример использования:

Запустите QEMU:
'''
qemu-system-i386 -cdrom path/to/android.iso
'''
<img src="img/screen2" alt="" width="50%">

Создание и подключение ADB клиента
'''
from droid import AndroidADBClient
adb = AndroidADBClient()
adb.connect_device()
'''

Выполнение команды
'''
version = adb.run_adb_command("getprop ro.build.version.release")
print(f"Версия Android: {version}")
'''

Установка APK
'''
adb.install_apk("path/to/app.apk")
'''

Копирование файла с устройства
'''
adb.pull_file("/data/local/tmp/file.txt", "downloaded_file.txt")
'''