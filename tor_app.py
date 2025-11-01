# Официальный репозиторий: https://github.com/Verity-Freedom/Tor-Portable

import os
import sys
import subprocess
import customtkinter as ctk
import requests
import zipfile
import threading
import webbrowser
import tkinter.filedialog as filedialog
import time
import socket
import tempfile
import shutil

# --- КОНФИГУРАЦИЯ ---
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

INSTALL_DIR = os.path.join(BASE_DIR, "TorPortable")
IPNS_URL = "https://ipfs.io/ipns/k51qzi5uqu5dldod6robuflgitvj276br0xye3adipm3kc0bh17hfiv1e0hnp4/"
DOWNLOAD_URLS = {
    "antidetect": IPNS_URL + "AntiTor_win8+AntiDetect_current.zip",
    "standard": IPNS_URL + "AntiTor_win8+_current.zip",
}
PSIPHON_URL = "https://github.com/Verity-Freedom/Tor-Portable/releases/tag/v1.0"
ZERO_OMEGA_CONFIG_URL = IPNS_URL + "ZeroOmegaOptions-RU.bak"
CHROME_ZEROOMEGA_URL = "https://chromewebstore.google.com/detail/proxy-switchyomega-3-zero/pfnededegaaopdmhkdmcofjmoldfiped"
FIREFOX_ZEROOMEGA_URL = "https://addons.mozilla.org/en-US/firefox/addon/zeroomega/"
WEBRTC_CONTROL_URL = "https://chromewebstore.google.com/detail/webrtc-control/fjkmabmdepjfammlpliljpnbhleegehm"

