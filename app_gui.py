import os
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

# Setup NVIDIA DLL paths if available
venv_site = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Lib", "site-packages")
for lib in ['cublas', 'cudnn', 'cuda_nvrtc']:
    p = os.path.join(venv_site, 'nvidia', lib, 'bin')
    if os.path.exists(p):
        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
        try:
            os.add_dll_directory(p)
        except Exception:
            pass

import ffmpeg
from faster_whisper import WhisperModel

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TranscriberApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎙️ Умная Транскрибация Видео")
        self.geometry("800x700")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # 1. Video Paths Header (Label + Button)
        self.frame_paths_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_paths_header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="ew")
        self.frame_paths_header.grid_columnconfigure(0, weight=1)

        self.label_paths = ctk.CTkLabel(self.frame_paths_header, text="Пути к видео:", font=("Segoe UI", 14, "bold"))
        self.label_paths.grid(row=0, column=0, sticky="w")
        
        self.btn_browse_files = ctk.CTkButton(self.frame_paths_header, text="Выбрать видео...", width=120, command=self.browse_files)
        self.btn_browse_files.grid(row=0, column=1, sticky="e")
        
        self.textbox_paths = ctk.CTkTextbox(self, height=100)
        self.textbox_paths.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 2. Save Directory
        self.label_save = ctk.CTkLabel(self, text="Папка для сохранения (txt и кадры):", font=("Segoe UI", 14, "bold"))
        self.label_save.grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.frame_save = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_save.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.frame_save.grid_columnconfigure(0, weight=1)
        
        default_dir = os.path.join(os.path.expanduser("~"), "Documents", "Транскрибации")
        self.entry_save = ctk.CTkEntry(self.frame_save)
        self.entry_save.insert(0, default_dir)
        self.entry_save.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.btn_browse = ctk.CTkButton(self.frame_save, text="Обзор...", width=120, command=self.browse_folder)
        self.btn_browse.grid(row=0, column=1)

        # 3. Checkbox Downloads
        self.checkbox_dl = ctk.CTkCheckBox(self, text="Дополнительно сохранить .txt в папку 'Загрузки'")
        self.checkbox_dl.select()
        self.checkbox_dl.grid(row=4, column=0, padx=20, pady=15, sticky="w")

        # 4. Log Area
        self.textbox_log = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 12))
        self.textbox_log.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")

        # 5. Start Button
        self.btn_start = ctk.CTkButton(self, text="НАЧАТЬ ОБРАБОТКУ", font=("Segoe UI", 16, "bold"), height=40, command=self.start_processing)
        self.btn_start.grid(row=6, column=0, padx=20, pady=20, sticky="ew")

    def browse_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите видео файлы",
            filetypes=[("Видео", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"), ("Все файлы", "*.*")]
        )
        if files:
            current_text = self.textbox_paths.get("1.0", "end-1c").strip()
            # Преобразуем кортеж путей в строку, разделенную переносами
            new_paths = "\n".join(files)
            if current_text:
                self.textbox_paths.insert("end", "\n" + new_paths)
            else:
                self.textbox_paths.insert("end", new_paths)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.entry_save.get())
        if folder:
            self.entry_save.delete(0, 'end')
            self.entry_save.insert(0, folder)

    def log_message(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", message + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")
        self.update_idletasks()

    def start_processing(self):
        paths_text = self.textbox_paths.get("1.0", "end-1c")
        save_dir = self.entry_save.get().strip()
        save_dl = self.checkbox_dl.get() == 1
        
        if not paths_text.strip():
            self.log_message("❌ Ошибка: Введите или выберите хотя бы один путь к видео!")
            return
        if not save_dir:
            self.log_message("❌ Ошибка: Укажите папку для сохранения!")
            return

        self.btn_start.configure(state="disabled", text="ИДЕТ ОБРАБОТКА...")
        self.btn_browse_files.configure(state="disabled")
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("1.0", "end")
        self.textbox_log.configure(state="disabled")
        
        # Start background thread
        thread = threading.Thread(target=self.process_videos, args=(paths_text.split('\n'), save_dir, save_dl))
        thread.daemon = True
        thread.start()

    def process_videos(self, video_paths, save_dir, save_to_downloads):
        try:
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            
            self.log_message("Загрузка модели Whisper (small)...")
            model = WhisperModel("small", device="cuda", compute_type="float16")
            
            for v_path in video_paths:
                v_path = v_path.strip().strip('"').strip("'")
                if not v_path:
                    continue
                if not os.path.exists(v_path):
                    self.log_message(f"Пропуск: файл не найден -> {v_path}")
                    continue
                    
                basename = os.path.splitext(os.path.basename(v_path))[0]
                self.log_message(f"\n--- Обработка: {basename} ---")
                
                temp_audio = f"temp_audio_{basename}.wav".replace(" ", "_")
                
                try:
                    # 1. Извлечение аудио
                    self.log_message("Извлечение аудио дорожки...")
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)
                        
                    (
                        ffmpeg
                        .input(v_path)
                        .output(temp_audio, acodec='pcm_s16le', ac=1, ar='16k')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # 2. Транскрибация
                    self.log_message("Транскрибация аудио в текст (может занять время)...")
                    segments, info = model.transcribe(temp_audio, beam_size=5, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
                    
                    result_text = []
                    for segment in segments:
                        start_min = int(segment.start // 60)
                        start_sec = int(segment.start % 60)
                        line = f"[{start_min:02d}:{start_sec:02d}] {segment.text}"
                        result_text.append(line)
                        self.log_message(line)  # Show progress line by line!
                    
                    full_text = "\n".join(result_text)
                    
                    # 3. Сохранение текста
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, f"{basename}.txt")
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(full_text)
                    self.log_message(f"✅ Текст сохранен в: {save_path}")
                    
                    if save_to_downloads:
                        dl_path = os.path.join(downloads_dir, f"{basename}.txt")
                        with open(dl_path, "w", encoding="utf-8") as f:
                            f.write(full_text)
                        self.log_message(f"✅ Также сохранено в Загрузки: {dl_path}")
                    
                    # 4. Видео составляющая (кадры)
                    self.log_message("Извлечение ключевых кадров (1 раз в минуту)...")
                    frames_dir = os.path.join(save_dir, f"{basename}_кадры")
                    os.makedirs(frames_dir, exist_ok=True)
                    (
                        ffmpeg
                        .input(v_path)
                        .filter('fps', fps=1/60)
                        .output(os.path.join(frames_dir, f"{basename}-frame-%04d.jpg"))
                        .run(quiet=True)
                    )
                    self.log_message(f"✅ Кадры сохранены в: {frames_dir}")
                    
                except Exception as e:
                    self.log_message(f"❌ Ошибка при обработке {basename}: {str(e)}")
                finally:
                    if os.path.exists(temp_audio):
                        os.remove(temp_audio)
                        
            self.log_message("\n🎉 Вся обработка успешно завершена!")
        except Exception as e:
            self.log_message(f"Критическая ошибка: {str(e)}")
        finally:
            self.btn_start.configure(state="normal", text="НАЧАТЬ ОБРАБОТКУ")
            self.btn_browse_files.configure(state="normal")

if __name__ == "__main__":
    app = TranscriberApp()
    app.mainloop()
