"""Модуль извлечения аудиодорожки, транскрибации речи и нарезки опорных слайдов из видеофайлов."""

import os
import shutil
import site
import sys
import time
from pathlib import Path
from typing import List

# Добавление путей к бинарным библиотекам NVIDIA CUDA в Windows PATH
venv_site = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".venv",
    "Lib",
    "site-packages",
)
for lib in ["cublas", "cudnn", "cuda_nvrtc"]:
    p = os.path.join(venv_site, "nvidia", lib, "bin")
    if os.path.exists(p):
        os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]
        try:
            os.add_dll_directory(p)
        except Exception:
            pass

import ffmpeg
from faster_whisper import WhisperModel


def extract_audio(video_path: str, temp_audio_path: str) -> None:
    """Извлечение 16-битной PCM аудиодорожки с частотой 16 кГц через ffmpeg."""
    if os.path.exists(temp_audio_path):
        return

    print("Извлечение аудиодорожки...")
    try:
        (
            ffmpeg.input(video_path)
            .output(temp_audio_path, acodec="pcm_s16le", ac=1, ar="16k")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as error:
        err_msg = error.stderr.decode() if error.stderr else str(error)
        print(f"Ошибка ffmpeg (аудио): {err_msg}")
        sys.exit(1)


def transcribe_audio(audio_path: str, transcript_file_path: str) -> None:
    """Транскрибация аудио через модель faster-whisper с сохранением временных меток."""
    if os.path.exists(transcript_file_path):
        return

    print("Транскрибация аудио (faster-whisper GPU CUDA)...")
    try:
        model = WhisperModel("small", device="cuda", compute_type="float16")
    except RuntimeError:
        print("CUDA недоступна. Выполняется переключение на CPU (int8)...")
        model = WhisperModel("small", device="cpu", compute_type="int8")

    segments, _ = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    with open(transcript_file_path, "w", encoding="utf-8") as file:
        for segment in segments:
            start_min = int(segment.start // 60)
            start_sec = int(segment.start % 60)
            file.write(f"[{start_min:02d}:{start_sec:02d}] {segment.text}\n")


def extract_frames(video_path: str, frames_directory: str, video_basename: str) -> None:
    """Извлечение ключевых слайдов на основе умной детекции смены сцен (Scene Change Detection)."""
    if len(os.listdir(frames_directory)) > 0:
        return

    print("Извлечение ключевых слайдов лекции (умная детекция смены сцен)...")
    try:
        # Умный фильтр: смена слайда (scene > 0.05) не чаще 1 раза в 5 сек,
        # либо гарантированный снимок каждые 120 секунд при статичном экране.
        select_expr = "isnan(prev_selected_t)+gte(t-prev_selected_t,5)*(gt(scene,0.05)+gte(t-prev_selected_t,120))"
        (
            ffmpeg.input(video_path)
            .filter("select", select_expr)
            .output(
                os.path.join(frames_directory, f"{video_basename}-frame-%04d.jpg"),
                vsync="vfr",
                qscale=2,
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as error:
        err_msg = error.stderr.decode() if error.stderr else str(error)
        print(f"Предупреждение ffmpeg (scene detection): {err_msg}. Переход на резервный режим...")
        try:
            (
                ffmpeg.input(video_path)
                .filter("fps", fps=1 / 60)
                .output(os.path.join(frames_directory, f"{video_basename}-frame-%04d.jpg"))
                .overwrite_output()
                .run(quiet=True)
            )
        except ffmpeg.Error as fallback_err:
            fallback_msg = fallback_err.stderr.decode() if fallback_err.stderr else str(fallback_err)
            print(f"Критическая ошибка ffmpeg (кадры): {fallback_msg}")
            sys.exit(1)


def extract_content(video_path: str) -> None:
    """Координатор сквозного процесса подготовки данных из видеозаписи."""
    if not os.path.exists(video_path):
        print(f"Ошибка: Видеофайл не найден: {video_path}")
        sys.exit(1)

    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(project_root, "cache", video_basename)

    os.makedirs(cache_dir, exist_ok=True)
    temp_audio = os.path.join(cache_dir, "audio.wav")
    transcript_file = os.path.join(cache_dir, "transcript.txt")
    frames_dir = os.path.join(cache_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    # 1. Извлечение аудио
    extract_audio(video_path, temp_audio)

    # 2. Распознавание речи
    transcribe_audio(temp_audio, transcript_file)

    # 3. Нарезка ключевых слайдов
    extract_frames(video_path, frames_dir, video_basename)

    print(f"\nГотово! Результаты сохранены в:\n{cache_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: uv run python src/extract.py <путь_к_видео>")
        sys.exit(1)
    extract_content(sys.argv[1])
