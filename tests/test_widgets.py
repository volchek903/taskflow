from __future__ import annotations

import sys
import types
import unittest

try:
    import aiohttp  # noqa: F401
except ModuleNotFoundError:
    sys.modules["aiohttp"] = types.SimpleNamespace()

from bot.app import COMMANDS, render_widget


class WidgetTest(unittest.TestCase):
    def test_every_bot_command_renders_real_state(self) -> None:
        state = {
            "user": {"id": "1", "telegramId": "10", "firstName": "Анна", "lastName": "Тест",
                     "name": "Анна Тест", "username": "anna"},
            "projects": [{"id": "p1", "name": "Запуск", "memberCount": 1,
                          "members": [{"firstName": "Анна", "lastName": "Тест"}]}],
            "tasks": [{"id": "t1", "title": "Проверить виджет", "project": "p1", "due": "",
                       "time": "12:00", "done": False}],
            "notices": [{"title": "Приглашение", "text": "Вас пригласили"}],
        }
        for command in COMMANDS:
            with self.subTest(command=command):
                result = render_widget(command, state)
                self.assertIn("TASKFLOW", result)
                self.assertNotIn("{{", result)


if __name__ == "__main__":
    unittest.main()
