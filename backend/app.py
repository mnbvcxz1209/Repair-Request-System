# app.py
# -*- coding: utf-8 -*-

"""
IC Frontend Backend (Flask)
- LINE Bot webhook (/api/line/webhook)
  * 使用者輸入：{Nickname}您好 → 回傳表單格式
  * 使用者依格式填寫後 → 檢查「學號/工號」是否重複，若不重複則寫入 DB 並綁定 LINE userId
- Web/API 端可依「姓名」或「學號/工號」查到 line_user_id 後推播訊息

"""

from __future__ import annotations

import os
import re
import json
import hmac
import base64
import hashlib
from typing import Optional, Dict, Any
import requests
import pymysql
from dotenv import load_dotenv
from flask_cors import CORS
from flask import Flask, jsonify, request, session
from werkzeug.security import check_password_hash


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip()
EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
POWER_AUTOMATE_URL = os.environ.get("POWER_AUTOMATE_URL")
def get_sharepoint_access_token():
    token_url = ""

    data = {
        "client_id": "<CLIENT_ID>",
        "client_secret": "<CLIENT_SECRET>",
        "grant_type": "client_credentials",
        "scope": ""
    }

    resp = requests.post(token_url, data=data)

    print("STATUS =", resp.status_code)
    print("HEADERS =", resp.headers)
    print("TEXT =", resp.text)

    try:
        body = resp.json()
    except Exception:
        raise RuntimeError("Token API did not return JSON")

    if "access_token" not in body:
        raise RuntimeError(f"Token error: {body}")

    return body["access_token"]



# -------------------------
# DB
# -------------------------
def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", ""),
        port=int(os.getenv("DB_PORT", "")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ic_system"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def ensure_tables() -> None:
     conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS line_users (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  nickname VARCHAR(50) NULL,
                  name VARCHAR(50) NOT NULL,
                  id_no VARCHAR(50) NOT NULL,
                  unit VARCHAR(100) NOT NULL,
                  line_user_id VARCHAR(64) NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uq_id_no (id_no),
                  UNIQUE KEY uq_line_user_id (line_user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
            )
        conn.commit()
    finally:
        conn.close()
def create_sharepoint_item(
    site_url: str,
    list_name: str,
    access_token: str,
    title: str,
    message: str,
    send_to_email: str
):
    endpoint = f"{site_url}/_api/web/lists/GetByTitle('{list_name}')/items"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose"
    }

    payload = {
        "__metadata": {
            "type": f"SP.Data.{list_name}ListItem"
        },
        "Title": title,
        "message": message,
        "send_to_email": send_to_email,
        "is_sent": False
    }

    resp = requests.post(
    endpoint,
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose; charset=utf-8",
    },
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
)


    if resp.status_code not in (200, 201):
        print("[SharePoint ERROR]", resp.status_code, resp.text)
        raise RuntimeError(f"SharePoint error: {resp.text}")

    return resp.json()




# -------------------------
# LINE signature verify
# -------------------------
def verify_line_signature(raw_body: bytes, signature: str) -> bool:
    if not LINE_CHANNEL_SECRET or not signature:
        return False
    mac = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)



def push_line_message(to_user_id: str, text: str):
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN is not set")

    url = ""
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": to_user_id,
        "messages": [{"type": "text", "text": text}]
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)

    print("[LINE] push status =", r.status_code)
    print("[LINE] push resp   =", r.text)

    return r.status_code, r.text
# -------------------------
# LINE push / reply
# -------------------------
def line_push_text(to_user_id: str, text: str) -> None:
    if not LINE_CHANNEL_ACCESS_TOKEN:
        raise RuntimeError("missing env LINE_CHANNEL_ACCESS_TOKEN")
    if not to_user_id:
        raise RuntimeError("missing to_user_id")

    url = ""
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"to": to_user_id, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(f"LINE push failed: {r.status_code} {r.text}")