LAUNCH_SCRIPT, SERVICE_MANAGER, CHANGE_MODE, UPDATER, DISCORD_PATCHER = "", "", "", "", ""
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Попытка импорта psutil для управления процессами
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil не установлен. Установите: pip install psutil")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tor Portable Helper ТЕСТ")
        self.geometry("850x750")
        self.minsize(800, 700)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) 
        self.grid_rowconfigure(1, weight=1)

        self.install_dir = INSTALL_DIR
        self.update_paths()

        self.tor_monitor_running = False
        self.tor_monitor_thread = None
        self.tor_status_lock = threading.Lock()
        self.last_tor_status = {"text": "Проверка...", "color": "gray"}
        
        self.notification_frame = None
        self.notification_timer = None

        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

        self.tab_view.add("1. Установка и Запуск")
        self.tab_view.add("2. Настройка Браузера")
        self.tab_view.add("3. Инструменты")
        self.tab_view.add("4. Тест-драйв")
        self.tab_view.add("Помощь и Ссылки")

        self.create_main_tab()
        self.create_setup_tab()
        self.create_tools_tab()
        self.create_test_tab()
        self.create_help_tab()

        self.check_installation()
        self.after(100, self.start_tor_monitor)

    def update_paths(self):
        global LAUNCH_SCRIPT, SERVICE_MANAGER, CHANGE_MODE, UPDATER, DISCORD_PATCHER
        LAUNCH_SCRIPT = os.path.join(self.install_dir, "AntiTor.cmd")
        SERVICE_MANAGER = os.path.join(self.install_dir, "service-manager.cmd")
        CHANGE_MODE = os.path.join(self.install_dir, "change-mode.cmd")
        UPDATER = os.path.join(self.install_dir, "updater-win10+.cmd")
        DISCORD_PATCHER = os.path.join(self.install_dir, "discord-drover", "drover.exe")

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"- {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
        
    def show_notification(self, message, message_type="info"):
        if self.notification_timer: 
            self.after_cancel(self.notification_timer)
        if self.notification_frame: 
            self.notification_frame.destroy()
        
        colors = {"info": "#3498db", "warning": "#f39c12", "error": "#e74c3c", "success": "#2ecc71"}
        fg_color = colors.get(message_type, "#3498db")
        
        self.notification_frame = ctk.CTkFrame(self, height=40, fg_color=fg_color, corner_radius=8)
        self.notification_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.notification_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.notification_frame, text=message, text_color="white", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkButton(self.notification_frame, text="✕", width=30, height=30, fg_color="transparent", hover_color="#000000", command=self.hide_notification).grid(row=0, column=1, padx=(0, 10), pady=5)
        
        self.notification_timer = self.after(3000, self.hide_notification)
        self.log(f"🔔 {message}")

    def hide_notification(self):
        if self.notification_timer: 
            self.after_cancel(self.notification_timer)
        if self.notification_frame: 
            self.notification_frame.destroy()
        self.notification_frame = None

    def set_ui_state(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in [self.download_button, self.choose_dir_button, self.select_existing_button]:
             if widget: 
                 widget.configure(state=state)

    def choose_install_directory(self):
        directory = filedialog.askdirectory(title="Выберите папку для установки Tor Portable", initialdir=BASE_DIR)
        if directory:
            self.install_dir = directory
            self.update_paths()
            self.install_dir_label.configure(text=f"📁 Выбрано: {self.install_dir}")
            self.log(f"Выбрана папка для установки: {self.install_dir}")
            self.check_installation()
            return True
        return False

    def select_existing_installation(self):
        directory = filedialog.askdirectory(title="Выберите папку с установленным Tor Portable", initialdir="C:\\")
        if directory:
            if os.path.exists(os.path.join(directory, "AntiTor.cmd")):
                self.install_dir = directory
                self.update_paths()
                self.install_dir_label.configure(text=f"📁 Обнаружено: {self.install_dir}")
                self.log(f"Обнаружена существующая установка в: {self.install_dir}")
                self.check_installation()
                return True
            else:
                self.log("❌ В выбранной папке не найден AntiTor.cmd")
                self.show_notification("❌ В выбранной папке не найдена установка Tor Portable", "error")
                return False
        return False

    def check_installation(self):
        has_launch = os.path.exists(LAUNCH_SCRIPT)
        has_updater = os.path.exists(UPDATER)
        if has_launch:
            self.status_label.configure(text="✅ Tor Portable найден!", text_color="lightgreen")
            self.download_button.configure(state="normal", text="Переустановить")
            self.service_manager_button.configure(state="normal")
            self.launch_browser_button.configure(state="normal")
            self.open_folder_button.configure(state="normal")
            self.update_button.configure(state="normal" if has_updater else "disabled")
            self.mode_button.configure(state="normal")
            self.discord_button.configure(state="normal" if os.path.exists(DISCORD_PATCHER) else "disabled")
        else:
            self.status_label.configure(text="❌ Tor Portable не найден", text_color="orange")
            self.download_button.configure(state="normal", text="Скачать и Установить")
            self.service_manager_button.configure(state="disabled")
            self.launch_browser_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.update_button.configure(state="disabled")
            self.mode_button.configure(state="disabled")
            self.discord_button.configure(state="disabled")

    def open_download_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Выбор версии")
        dialog.geometry("550x350")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self)
        ctk.CTkLabel(dialog, text="Выберите версию для скачивания", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text=f"Программа будет установлена в папку:\n{self.install_dir}", text_color="yellow", wraplength=500).pack(pady=5)
        path_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        path_frame.pack(pady=5)
        path_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(path_frame, text="📁 Сменить папку установки", fg_color="gray", hover_color="#555555", width=200, command=lambda: (self.choose_install_directory(), dialog.destroy(), self.open_download_dialog())).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(path_frame, text="🔍 Выбрать существующую установку", fg_color="#3498db", hover_color="#2980b9", width=200, command=lambda: (self.select_existing_installation(), dialog.destroy(), self.open_download_dialog())).grid(row=0, column=1, padx=5, pady=5)
        version_frame = ctk.CTkFrame(dialog)
        version_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(version_frame, text="Скачать Рекомендуемую версию (AntiDetect)", command=lambda: (self.start_download(DOWNLOAD_URLS["antidetect"]), dialog.destroy())).pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(version_frame, text="Нет .exe, антивирусы не ругаются.", text_color="gray").pack()
        ctk.CTkButton(version_frame, text="Скачать Стандартную версию", fg_color="gray", command=lambda: (self.start_download(DOWNLOAD_URLS["standard"]), dialog.destroy())).pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(version_frame, text="Есть .exe, может быть ложная тревога антивируса.", text_color="gray").pack()

    def check_write_permission(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            test_file = os.path.join(directory, "test_write.tmp")
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except Exception as e:
            self.log(f"Ошибка прав на запись: {e}")
            return False

    def start_download(self, url):
        if not self.check_write_permission(self.install_dir):
            self.log(f"❌ Нет прав на запись в папку: {self.install_dir}")
            self.status_label.configure(text="Ошибка прав на запись!", text_color="red")
            self.show_notification("❌ Ошибка: нет прав на запись в выбранную папку", "error")
            return
        self.progress_bar.set(0)
        threading.Thread(target=self.download_and_install, args=(url,), daemon=True).start()

    def download_and_install(self, download_url):
        zip_filename = os.path.join(BASE_DIR, "tor_portable_temp.zip")
        try:
            self.set_ui_state(False)
            self.status_label.configure(text="Скачивание...")
            self.log(f"Начинаю скачивание в: {self.install_dir}")
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                with open(zip_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            progress = downloaded_size / total_size if total_size > 0 else 0
                            self.progress_bar.set(progress)
            
            self.status_label.configure(text="Распаковка...")
            self.log("Скачивание завершено. Распаковываю...")
            
            # Останавливаем Tor перед распаковкой
            self.kill_tor_process()
            time.sleep(2)
            
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(self.install_dir)
            
            self.log(f"Успешно распаковано в '{self.install_dir}'")
            self.show_notification("✅ Установка Tor Portable завершена успешно!", "success")
            self.log("Установка завершена успешно!")
            
        except Exception as e:
            self.status_label.configure(text="Ошибка!", text_color="red")
            self.log(f"ОШИБКА: {e}")
            self.show_notification(f"❌ Ошибка установки: {str(e)}", "error")
        finally:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                self.log("Временный архив удалён.")
            self.check_installation()
            self.set_ui_state(True)

    def is_tor_running(self):
        """Проверяет, запущен ли процесс Tor"""
        if not PSUTIL_AVAILABLE:
            # Альтернативная проверка через netstat
            try:
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                return ':9050' in result.stdout and 'LISTENING' in result.stdout
            except:
                return False
        
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and 'tor.exe' in proc.info['name'].lower():
                    return True
            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def kill_tor_process(self):
        """Завершает все процессы Tor"""
        if not PSUTIL_AVAILABLE:
            # Альтернативный способ через taskkill
            try:
                subprocess.run(['taskkill', '/f', '/im', 'tor.exe'], 
                             capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.log("Процесс Tor завершен (taskkill)")
            except:
                pass
            return
        
        try:
            killed = False
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] and 'tor.exe' in proc.info['name'].lower():
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                        self.log(f"Процесс Tor (PID: {proc.info['pid']}) завершен")
                        killed = True
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        pass
            if not killed:
                self.log("Процесс Tor не найден")
        except Exception as e:
            self.log(f"Ошибка при завершении Tor: {e}")

    def run_script_silent(self, script_path):
        """Запускает скрипт без отображения окна"""
        if not os.path.exists(script_path):
            self.log(f"❌ Файл не найден: {script_path}")
            self.show_notification(f"❌ Файл не найден: {os.path.basename(script_path)}", "error")
            return False
        
        script_name = os.path.basename(script_path)
        working_directory = os.path.dirname(script_path)
        
        try:
            # Для скриптов Tor сначала завершаем существующие процессы
            if script_path in [LAUNCH_SCRIPT, SERVICE_MANAGER, CHANGE_MODE, UPDATER]:
                self.log(f"Завершаем Tor перед запуском {script_name}...")
                self.kill_tor_process()
                time.sleep(2)
            
            self.log(f"Запускаю {script_name} (тихий режим)...")
            
            # Запуск без отображения окна
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            process = subprocess.Popen(
                [script_path],
                cwd=working_directory,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Для service-manager даем больше времени на запуск
            if script_path == SERVICE_MANAGER:
                self.after(8000, self.force_tor_check)
            elif script_path in [LAUNCH_SCRIPT, CHANGE_MODE, UPDATER]:
                self.after(5000, self.force_tor_check)
                
            self.log(f"✅ {script_name} запущен успешно")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка запуска {script_name}: {e}")
            self.show_notification(f"❌ Ошибка запуска {script_name}", "error")
            return False

    def run_script(self, script_path):
        """Основной метод запуска скриптов (для обратной совместимости)"""
        return self.run_script_silent(script_path)

    def _check_tor_status(self):
        try:
            # Сначала проверяем порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if sock.connect_ex(('127.0.0.1', 9050)) != 0:
                return {"text": "❌ Порт 9050 закрыт", "color": "red"}
            sock.close()
            
            # Затем проверяем через Tor Project
            proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}
            
            response = requests.get("https://check.torproject.org/", proxies=proxies, timeout=10)
            if "Congratulations" in response.text:
                return {"text": "✅ Онлайн", "color": "lightgreen"}
            return {"text": "⚠️ Онлайн (не Tor)", "color": "yellow"}
        except requests.exceptions.Timeout:
            return {"text": "❌ Таймаут", "color": "orange"}
        except requests.exceptions.RequestException:
            return {"text": "❌ Ошибка сети", "color": "red"}
        except Exception:
            return {"text": "❌ Офлайн", "color": "orange"}

    def create_main_tab(self):
        tab = self.tab_view.tab("1. Установка и Запуск")
        tab.grid_columnconfigure(0, weight=1)
        
        self.install_dir_label = ctk.CTkLabel(tab, text=f"📍 Текущий путь: {self.install_dir}", text_color="lightblue", wraplength=700)
        self.install_dir_label.pack(pady=(10, 10))
        
        path_buttons_frame = ctk.CTkFrame(tab, fg_color="transparent")
        path_buttons_frame.pack(pady=5)
        path_buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.choose_dir_button = ctk.CTkButton(path_buttons_frame, text="📁 Выбрать папку для установки", fg_color="gray", hover_color="#555555", command=self.choose_install_directory)
        self.choose_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.select_existing_button = ctk.CTkButton(path_buttons_frame, text="🔍 Указать существующую установку", fg_color="#3498db", hover_color="#2980b9", command=self.select_existing_installation)
        self.select_existing_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.status_label = ctk.CTkLabel(tab, text="", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.pack(pady=20)
        
        ctk.CTkLabel(tab, text="Действия с Tor Portable", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 0))
        
        self.download_button = ctk.CTkButton(tab, text="Скачать и Установить", command=self.open_download_dialog, height=40)
        self.download_button.pack(pady=5, padx=20, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(tab, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 10))
        
        self.tor_status_label = ctk.CTkLabel(tab, text="Статус Tor: Проверка...", text_color="gray", font=ctk.CTkFont(size=14))
        self.tor_status_label.pack(pady=5)
        
        self.check_status_button = ctk.CTkButton(tab, text="🔄 Проверить статус Tor", command=self.force_tor_check, fg_color="gray", height=28)
        self.check_status_button.pack(pady=5)
        
        ctk.CTkLabel(tab, text="Запуск Tor Portable", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 0))
        
        self.service_manager_button = ctk.CTkButton(tab, text="Запустить как Службу (Рекомендуется, без окна)", command=lambda: self.run_script_silent(SERVICE_MANAGER), height=40, fg_color="#2ecc71", hover_color="#27ae60", font=ctk.CTkFont(size=14, weight="bold"))
        self.service_manager_button.pack(pady=5, padx=20, fill="x")
        
        self.launch_browser_button = ctk.CTkButton(tab, text="Запустить в обычном режиме (через AntiTor.cmd)", command=lambda: self.run_script_silent(LAUNCH_SCRIPT), height=40)
        self.launch_browser_button.pack(pady=5, padx=20, fill="x")
        
        self.open_folder_button = ctk.CTkButton(tab, text="Открыть папку TorPortable", fg_color="gray", command=lambda: os.startfile(self.install_dir))
        self.open_folder_button.pack(pady=(20, 5), padx=20, fill="x")
        
        self.log_textbox = ctk.CTkTextbox(tab, height=150)
        self.log_textbox.pack(pady=10, padx=20, fill="both", expand=True)
        self.log_textbox.configure(state="disabled")

    def start_tor_monitor(self):
        if self.tor_monitor_running: 
            return
        self.tor_monitor_running = True
        self.tor_monitor_thread = threading.Thread(target=self._tor_monitor_loop, daemon=True)
        self.tor_monitor_thread.start()

    def _tor_monitor_loop(self):
        while self.tor_monitor_running:
            try:
                status = self._check_tor_status()
                with self.tor_status_lock:
                    if status != self.last_tor_status:
                        self.last_tor_status = status
                        self.after(0, self._update_tor_status_gui)
            except Exception as e:
                self.log(f"Ошибка в мониторе Tor: {e}")
            time.sleep(15)

    def _update_tor_status_gui(self):
        with self.tor_status_lock: 
            status = self.last_tor_status
        self.tor_status_label.configure(text=f"Статус Tor: {status['text']}", text_color=status['color'])

    def _force_check_and_update(self):
        self.after(0, lambda: self.tor_status_label.configure(text="Статус Tor: Проверка...", text_color="gray"))
        self.after(0, lambda: self.check_status_button.configure(state="disabled"))
        
        self.log("\n=== ПРОВЕРКА СТАТУСА TOR ===")
        status = self._check_tor_status()
        self.log(f"Результат проверки: {status['text']}")
        
        with self.tor_status_lock: 
            self.last_tor_status = status
        
        self.after(0, self._update_tor_status_gui)
        self.after(0, lambda: self.check_status_button.configure(state="normal"))

    def force_tor_check(self):
        threading.Thread(target=self._force_check_and_update, daemon=True).start()

    def destroy(self):
        self.tor_monitor_running = False
        if self.tor_monitor_thread and self.tor_monitor_thread.is_alive():
            self.tor_monitor_thread.join(timeout=1.0)
        super().destroy()

    def create_setup_tab(self):
        tab = self.tab_view.tab("2. Настройка Браузера")
        frame = ctk.CTkScrollableFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="Шаг 1: Установите расширение ZeroOmega", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkButton(frame, text="Для Chrome / Edge / Opera", command=lambda: webbrowser.open_new_tab(CHROME_ZEROOMEGA_URL)).pack(fill="x", pady=5)
        ctk.CTkButton(frame, text="Для Firefox", command=lambda: webbrowser.open_new_tab(FIREFOX_ZEROOMEGA_URL)).pack(fill="x", pady=5)
        
        ctk.CTkLabel(frame, text="Шаг 2: Загрузите настройки в ZeroOmega", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 10))
        ctk.CTkLabel(frame, text='Откройте настройки расширения -> Import/Export -> вставьте ссылку в поле "Restore from online" -> нажмите Restore.', wraplength=700).pack(anchor="w")
        
        config_frame = ctk.CTkFrame(frame, fg_color="transparent")
        config_frame.pack(fill="x", pady=10)
        config_frame.grid_columnconfigure(0, weight=1)
        
        config_entry = ctk.CTkEntry(config_frame)
        config_entry.insert(0, ZERO_OMEGA_CONFIG_URL)
        config_entry.configure(state="readonly")
        config_entry.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkButton(config_frame, text="Копировать", width=120, command=lambda: (self.clipboard_clear(), self.clipboard_append(ZERO_OMEGA_CONFIG_URL), self.show_notification("📋 Ссылка на конфиг скопирована", "info"))).grid(row=0, column=1, padx=(10, 0))
        
        ctk.CTkLabel(frame, text="Шаг 3 (Важно!): Закройте утечку IP в Chrome-браузерах", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 10))
        ctk.CTkLabel(frame, text='Браузеры на движке Chromium имеют уязвимость WebRTC. Установите это расширение, чтобы её закрыть.', wraplength=700).pack(anchor="w")
        ctk.CTkButton(frame, text="Установить WebRTC Control", fg_color="#e74c3c", hover_color="#c0392b", command=lambda: webbrowser.open_new_tab(WEBRTC_CONTROL_URL)).pack(fill="x", pady=5)

    def create_tools_tab(self):
        tab = self.tab_view.tab("3. Инструменты")
        tab.grid_columnconfigure((0, 1), weight=1)
        
        self.update_button = ctk.CTkButton(tab, text="Обновить Tor Portable", command=lambda: self.run_script_silent(UPDATER))
        self.update_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.mode_button = ctk.CTkButton(tab, text="Сменить режим (Pro/Default)", command=lambda: self.run_script_silent(CHANGE_MODE))
        self.mode_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.discord_button = ctk.CTkButton(tab, text="Разблокировать клиент Discord", command=lambda: self.run_script_silent(DISCORD_PATCHER))
        self.discord_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(tab, text="Скачать Psiphon TM ('Таран')", fg_color="#f39c12", hover_color="#d35400", command=lambda: webbrowser.open_new_tab(PSIPHON_URL)).grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(tab, text="После скачивания Psiphon TM распакуйте его, запустите runme.cmd и выберите режим PROXY в расширении ZeroOmega.", wraplength=700).grid(row=2, column=0, columnspan=2, padx=10, pady=20)

    def create_test_tab(self):
        tab = self.tab_view.tab("4. Тест-драйв")
        frame = ctk.CTkScrollableFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="Разблокировываем ВЕСЬ ИНТЕРНЕТ играючи!", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        tests = [
            ("1. Доступ в Darknet", "Поисковик DuckDuckGo в сети .onion", "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"),
            ("2. Базовый обход (Habr)", "Статья о VPN, заблокированная в РФ", "https://habr.com/ru/articles/849092/"),
            ("3. Обход геоблока (YouTube)", "Видео, недоступное в РФ", "https://www.youtube.com/watch?v=-kcOpyM9cBg"),
            ("4. Обход блокировки Tor (YouTube)", "Видео, блокирующее обычный Tor. Поможет режим 'Pro'", "https://www.youtube.com/watch?v=W9lsWI7zhTY"),
            ("5. 'Финальный босс' (Grok)", "Сайт с максимальной защитой. Потребуется Psiphon TM + режим PROXY", "https://grok.com/")
        ]
        
        for title, desc, url in tests:
            test_frame = ctk.CTkFrame(frame)
            test_frame.pack(fill="x", pady=5)
            test_frame.grid_columnconfigure(0, weight=1)
            
            ctk.CTkLabel(test_frame, text=title, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")
            ctk.CTkLabel(test_frame, text=desc, text_color="gray", wraplength=550).grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
            ctk.CTkButton(test_frame, text="Открыть", width=100, command=lambda u=url: webbrowser.open_new_tab(u)).grid(row=0, column=1, rowspan=2, padx=10)

    def create_help_tab(self):
        tab = self.tab_view.tab("Помощь и Ссылки")
        frame = ctk.CTkScrollableFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="Полезные ссылки из гайда", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(5, 5))
        
        links_frame = ctk.CTkFrame(frame, fg_color="transparent")
        links_frame.pack(fill="x", pady=5)
        links_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(links_frame, text="Видеогайд", command=lambda: webbrowser.open_new_tab("https://ipfs.io/ipfs/bafybeicgytyokctpwsuya66yvzwxnjmahexcgisaivcdxszohprygxvzbq/НОВЫЙ%20обход%20блокировки%20через%20сервера%20TOR%20｜%20AntiTor%20%28TorPortable%29%20%5B8HO9jhADip4%5D.webm")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(links_frame, text="Главная страница (GitHub)", command=lambda: webbrowser.open_new_tab("https://github.com/Verity-Freedom/Tor-Portable")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(links_frame, text="Telegram-канал автора", command=lambda: webbrowser.open_new_tab("https://t.me/Tor_Portable")).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(links_frame, text="Поддержать автора", command=lambda: webbrowser.open_new_tab("https://www.donationalerts.com/r/verity_freedom")).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(frame, text="Частые проблемы и решения", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 10))
        
        problems = {
            "Путь к папке содержит пробелы или кириллицу": "Переместите папку с программой в корень диска, например C:\\TorHelper.", 
            "Антивирус ругается на вирус": "Это ложная тревога. Используйте 'Рекомендуемую версию (AntiDetect)'.", 
            "Низкая скорость / Видео тормозит": "Переключитесь на режим 'Pro' на вкладке 'Инструменты'.", 
            "Сайт не открывается": "Убедитесь, что Tor запущен и выбран правильный режим в ZeroOmega.", 
            "После обновления что-то сломалось": "Переустановите фоновую службу и снова нажмите Restore в настройках ZeroOmega."
        }
        
        for problem, solution in problems.items():
            ctk.CTkLabel(frame, text=f"❓ {problem}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(15, 5))
            ctk.CTkLabel(frame, text=f"💡 {solution}", wraplength=700, justify="left").pack(anchor="w", padx=15)


if __name__ == "__main__":
    app = App()

    app.mainloop()
