from __future__ import annotations

import asyncio
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    async def _run(self, callback: Callable[[sqlite3.Connection], T], *, write: bool = False) -> T:
        def execute() -> T:
            with self._connect() as connection:
                result = callback(connection)
                if write:
                    connection.commit()
                return result

        if write:
            async with self._write_lock:
                return await asyncio.to_thread(execute)
        return await asyncio.to_thread(execute)

    async def initialize(self) -> None:
        def migrate(connection: sqlite3.Connection) -> None:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL DEFAULT '',
                    photo_url TEXT,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS users_username_ci
                    ON users(lower(username)) WHERE username IS NOT NULL;
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id INTEGER NOT NULL REFERENCES users(id),
                    join_enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_members (
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('owner','member')),
                    joined_at TEXT NOT NULL,
                    PRIMARY KEY(project_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS project_invites (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    code TEXT NOT NULL UNIQUE,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    invited_user_id INTEGER REFERENCES users(id),
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','accepted','revoked')),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'Средний',
                    due TEXT NOT NULL DEFAULT '',
                    time TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Запланировано',
                    done INTEGER NOT NULL DEFAULT 0,
                    assignee_id INTEGER REFERENCES users(id),
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    position INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checklist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL DEFAULT 0
                );
            """)

        await self._run(migrate, write=True)

    async def upsert_user(self, profile: dict[str, Any]) -> int:
        telegram_id = int(profile["id"])

        def query(connection: sqlite3.Connection) -> int:
            timestamp = now()
            connection.execute("""
                INSERT INTO users(telegram_id, username, first_name, last_name, photo_url, created_at, last_seen_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username=excluded.username, first_name=excluded.first_name,
                    last_name=excluded.last_name, photo_url=COALESCE(excluded.photo_url, users.photo_url),
                    last_seen_at=excluded.last_seen_at
            """, (telegram_id, profile.get("username"), profile.get("first_name") or "Пользователь",
                  profile.get("last_name") or "", profile.get("photo_url"), timestamp, timestamp))
            return int(connection.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()["id"])

        return await self._run(query, write=True)

    @staticmethod
    def _user(row: sqlite3.Row, prefix: str = "") -> dict[str, Any]:
        first = row[f"{prefix}first_name"]
        last = row[f"{prefix}last_name"]
        return {"id": str(row[f"{prefix}id"]), "telegramId": str(row[f"{prefix}telegram_id"]),
                "username": row[f"{prefix}username"], "firstName": first, "lastName": last,
                "name": f"{first} {last}".strip(), "photoUrl": row[f"{prefix}photo_url"]}

    def _project(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        member_rows = connection.execute("""
            SELECT u.id,u.telegram_id,u.username,u.first_name,u.last_name,u.photo_url,pm.role
            FROM project_members pm JOIN users u ON u.id=pm.user_id
            WHERE pm.project_id=? ORDER BY pm.role='owner' DESC, u.first_name
        """, (row["id"],)).fetchall()
        members = [{**self._user(member), "role": member["role"]} for member in member_rows]
        return {"id": row["id"], "name": row["name"], "ownerId": str(row["owner_id"]),
                "joinEnabled": bool(row["join_enabled"]), "members": members, "memberCount": len(members)}

    def _tasks(self, connection: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
        rows = connection.execute("""
            SELECT t.* FROM tasks t JOIN project_members pm ON pm.project_id=t.project_id
            WHERE pm.user_id=? ORDER BY t.position,t.created_at
        """, (user_id,)).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            checklist = connection.execute(
                "SELECT text,done FROM checklist_items WHERE task_id=? ORDER BY position,id", (row["id"],)
            ).fetchall()
            result.append({"id": row["id"], "title": row["title"], "project": row["project_id"],
                           "description": row["description"], "priority": row["priority"], "due": row["due"],
                           "time": row["time"], "status": row["status"], "done": bool(row["done"]),
                           "assigneeId": str(row["assignee_id"]) if row["assignee_id"] else "",
                           "checklist": [{"text": item["text"], "done": bool(item["done"])} for item in checklist]})
        return result

    async def bootstrap(self, user_id: int) -> dict[str, Any]:
        def query(connection: sqlite3.Connection) -> dict[str, Any]:
            user_row = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            project_rows = connection.execute("""
                SELECT p.* FROM projects p JOIN project_members pm ON pm.project_id=p.id
                WHERE pm.user_id=? ORDER BY p.created_at DESC
            """, (user_id,)).fetchall()
            invite_rows = connection.execute("""
                SELECT i.id,i.code,p.name,u.first_name,u.last_name FROM project_invites i
                JOIN projects p ON p.id=i.project_id JOIN users u ON u.id=i.created_by
                WHERE i.invited_user_id=? AND i.status='active' ORDER BY i.created_at DESC
            """, (user_id,)).fetchall()
            notices = [{"id": row["id"], "title": f"Приглашение в «{row['name']}»",
                        "text": f"{row['first_name']} {row['last_name']} приглашает вас в проект.",
                        "read": False, "inviteCode": row["code"]} for row in invite_rows]
            return {"user": self._user(user_row), "projects": [self._project(connection, row) for row in project_rows],
                    "tasks": self._tasks(connection, user_id), "notices": notices}

        return await self._run(query)

    async def create_project(self, user_id: int, name: str) -> str:
        def query(connection: sqlite3.Connection) -> str:
            project_id = str(uuid.uuid4())
            connection.execute("INSERT INTO projects(id,name,owner_id,created_at) VALUES(?,?,?,?)",
                               (project_id, name[:100], user_id, now()))
            connection.execute("INSERT INTO project_members(project_id,user_id,role,joined_at) VALUES(?,?,?,?)",
                               (project_id, user_id, "owner", now()))
            return project_id
        return await self._run(query, write=True)

    async def set_join_enabled(self, user_id: int, project_id: str, enabled: bool) -> None:
        def query(connection: sqlite3.Connection) -> None:
            cursor = connection.execute("UPDATE projects SET join_enabled=? WHERE id=? AND owner_id=?",
                                        (int(enabled), project_id, user_id))
            if not cursor.rowcount:
                raise PermissionError("Only the project owner can change access")
        await self._run(query, write=True)

    async def create_invite(self, user_id: int, project_id: str, identifier: str | None) -> dict[str, str]:
        def query(connection: sqlite3.Connection) -> dict[str, str]:
            project = connection.execute("SELECT * FROM projects WHERE id=? AND owner_id=?", (project_id, user_id)).fetchone()
            if not project:
                raise PermissionError("Only the project owner can invite members")
            if not project["join_enabled"]:
                raise PermissionError("Сначала откройте присоединение к проекту")
            invited_id = None
            if identifier:
                cleaned = identifier.strip().lstrip("@")
                if cleaned.isdigit():
                    target = connection.execute("SELECT id,telegram_id FROM users WHERE telegram_id=?", (int(cleaned),)).fetchone()
                else:
                    target = connection.execute("SELECT id,telegram_id FROM users WHERE lower(username)=lower(?)", (cleaned,)).fetchone()
                if not target:
                    raise LookupError("Пользователь ещё не запускал Taskflow")
                invited_id = int(target["id"])
                if invited_id == user_id:
                    raise ValueError("Владелец уже состоит в проекте")
                if connection.execute("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (project_id, invited_id)).fetchone():
                    raise ValueError("Пользователь уже состоит в проекте")
            code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()
            invite_id = str(uuid.uuid4())
            connection.execute("""INSERT INTO project_invites(id,project_id,code,created_by,invited_user_id,created_at)
                                VALUES(?,?,?,?,?,?)""", (invite_id, project_id, code, user_id, invited_id, now()))
            result = {"id": invite_id, "code": code, "projectName": project["name"]}
            if identifier and target:
                result["telegramId"] = str(target["telegram_id"])
            return result
        return await self._run(query, write=True)

    async def join_invite(self, user_id: int, code: str) -> str:
        def query(connection: sqlite3.Connection) -> str:
            invite = connection.execute("""SELECT i.*,p.join_enabled FROM project_invites i
                                         JOIN projects p ON p.id=i.project_id WHERE upper(i.code)=upper(?)""", (code,)).fetchone()
            if not invite or invite["status"] == "revoked":
                raise LookupError("Приглашение не найдено или отозвано")
            if not invite["join_enabled"]:
                raise PermissionError("Владелец временно закрыл присоединение к проекту")
            if invite["invited_user_id"] and invite["invited_user_id"] != user_id:
                raise PermissionError("Это приглашение предназначено другому пользователю")
            connection.execute("INSERT OR IGNORE INTO project_members(project_id,user_id,role,joined_at) VALUES(?,?,?,?)",
                               (invite["project_id"], user_id, "member", now()))
            if invite["invited_user_id"]:
                connection.execute("UPDATE project_invites SET status='accepted' WHERE id=?", (invite["id"],))
            return str(invite["project_id"])
        return await self._run(query, write=True)

    @staticmethod
    def _assert_member(connection: sqlite3.Connection, user_id: int, project_id: str) -> None:
        if not connection.execute("SELECT 1 FROM project_members WHERE project_id=? AND user_id=?", (project_id, user_id)).fetchone():
            raise PermissionError("Нет доступа к проекту")

    async def create_task(self, user_id: int, payload: dict[str, Any]) -> str:
        def query(connection: sqlite3.Connection) -> str:
            project_id = str(payload.get("project", "")); self._assert_member(connection, user_id, project_id)
            assignee = int(payload["assigneeId"]) if payload.get("assigneeId") else None
            if assignee is not None:
                self._assert_member(connection, assignee, project_id)
            task_id = str(payload.get("id") or uuid.uuid4()); timestamp = now()
            position = connection.execute("SELECT COALESCE(MAX(position),-1)+1 AS value FROM tasks WHERE project_id=?", (project_id,)).fetchone()["value"]
            connection.execute("""INSERT INTO tasks(id,project_id,title,description,priority,due,time,status,done,assignee_id,created_by,position,created_at,updated_at)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                               (task_id, project_id, str(payload.get("title", ""))[:160], str(payload.get("description", ""))[:4000],
                                payload.get("priority", "Средний"), payload.get("due", ""), payload.get("time", ""),
                                payload.get("status", "Запланировано"), int(bool(payload.get("done"))), assignee, user_id, position, timestamp, timestamp))
            return task_id
        return await self._run(query, write=True)

    async def update_task(self, user_id: int, task_id: str, payload: dict[str, Any]) -> None:
        def query(connection: sqlite3.Connection) -> None:
            task = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task: raise LookupError("Задача не найдена")
            self._assert_member(connection, user_id, task["project_id"])
            assignee_value = payload.get("assigneeId", str(task["assignee_id"] or ""))
            assignee = int(assignee_value) if assignee_value else None
            if assignee is not None: self._assert_member(connection, assignee, task["project_id"])
            values = {key: payload.get(key, task[column]) for key, column in (("title","title"),("description","description"),("priority","priority"),("due","due"),("time","time"),("status","status"))}
            done = int(bool(payload.get("done", task["done"])))
            connection.execute("""UPDATE tasks SET title=?,description=?,priority=?,due=?,time=?,status=?,done=?,assignee_id=?,updated_at=? WHERE id=?""",
                               (values["title"],values["description"],values["priority"],values["due"],values["time"],values["status"],done,assignee,now(),task_id))
            if "checklist" in payload:
                connection.execute("DELETE FROM checklist_items WHERE task_id=?", (task_id,))
                for index, item in enumerate(payload["checklist"]):
                    connection.execute("INSERT INTO checklist_items(task_id,text,done,position) VALUES(?,?,?,?)",
                                       (task_id, str(item.get("text", ""))[:200], int(bool(item.get("done"))), index))
        await self._run(query, write=True)

    async def reorder_tasks(self, user_id: int, tasks: list[dict[str, Any]]) -> None:
        def query(connection: sqlite3.Connection) -> None:
            for position, item in enumerate(tasks):
                task = connection.execute("SELECT project_id FROM tasks WHERE id=?", (item.get("id"),)).fetchone()
                if not task: continue
                self._assert_member(connection, user_id, task["project_id"])
                connection.execute("UPDATE tasks SET position=?,status=?,done=?,updated_at=? WHERE id=?",
                                   (position, item.get("status", "Запланировано"), int(bool(item.get("done"))), now(), item["id"]))
        await self._run(query, write=True)

    async def widget_summary(self, telegram_id: int) -> dict[str, Any]:
        def query(connection: sqlite3.Connection) -> dict[str, Any]:
            user = connection.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
            if not user: return {"name": "Пользователь", "tasks": [], "project_count": 0}
            rows = connection.execute("""SELECT t.title,t.time,t.done,p.name AS project_name FROM tasks t
                JOIN projects p ON p.id=t.project_id WHERE t.assignee_id=? ORDER BY t.done,t.due,t.time LIMIT 4""", (user["id"],)).fetchall()
            project_count = connection.execute("SELECT COUNT(*) AS value FROM project_members WHERE user_id=?", (user["id"],)).fetchone()["value"]
            return {"name": user["first_name"], "tasks": [dict(row) for row in rows], "project_count": project_count}
        return await self._run(query)