def reply_text(reply_token: Optional[str], text: str) -> None:
    if not reply_token:
        return
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return

    url = ""
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception:
        pass
@app.post("/api/push")
def api_push():
    # 1) 驗證 API token
    if not require_api_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # 2) 讀 body
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    id_no = (data.get("id_no") or "").strip()
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400
    if not (name or id_no):
        return jsonify({"ok": False, "error": "provide name or id_no"}), 400

    # 3) 查 DB 找 line_user_id
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if id_no:
                cur.execute(
                    "SELECT id, name, id_no, unit, line_user_id FROM line_users WHERE id_no=%s LIMIT 1",
                    (id_no,),
                )
            else:
                # 同名可能多筆：取最新一筆
                cur.execute(
                    "SELECT id, name, id_no, unit, line_user_id FROM line_users WHERE name=%s ORDER BY id DESC LIMIT 1",
                    (name,),
                )

            user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "error": "target not found"}), 404
        if not user.get("line_user_id"):
            return jsonify({"ok": False, "error": "target has no line_user_id"}), 400

        # 4) LINE push
        line_push_text(user["line_user_id"], message)

        return jsonify({
            "ok": True,
            "to": {
                "name": user["name"],
                "id_no": user["id_no"],
                "unit": user["unit"],
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


# -------------------------
# LINE register flow
# -------------------------
HELLO_RE = re.compile(r"^(.{1,20})您好$")  # nickname <= 20 chars


def parse_register_form(text: str) -> Optional[Dict[str, str]]:
    """
    解析使用者貼回來的表單：
      姓名：xxx
      學號/工號：yyy
      單位：zzz
    支援全形/半形冒號與多餘空白。
    """
    def pick(pattern: str) -> str:
        m = re.search(pattern, text, re.MULTILINE)
        return (m.group(1).strip() if m else "")

    name = pick(r"^姓名\s*[：:]\s*(.+)$")
    id_no = pick(r"^學號/工號\s*[：:]\s*(.+)$")
    unit = pick(r"^單位\s*[：:]\s*(.+)$")

    if not (name and id_no and unit):
        return None
    return {"name": name, "id_no": id_no, "unit": unit}


def db_get_line_user_by_name(conn, name: str) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nickname, name, id_no, unit, line_user_id
            FROM line_users
            WHERE name=%s
            ORDER BY id DESC
            LIMIT 1
            """,
            (name,),
        )
        return cur.fetchone()


def db_get_line_user_by_idno(conn, id_no: str) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nickname, name, id_no, unit, line_user_id
            FROM line_users
            WHERE id_no=%s
            LIMIT 1
            """,
            (id_no,),
        )
        return cur.fetchone()


def db_get_line_user_by_lineid(conn, line_user_id: str) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nickname, name, id_no, unit, line_user_id
            FROM line_users
            WHERE line_user_id=%s
            LIMIT 1
            """,
            (line_user_id,),
        )
        return cur.fetchone()


def db_insert_line_user(conn, nickname: Optional[str], name: str, id_no: str, unit: str, line_user_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO line_users (nickname, name, id_no, unit, line_user_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nickname, name, id_no, unit, line_user_id),
        )
        
def get_owner_email(owner_id: int) -> str:
    conn = pymysql.connect(
        host="localhost",
        user="你的db_user",
        password="你的db_password",
        database="你的db_name",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT id_no
                FROM owner_contacts
                WHERE id = %s
            """
            cursor.execute(sql, (owner_id,))
            row = cursor.fetchone()

            if not row:
                raise Exception("owner_id not found")

            return f"{row['id_no']}@cgu.edu.tw"

    finally:
        conn.close()




# -------------------------
# Health
# -------------------------
@app.get("/api/health")
def health():
    return jsonify({"ok": True})


# -------------------------
# Owners 
# -------------------------
@app.get("/api/owners")
def owners():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            
            cur.execute(
                "SELECT id, name, sales, ext, line_user_id FROM owner_contacts ORDER BY id ASC"
            )
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


@app.get("/api/owners/all")
def owners_all():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, sales, ext, line_user_id FROM owner_contacts ORDER BY name ASC"
            )
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


# -------------------------
# Work items 
# -------------------------
@app.get("/api/work-items")
def work_items():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, title_en FROM work_items ORDER BY title ASC")
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


@app.get("/api/work-items/<int:work_item_id>/owners")
def owners_by_work_item(work_item_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT oc.id, oc.name, oc.sales, oc.ext, oc.line_user_id
                FROM work_item_owners wio
                JOIN owner_contacts oc ON oc.id = wio.owner_id
                WHERE wio.work_item_id = %s
                ORDER BY oc.name ASC
                """,
                (work_item_id,),
            )
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


@app.post("/api/work-items")
def create_work_item():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO work_items (title) VALUES (%s)", (title,))
        conn.commit()
        return jsonify({"ok": True})
    except pymysql.err.IntegrityError:
        return jsonify({"error": "title already exists"}), 409
    finally:
        conn.close()


@app.delete("/api/work-items/<int:work_item_id>")
def delete_work_item(work_item_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM work_items WHERE id = %s", (work_item_id,))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


@app.post("/api/work-items/<int:work_item_id>/owners")
def set_work_item_owners(work_item_id: int):
    body = request.get_json(silent=True) or {}
    owner_ids = body.get("ownerIds") or []
    if not isinstance(owner_ids, list):
        return jsonify({"error": "ownerIds must be a list"}), 400

    clean_ids = []
    for x in owner_ids:
        try:
            clean_ids.append(int(x))
        except Exception:
            pass
    clean_ids = sorted(set(clean_ids))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM work_item_owners WHERE work_item_id = %s", (work_item_id,)
            )
            for oid in clean_ids:
                cur.execute(
                    "INSERT INTO work_item_owners (work_item_id, owner_id) VALUES (%s, %s)",
                    (work_item_id, oid),
                )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        conn.close()


# -------------------------
# Auth
# -------------------------
@app.post("/api/auth/login")
def admin_login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username/password required"}), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM admins WHERE username=%s",
                (username,),
            )
            admin = cur.fetchone()

        if not admin or not check_password_hash(admin["password_hash"], password):
            return jsonify({"error": "invalid credentials"}), 401

        session["admin_id"] = admin["id"]
        session["admin_username"] = admin["username"]
        return jsonify({"ok": True, "username": admin["username"]})
    finally:
        conn.close()


@app.post("/api/auth/logout")
def admin_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/auth/me")
def admin_me():
    if not session.get("admin_id"):
        return jsonify({"loggedIn": False})
    return jsonify({"loggedIn": True, "username": session.get("admin_username")})


# -------------------------
# Comments 
# -------------------------
@app.get("/api/comments")
def list_comments():
    work_item_id = request.args.get("work_item_id", type=int)
    owner_id = request.args.get("owner_id", type=int)
    limit = request.args.get("limit", default=50, type=int)

    if limit is None or limit <= 0:
        limit = 50
    if limit > 200:
        limit = 200

    sql = """
        SELECT
            c.id,
            c.name,
            c.work_item_id,
            wi.title AS work_item_title,
            c.owner_id,
            oc.name AS owner_name,
            oc.sales AS owner_sales,
            oc.ext AS owner_ext,
            c.note,
            DATE_FORMAT(c.created_at, '%%Y-%%m-%%dT%%H:%%i:%%s') AS created_at
        FROM comments c
        JOIN work_items wi ON wi.id = c.work_item_id
        JOIN owner_contacts oc ON oc.id = c.owner_id
        WHERE 1=1
    """
    params = []

    if work_item_id:
        sql += " AND c.work_item_id = %s"
        params.append(work_item_id)

    if owner_id:
        sql += " AND c.owner_id = %s"
        params.append(owner_id)

    sql += " ORDER BY c.created_at DESC LIMIT %s"
    params.append(limit)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


# -------------------------
#  API: 依姓名查到 id_no / 單位
# -------------------------
@app.get("/api/people")
def list_people():
    """
    Query params:
      - q: name keyword (optional)
      - limit: default 20
    """
    q = (request.args.get("q") or "").strip()
    limit = request.args.get("limit", default=20, type=int)
    if limit <= 0:
        limit = 20
    if limit > 100:
        limit = 100

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    """
                    SELECT id, nickname, name, id_no, unit
                    FROM line_users
                    WHERE name LIKE %s
                    ORDER BY name ASC
                    LIMIT %s
                    """,
                    (f"%{q}%", limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, nickname, name, id_no, unit
                    FROM line_users
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
        return jsonify({"data": rows})
    finally:
        conn.close()


# -------------------------
#  API: 送留言 → LINE Push
#     - 保留 owner_id 
#     - 新增 name / id_no 
# -------------------------
@app.post("/api/messages")
def send_message():
    if not require_api_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"ok": False, "error": "content required"}), 400

    owner_id = data.get("owner_id")
    name = (data.get("name") or "").strip()
    id_no = (data.get("id_no") or "").strip()

    conn = get_conn()
    try:
        
        if owner_id:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, line_user_id FROM owner_contacts WHERE id=%s",
                    (owner_id,),
                )
                owner = cur.fetchone()

            if not owner:
                return jsonify({"ok": False, "error": "owner not found"}), 404
            if not owner.get("line_user_id"):
                return jsonify({"ok": False, "error": "owner not bound to LINE"}), 400

            line_push_text(owner["line_user_id"], content)
            return jsonify({"ok": True, "mode": "owner_id"})

        
        target = None
        if id_no:
            target = db_get_line_user_by_idno(conn, id_no)
        elif name:
            target = db_get_line_user_by_name(conn, name)

        if not target:
            return jsonify({"ok": False, "error": "target not found (use name or id_no)"}), 404

        line_push_text(target["line_user_id"], content)
        return jsonify({"ok": True, "mode": "line_users", "to": {"name": target["name"], "id_no": target["id_no"]}})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.post("/api/comments")
def create_comment():
    data = request.get_json(force=True) or {}
    print("[DEBUG] /api/comments payload =", data)

    name = (data.get("name") or "").strip()
    contact = (data.get("contact") or "").strip()
    email = (data.get("email") or "").strip()  
    work_item_id = data.get("work_item_id")
    owner_id = data.get("owner_id")
    note = (data.get("note") or "").strip()

    # ---------- 基本驗證 ----------
    if not name:
        return jsonify({"ok": False, "message": "name is required"}), 400

    if not contact:
        return jsonify({"ok": False, "message": "contact is required"}), 400

    if not email:
        return jsonify({"ok": False, "message": "email is required"}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "message": "email format is invalid"}), 400

    if work_item_id is None:
        return jsonify({"ok": False, "message": "work_item_id is required"}), 400
    if owner_id is None:
        return jsonify({"ok": False, "message": "owner_id is required"}), 400

    try:
        work_item_id = int(work_item_id)
        owner_id = int(owner_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "work_item_id and owner_id must be integers"}), 400

    conn = get_conn()
    created_row = None
    target_owner = None
    target_line_user_id = None

    try:
        with conn.cursor() as cur:
            # ---------- 檢查 work_item 存在 ----------
            cur.execute("SELECT id, title FROM work_items WHERE id=%s", (work_item_id,))
            wi = cur.fetchone()
            if wi is None:
                return jsonify({"ok": False, "message": "work_item_id not found"}), 404

            # ---------- 檢查 owner_contacts 存在 + 抓 line_user_id ----------
            cur.execute(
                "SELECT id, name, id_no, line_user_id FROM owner_contacts WHERE id=%s",
                (owner_id,)
            )
            target_owner = cur.fetchone()
            if target_owner is None:
                return jsonify({"ok": False, "message": "owner_id not found"}), 404

            target_line_user_id = target_owner.get("line_user_id")

            # ---------- 寫入 comments ----------
            try:
                cur.execute(
                    """
                    INSERT INTO comments (name, contact, email, work_item_id, owner_id, note, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (name, contact, email, work_item_id, owner_id, note if note else None)
                )
            except Exception as e:
                msg = str(e)
                print("[ERROR] INSERT comments failed:", msg)

                
                if "Unknown column" in msg and "email" in msg:
                    return jsonify({
                        "ok": False,
                        "message": "DB schema missing column 'comments.email'. Please run ALTER TABLE to add it.",
                        "hint_sql": "ALTER TABLE comments ADD COLUMN email VARCHAR(255) NOT NULL AFTER contact;"
                    }), 500

                
                if "Unknown column" in msg and "contact" in msg:
                    return jsonify({
                        "ok": False,
                        "message": "DB schema missing column 'comments.contact'. Please run ALTER TABLE to add it.",
                        "hint_sql": "ALTER TABLE comments ADD COLUMN contact VARCHAR(100) NOT NULL AFTER name;"
                    }), 500

                raise

            conn.commit()
            new_id = cur.lastrowid

            
            cur.execute(
                """
                SELECT
                    c.id,
                    c.name,
                    c.contact,
                    c.email,
                    c.work_item_id,
                    wi.title AS work_item_title,
                    c.owner_id,
                    oc.name AS owner_name,
                    oc.sales AS owner_sales,
                    oc.ext AS owner_ext,
                    c.note,
                    DATE_FORMAT(c.created_at, '%%Y-%%m-%%dT%%H:%%i:%%s') AS created_at
                FROM comments c
                JOIN work_items wi ON wi.id = c.work_item_id
                JOIN owner_contacts oc ON oc.id = c.owner_id
                WHERE c.id = %s
                """,
                (new_id,)
            )
            created_row = cur.fetchone()

       
        line_result = {
            "attempted": True,
            "mode": "owner_id",
            "owner_id": owner_id,
            "owner_name": target_owner.get("name") if target_owner else None,
            "owner_id_no": target_owner.get("id_no") if target_owner else None,
            "to_line_user_id": target_line_user_id,
        }

        print("[DEBUG] owner_id =", owner_id)
        print("[DEBUG] resolved line_user_id =", target_line_user_id)

        if not target_line_user_id:
            line_result["ok"] = False
            line_result["message"] = "owner not bound to LINE (owner_contacts.line_user_id is NULL)"
            print("[LINE] skip:", line_result["message"])
        else:
            msg = (
                " 新留言\n"
                f"事項：{created_row.get('work_item_title')}\n"
                f"留言者：{name}\n"
                f"聯絡方式：{contact}\n"
                f"Email：{email}\n"
                f"內容：{note or '(無內容)'}"
            )
            try:
                status, resp_text = push_line_message(target_line_user_id, msg)
                line_result["ok"] = (200 <= status < 300)
                line_result["status_code"] = status
                line_result["resp"] = resp_text
                print("[LINE] push status =", status)
                print("[LINE] push resp   =", resp_text)
            except Exception as e:
                line_result["ok"] = False
                line_result["error"] = str(e)
                print("[LINE] push exception:", e)

        return jsonify({"ok": True, "data": created_row, "line_push": line_result}), 201

    finally:
        conn.close()
@app.get("/api/owner-work-items")
def get_owner_work_items():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
           
            cur.execute("""
                SELECT
                    oc.id AS owner_id,
                    oc.name AS owner_name,
                    oc.ext AS owner_ext,
                    wi.id AS work_item_id,
                    wi.title AS work_title
                FROM owner_contacts oc
                LEFT JOIN work_item_owners wio
                    ON wio.owner_id = oc.id
                LEFT JOIN work_items wi
                    ON wi.id = wio.work_item_id
                ORDER BY oc.id, wi.id
            """)
            rows = cur.fetchall()

        
        owners_map = {}
        for r in rows:
            oid = r["owner_id"]
            if oid not in owners_map:
                owners_map[oid] = {
                    "id": oid,
                    "name": r.get("owner_name"),
                    "ext": r.get("owner_ext"),
                    "works": []
                }

            
            wid = r.get("work_item_id")
            if wid is not None:
                owners_map[oid]["works"].append({
                    "id": wid,
                    "title": r.get("work_title")
                })

        data = list(owners_map.values())
        return jsonify({"ok": True, "data": data}), 200

    finally:
        conn.close()


@app.route("/api/notify", methods=["POST"])
def notify():
    data = request.get_json(force=True)

    owner_id = data.get("owner_id")
    title = data.get("title", "系統通知")
    message = data.get("message", "")

    if not owner_id:
        return jsonify({"error": "owner_id is required"}), 400

    try:
        #  DB → email
        send_to_email = get_owner_email(owner_id)

        #
        create_sharepoint_item(
            site_url="",
            list_name="TeamsNotifyList",
            title=title,
            message=message,
            send_to_email=send_to_email
        )

        return jsonify({
            "status": "ok",
            "send_to_email": send_to_email
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

        
# -------------------------
#  LINE webhook：註冊 + 綁定
# -------------------------
@app.post("/api/line/webhook")
def line_webhook():
    raw = request.get_data()  # bytes
    signature = request.headers.get("X-Line-Signature", "")

    
    if not verify_line_signature(raw, signature):
        return "bad signature", 400

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return "bad json", 400

    events = payload.get("events") or []
    for ev in events:
        if ev.get("type") != "message":
            continue
        msg = ev.get("message") or {}
        if msg.get("type") != "text":
            continue

        text = (msg.get("text") or "").strip()
        reply_token = ev.get("replyToken")
        user_id = (ev.get("source") or {}).get("userId")

       
        m = HELLO_RE.match(text)
        if m:
            nickname = m.group(1)
            reply_text(
                reply_token,
                f"{nickname}您好\n"
                "請依照下述格式填寫\n"
                "姓名：\n"
                "學號/工號：\n"
                "單位："
            )
            continue

        
        form = parse_register_form(text)
        if form:
            if not user_id:
                reply_text(reply_token, " 無法取得你的 LINE userId，請稍後再試")
                continue

            conn = get_conn()
            try:
                # 你本人已經註冊過（line_user_id 已存在）
                me = db_get_line_user_by_lineid(conn, user_id)
                if me:
                    reply_text(reply_token, " 你已經註冊過了，不需要重複註冊")
                    continue

                # 學號/工號是否重複
                dup = db_get_line_user_by_idno(conn, form["id_no"])
                if dup:
                    reply_text(reply_token, f" 學號/工號已存在（已被 {dup['name']} 註冊）")
                    continue

                # 寫入
                # nickname 目前只會在「您好」那次取得，表單貼回通常不含暱稱，這裡先存 NULL
                db_insert_line_user(conn, None, form["name"], form["id_no"], form["unit"], user_id)
                conn.commit()

                reply_text(reply_token, " 註冊成功！之後管理端可依姓名或學號/工號推播訊息給你。")
            except pymysql.err.IntegrityError:
                # 保險：unique key 競態
                conn.rollback()
                reply_text(reply_token, " 註冊失敗：資料可能已存在（請確認學號/工號是否重複）")
            finally:
                conn.close()
            continue

        # 3) 其他訊息：提示流程
        reply_text(
            reply_token,
            "請先輸入：{暱稱}您好\n"
            "再依格式填寫：\n"
            "姓名：\n"
            "學號/工號：\n"
            "單位："
        )

    return "OK"


if __name__ == "__main__":
    ensure_tables()
    app.run(host="", port=, debug=True)
