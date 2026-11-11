from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from bot.db import Database


class DatabaseTest(unittest.TestCase):
    def test_project_invite_membership_and_task(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as directory:
                database = Database(str(Path(directory) / "taskflow.db"))
                await database.initialize()
                owner = await database.upsert_user({"id": 101, "first_name": "Owner", "username": "owner"})
                member = await database.upsert_user({"id": 202, "first_name": "Member", "username": "member"})
                project = await database.create_project(owner, "Проект")
                invite = await database.create_invite(owner, project, "@member")
                self.assertEqual(await database.join_invite(member, invite["code"]), project)
                task = {"id": "task-1", "project": project, "title": "Проверить API", "description": "",
                        "priority": "Средний", "due": "", "time": "", "status": "Запланировано",
                        "done": False, "assigneeId": str(member), "checklist": []}
                await database.create_task(owner, task)
                state = await database.bootstrap(member)
                self.assertEqual(state["projects"][0]["memberCount"], 2)
                self.assertEqual(state["tasks"][0]["assigneeId"], str(member))
                public_invite = await database.create_invite(owner, project, None)
                await database.set_join_enabled(owner, project, False)
                third = await database.upsert_user({"id": 303, "first_name": "Third"})
                with self.assertRaises(PermissionError):
                    await database.join_invite(third, public_invite["code"])

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
