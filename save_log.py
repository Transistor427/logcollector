import os
import shutil
import subprocess
import datetime
import tarfile
import psutil
import re

def get_serial_number():
    """Извлекает серийный номер из printer.cfg"""
    try:
        with open("/home/pi/printer_data/config/printer.cfg", "r") as f:
            for line in f:
                if line.startswith("# S/N: ZBS"):
                    match = re.match(r'# S/N: (ZBS\d+)', line)
                    if match:
                        return match.group(1)
    except Exception as e:
        print(f"Ошибка чтения printer.cfg: {str(e)}")
    return "UNKNOWN"  # Значение по умолчанию

def get_usb_mount_point():
    """Находит путь монтирования USB-устройства в базовой директории"""
    base_dir = "/home/pi/printer_data/gcodes/"
    for part in psutil.disk_partitions():
        if (
            part.device.startswith('/dev/sd')  # Ищем только SCSI-устройства
            and part.mountpoint.startswith(base_dir)
            and 'rw' in part.opts.split(',')
        ):
            return part.mountpoint
    return None

def create_logs_folder(serial):
    """Создает директорию для логов с серийным номером и временем"""
    timestamp = datetime.datetime.now().strftime("%d%m%Y_%H%M%S")
    safe_serial = re.sub(r'[^a-zA-Z0-9_-]', '_', serial)  # Санитизация имени
    logs_dir = f"/home/pi/logs_{safe_serial}_{timestamp}"
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir

def copy_log_files(logs_dir):
    """Копирует указанные файлы логов в целевую директорию"""
    log_files = [
        "/home/pi/printer_data/logs/klippy.log",
        "/home/pi/printer_data/logs/moonraker.log",
        "/home/pi/printer_data/logs/KlipperScreen.log",
        "/home/pi/printer_data/logs/crowsnest.log"
    ]

    for log_file in log_files:
        if os.path.exists(log_file):
            shutil.copy2(log_file, logs_dir)

def save_dmesg(logs_dir):
    """Сохраняет вывод dmesg в файл"""
    result = subprocess.run(
        ['dmesg'],
        capture_output=True,
        text=True
    )
    with open(os.path.join(logs_dir, "dmesg.log"), "w") as f:
        f.write(result.stdout)

def save_debug_info(logs_dir):
    """Сохраняет серийный номер и информацию о ядре в debug.log"""
    debug_path = os.path.join(logs_dir, "debug.log")
    serial_number = get_serial_number()  # Используем общую функцию

    # Получение версии ядра
    uname_result = subprocess.run(
        ['uname', '-a'],
        capture_output=True,
        text=True
    )
    kernel_version = uname_result.stdout.strip()

    # Получение списка USB-устройств
    usb_result = subprocess.run(
        ['lsusb'],
        capture_output=True,
        text=True
    )
    usb_list = usb_result.stdout.strip()

    # Получение свободного места
    df_result = subprocess.run(
        ['df', '-h'],
        capture_output=True,
        text=True
    )
    avaible_space = df_result.stdout.strip()

    # Получение информации об оперативной памяти
    ram_result = subprocess.run(
        ['free', '-h'],
        capture_output=True,
        text=True
    )
    ram_space = ram_result.stdout.strip()

    # Получение устройств v4l
    v4l_result = subprocess.run(
        ['find', '/dev/v4l'],
        capture_output=True,
        text=True
    )
    v4l_dev = v4l_result.stdout.strip()

    # Запись в debug.log
    with open(debug_path, "w") as f:
        f.write(f"Серийный номер: {serial_number}\n\n")
        f.write("uname -r\n")
        f.write(f"{kernel_version}\n\n")
        f.write(f"lsusb\n")
        f.write(f"{usb_list}\n\n")
        f.write(f"find /dev/v4l\n")
        f.write(f"{v4l_dev}\n\n")
        f.write(f"df -h\n")
        f.write(f"{avaible_space}\n\n")
        f.write(f"free -h\n")
        f.write(f"{ram_space}\n\n")

def create_and_move_archive(logs_dir, usb_mount_point):
    """Создает архив и перемещает его на USB-накопитель"""
    archive_name = f"{logs_dir}.tar.gz"

    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(logs_dir, arcname=os.path.basename(logs_dir))

    if os.path.exists(usb_mount_point):
        shutil.move(archive_name, usb_mount_point)
    else:
        raise FileNotFoundError(f"Директория монтирования {usb_mount_point} не найдена")

    shutil.rmtree(logs_dir)

def main():
    try:
        usb_mount_point = get_usb_mount_point()
        if not usb_mount_point:
            print("USB-накопитель не подключен или не смонтирован")
            return

        # Получаем серийный номер перед созданием папки
        serial = get_serial_number()
        logs_dir = create_logs_folder(serial)

        copy_log_files(logs_dir)
        save_dmesg(logs_dir)
        save_debug_info(logs_dir)
        create_and_move_archive(logs_dir, usb_mount_point)
        print("Операция успешно завершена")

    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main()
