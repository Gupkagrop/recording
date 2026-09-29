"""Модуль базовых дымовых тестов (smoke tests) для верификации целостности репозитория."""

import importlib.util
import os
import unittest
from pathlib import Path


class TestProjectIntegrity(unittest.TestCase):
    """Набор тестов для проверки структуры проекта и валидности модулей."""

    def setUp(self) -> None:
        """Инициализация путей к ключевым артефактам проекта."""
        self.root_dir = Path(__file__).resolve().parent.parent

    def test_required_files_exist(self) -> None:
        """Проверка наличия всех обязательных файлов стандарта 2026 года."""
        required_files = [
            "AGENTS.md",
            "GEMINI.md",
            "PROCESSED_VIDEOS.md",
            ".gitignore",
            ".env.example",
            "app_gui.py",
            "src/extract.py",
            "docs/architecture/pipeline.md",
            "docs/architecture/obsidian_vault.md",
        ]
        for rel_path in required_files:
            file_path = self.root_dir / rel_path
            self.assertTrue(
                file_path.exists(),
                f"Обязательный файл {rel_path} отсутствует в репозитории.",
            )

    def test_agents_contract_structure(self) -> None:
        """Проверка структуры и ключевых разделов файла AGENTS.md."""
        agents_file = self.root_dir / "AGENTS.md"
        content = agents_file.read_text(encoding="utf-8")

        expected_sections = [
            "Tech Stack",
            "Commands",
            "Code Standards",
            "Architecture & Pipeline Rules",
            "Prohibited Patterns",
        ]
        for section in expected_sections:
            self.assertIn(
                section,
                content,
                f"Раздел '{section}' отсутствует в файле AGENTS.md.",
            )

    def test_key_invariants_present(self) -> None:
        """Проверка ключевых инвариантов конвейера в AGENTS.md."""
        agents_file = self.root_dir / "AGENTS.md"
        content = agents_file.read_text(encoding="utf-8")

        expected_invariants = [
            "Мультимодальный анализ слайдов",
            "Аббревиатуры дисциплин",
            "Синхронная миграция без потери связей",
            "Active Recall",
            "Дедлайны и ДЗ",
            "Self-Linting",
            "scratch",
        ]
        for inv in expected_invariants:
            self.assertIn(
                inv,
                content,
                f"Ключевой инвариант '{inv}' отсутствует в AGENTS.md.",
            )

    def test_root_directory_cleanliness(self) -> None:
        """Проверка отсутствия посторонних скриптов в корневой директории."""
        allowed_root_py = {"app_gui.py"}
        root_py_files = {
            f.name for f in self.root_dir.glob("*.py") if f.is_file()
        }
        unexpected_files = root_py_files - allowed_root_py
        self.assertEqual(
            unexpected_files,
            set(),
            f"Обнаружены посторонние скрипты в корне проекта: {unexpected_files}. Используйте папку scratch/.",
        )

    def test_extract_module_syntax(self) -> None:
        """Проверка корректности синтаксиса и структуры модуля extract.py."""
        extract_path = self.root_dir / "src" / "extract.py"
        spec = importlib.util.spec_from_file_location("extract", extract_path)
        self.assertIsNotNone(spec, "Не удалось создать спецификацию для модуля extract.py")


if __name__ == "__main__":
    unittest.main()
