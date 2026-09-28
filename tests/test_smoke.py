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

    def test_extract_module_syntax(self) -> None:
        """Проверка корректности синтаксиса и структуры модуля extract.py."""
        extract_path = self.root_dir / "src" / "extract.py"
        spec = importlib.util.spec_from_file_location("extract", extract_path)
        self.assertIsNotNone(spec, "Не удалось создать спецификацию для модуля extract.py")


if __name__ == "__main__":
    unittest.main()
