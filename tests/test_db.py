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


class ProjectCollaborationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Database(str(Path(self.directory.name) / 'taskflow.db'))
        await self.database.initialize()
        self.owner = await self.database.upsert_user({'id': 101, 'first_name': 'Owner', 'username': 'owner'})
        self.member = await self.database.upsert_user({'id': 202, 'first_name': 'Member', 'username': 'member'})
        self.other = await self.database.upsert_user({'id': 303, 'first_name': 'Other'})
        self.project = await self.database.create_project(self.owner, 'Команда')

    async def test_invite_requires_explicit_acceptance_and_assigns_role(self):
        invite = await self.database.create_invite(self.owner, self.project, '@member', 'admin')
        preview = await self.database.preview_invite(self.member, invite['code'])
        self.assertEqual(preview['role'], 'admin')
        state = await self.database.bootstrap(self.member)
        self.assertEqual(state['projects'], [])
        self.assertEqual(state['notices'][0]['role'], 'admin')
        with self.assertRaises(PermissionError):
            await self.database.join_invite(self.other, invite['code'])
        await self.database.join_invite(self.member, invite['code'])
        state = await self.database.bootstrap(self.member)
        self.assertEqual(state['projects'][0]['memberCount'], 2)
        self.assertEqual(next(user['role'] for user in state['projects'][0]['members'] if user['id'] == str(self.member)), 'admin')
        self.assertEqual(state['notices'], [])
        with self.assertRaises(LookupError):
            await self.database.join_invite(self.member, invite['code'])

    async def test_declined_invitation_cannot_be_accepted(self):
        invite = await self.database.create_invite(self.owner, self.project, '@member', 'viewer')
        with self.assertRaises(PermissionError):
            await self.database.decline_invite(self.other, invite['code'])
        await self.database.decline_invite(self.member, invite['code'])
        self.assertEqual((await self.database.bootstrap(self.member))['notices'], [])
        with self.assertRaises(LookupError):
            await self.database.join_invite(self.member, invite['code'])
        public = await self.database.create_invite(self.owner, self.project, None)
        await self.database.decline_invite(self.member, public['code'])
        with self.assertRaises(PermissionError):
            await self.database.join_invite(self.member, public['code'])
        await self.database.join_invite(self.other, public['code'])

    async def test_roles_and_assignment_are_enforced(self):
        with self.assertRaises(PermissionError):
            await self.database.set_member(self.member, self.project, '303', 'admin')
        with self.assertRaises(ValueError):
            await self.database.set_member(self.owner, self.project, '202', 'owner')
        with self.assertRaises(ValueError):
            await self.database.set_member(self.owner, self.project, '101', 'viewer')
        task = {'project': self.project, 'title': 'Баг', 'assigneeId': str(self.member)}
        with self.assertRaises(PermissionError):
            await self.database.create_task(self.owner, task)
        await self.database.set_member(self.owner, self.project, '@member', 'viewer')
        task_id = await self.database.create_task(self.owner, task)
        for operation in (
            self.database.create_task(self.member, task),
            self.database.update_task(self.member, task_id, {'title': 'Изменено'}),
            self.database.reorder_tasks(self.member, [{'id': task_id}]),
            self.database.set_statuses(self.member, self.project, ['Баг']),
        ):
            with self.assertRaises(PermissionError):
                await operation
        with self.assertRaises(PermissionError):
            await self.database.update_task(self.owner, task_id, {'assigneeId': str(self.other)})
        await self.database.set_member(self.owner, self.project, '202', 'admin')
        await self.database.set_statuses(self.member, self.project, ['Баг', 'Готово'])
        await self.database.update_task(self.member, task_id, {'status': 'Баг'})

    async def test_custom_columns_rename_remove_and_completion(self):
        await self.database.set_statuses(self.owner, self.project, ['Новые', 'Баг', 'Готово'])
        task_id = await self.database.create_task(self.owner, {'project': self.project, 'title': 'Ошибка', 'status': 'Баг', 'done': True})
        await self.database.set_statuses(self.owner, self.project, ['Новые', 'Ошибка', 'Готово'], {'Баг': 'Ошибка'})
        state = await self.database.bootstrap(self.owner)
        self.assertEqual(state['tasks'][0]['status'], 'Ошибка')
        self.assertTrue(state['tasks'][0]['done'])
        await self.database.set_statuses(self.owner, self.project, ['Новые', 'Готово'])
        self.assertEqual((await self.database.bootstrap(self.owner))['tasks'][0]['status'], 'Новые')
        for invalid in ([], ['Баг', 'Баг'], ['  '], ['x' * 51]):
            with self.assertRaises(ValueError):
                await self.database.set_statuses(self.owner, self.project, invalid)
        with self.assertRaises(ValueError):
            await self.database.update_task(self.owner, task_id, {'status': 'Не существует'})
        with self.assertRaises(ValueError):
            await self.database.reorder_tasks(self.owner, [{'id': task_id, 'status': 'Не существует'}])
        await self.database.initialize()
        self.assertEqual((await self.database.bootstrap(self.owner))['projects'][0]['statuses'], ['Новые', 'Готово'])

    async def test_legacy_database_migration_preserves_data(self):
        import sqlite3
        invite = await self.database.create_invite(self.owner, self.project, '@member')
        with sqlite3.connect(self.database.path) as connection:
            connection.executescript('''
                CREATE TABLE legacy_members (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('owner','member')),
                    joined_at TEXT NOT NULL, PRIMARY KEY(project_id,user_id));
                INSERT INTO legacy_members SELECT * FROM project_members;
                DROP TABLE project_members;
                ALTER TABLE legacy_members RENAME TO project_members;
                ALTER TABLE projects DROP COLUMN statuses;
                ALTER TABLE project_invites DROP COLUMN role;
            ''')
        await self.database.initialize()
        await self.database.join_invite(self.member, invite['code'])
        await self.database.set_member(self.owner, self.project, '@member', 'admin')
        state = await self.database.bootstrap(self.member)
        self.assertEqual(state['projects'][0]['memberCount'], 2)
        self.assertEqual(state['projects'][0]['statuses'], ['Запланировано', 'В работе', 'Готово'])


if __name__ == "__main__":
    unittest.main()
