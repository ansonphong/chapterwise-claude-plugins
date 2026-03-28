#!/usr/bin/env python3
"""
feedback.py — CLI tool for querying and managing the ChapterWise feedback table.

Usage:
    python3 feedback.py list [--status=new,triaged] [--category=bug] [--area=website] [--limit=20]
    python3 feedback.py show <id>
    python3 feedback.py update <id> [--status=in_progress] [--priority=high] [--resolution-note="text"]
    python3 feedback.py resolve <id> [--commit=abc123] [--note="Fixed in auth refactor"]
    python3 feedback.py stats

Requires: DATABASE_URL env var, SSH tunnel to production DB.
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 required: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

VALID_STATUSES = {'new', 'triaged', 'in_progress', 'resolved', 'wont_fix'}
VALID_PRIORITIES = {'low', 'medium', 'high', 'critical'}
VALID_CATEGORIES = {'bug', 'feature', 'improvement', 'analysis', 'import', 'other'}
VALID_AREAS = {'website', 'vscode', 'desktop'}


def error_exit(message):
    """Errors go to stderr only (matching plugin convention). Exit code 1."""
    print(message, file=sys.stderr)
    sys.exit(1)


def get_connection():
    url = os.environ.get('DATABASE_URL')
    if not url:
        error_exit("DATABASE_URL not set. Export it or ensure SSH tunnel is running.")
    try:
        return psycopg2.connect(url)
    except psycopg2.OperationalError:
        error_exit("Connection failed — is the SSH tunnel running? (port 15432)")


def resolve_id(conn, id_prefix):
    """Resolve a full or partial UUID to a single feedback ID."""
    if len(id_prefix) < 6:
        error_exit(f"ID prefix too short (min 6 chars): '{id_prefix}'")
    # Use a plain cursor for positional access (avoids RealDictCursor issues)
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM feedback WHERE id::text LIKE %s",
        (id_prefix + '%',)
    )
    rows = cur.fetchall()
    cur.close()
    if len(rows) == 0:
        error_exit(f"No feedback item matching '{id_prefix}'")
    if len(rows) > 1:
        ids = [str(r[0])[:8] for r in rows]
        error_exit(f"Ambiguous ID '{id_prefix}' — matches: {', '.join(ids)}")
    return rows[0][0]


def cmd_list(args):
    statuses = [s.strip() for s in args.status.split(',')]
    for s in statuses:
        if s not in VALID_STATUSES:
            error_exit(f"Invalid status '{s}' — must be one of: {', '.join(sorted(VALID_STATUSES))}")

    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        conditions = ["f.status IN %s"]
        params = [tuple(statuses)]

        if args.category:
            if args.category not in VALID_CATEGORIES:
                error_exit(f"Invalid category '{args.category}' — must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
            conditions.append("f.category = %s")
            params.append(args.category)

        if args.area:
            if args.area not in VALID_AREAS:
                error_exit(f"Invalid area '{args.area}' — must be one of: {', '.join(sorted(VALID_AREAS))}")
            conditions.append("f.product_area = %s")
            params.append(args.area)

        where = " AND ".join(conditions)
        params.append(args.limit)

        sql = f"""
            SELECT f.id, f.category, f.product_area, f.title, f.status,
                   f.priority, f.created_at, u.email AS user_email
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            WHERE {where}
            ORDER BY f.created_at DESC
            LIMIT %s
        """
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

        items = []
        for row in rows:
            item = dict(row)
            item['id'] = str(item['id'])
            item['created_at'] = item['created_at'].isoformat() if item['created_at'] else None
            items.append(item)

        json.dump({"count": len(items), "items": items}, sys.stdout, indent=2)
        print(file=sys.stdout)
    except psycopg2.Error as e:
        error_exit(f"Database error: {e.pgerror or str(e)}")
    finally:
        conn.close()


def cmd_show(args):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        full_id = resolve_id(conn, args.id)

        cur.execute("""
            SELECT f.*, u.email AS user_email
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            WHERE f.id = %s
        """, (full_id,))
        row = cur.fetchone()

        item = dict(row)
        item['id'] = str(item['id'])
        item['user_id'] = str(item['user_id'])
        item['created_at'] = item['created_at'].isoformat() if item['created_at'] else None
        item['updated_at'] = item['updated_at'].isoformat() if item['updated_at'] else None

        json.dump(item, sys.stdout, indent=2)
        print(file=sys.stdout)
    except psycopg2.Error as e:
        error_exit(f"Database error: {e.pgerror or str(e)}")
    finally:
        conn.close()


def cmd_update(args):
    conn = get_connection()
    try:
        cur = conn.cursor()
        full_id = resolve_id(conn, args.id)

        # Build SET clause from provided flags
        updates = []
        params = []
        updated_fields = []

        if args.status:
            if args.status not in VALID_STATUSES:
                error_exit(f"Invalid status '{args.status}' — must be one of: {', '.join(sorted(VALID_STATUSES))}")
            updates.append("status = %s")
            params.append(args.status)
            updated_fields.append('status')

        if args.priority:
            if args.priority not in VALID_PRIORITIES:
                error_exit(f"Invalid priority '{args.priority}' — must be one of: {', '.join(sorted(VALID_PRIORITIES))}")
            updates.append("priority = %s")
            params.append(args.priority)
            updated_fields.append('priority')

        if args.resolution_note:
            updates.append("resolution_note = %s")
            params.append(args.resolution_note)
            updated_fields.append('resolution_note')

        if not updates:
            error_exit("No fields to update. Provide --status, --priority, or --resolution-note.")

        updates.append("updated_at = NOW()")
        params.append(full_id)

        # Conditional update for in_progress (concurrency guard)
        if args.status == 'in_progress':
            sql = f"UPDATE feedback SET {', '.join(updates)} WHERE id = %s AND status IN ('new', 'triaged') RETURNING id"
        else:
            sql = f"UPDATE feedback SET {', '.join(updates)} WHERE id = %s RETURNING id"

        cur.execute(sql, tuple(params))
        result = cur.fetchone()
        conn.commit()

        if result is None and args.status == 'in_progress':
            json.dump({"ok": False, "id": str(full_id), "message": "Item already in_progress or resolved"}, sys.stdout, indent=2)
        else:
            json.dump({"ok": True, "id": str(full_id), "updated_fields": updated_fields}, sys.stdout, indent=2)
        print(file=sys.stdout)
    except psycopg2.Error as e:
        conn.rollback()
        error_exit(f"Database error: {e.pgerror or str(e)}")
    finally:
        conn.close()


def cmd_resolve(args):
    conn = get_connection()
    try:
        cur = conn.cursor()
        full_id = resolve_id(conn, args.id)

        params = ['resolved']
        sets = ["status = %s", "updated_at = NOW()"]

        if args.note:
            sets.append("resolution_note = %s")
            params.append(args.note)

        if args.commit:
            sets.append("resolved_commit = %s")
            params.append(args.commit)

        params.append(full_id)
        sql = f"UPDATE feedback SET {', '.join(sets)} WHERE id = %s"
        cur.execute(sql, tuple(params))
        conn.commit()

        json.dump({"ok": True, "id": str(full_id), "status": "resolved"}, sys.stdout, indent=2)
        print(file=sys.stdout)
    except psycopg2.Error as e:
        conn.rollback()
        error_exit(f"Database error: {e.pgerror or str(e)}")
    finally:
        conn.close()


def cmd_stats(args):
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM feedback")
        total = cur.fetchone()[0]

        cur.execute("SELECT status, COUNT(*) FROM feedback GROUP BY status ORDER BY status")
        by_status = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT category, COUNT(*) FROM feedback GROUP BY category ORDER BY category")
        by_category = {row[0]: row[1] for row in cur.fetchall()}

        cur.execute("SELECT product_area, COUNT(*) FROM feedback GROUP BY product_area ORDER BY product_area")
        by_area = {row[0]: row[1] for row in cur.fetchall()}

        json.dump({
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "by_area": by_area,
        }, sys.stdout, indent=2)
        print(file=sys.stdout)
    except psycopg2.Error as e:
        error_exit(f"Database error: {e.pgerror or str(e)}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="ChapterWise feedback CLI")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # list
    p_list = subparsers.add_parser('list', help='List feedback items')
    p_list.add_argument('--status', default='new,triaged', help='Comma-separated status filter')
    p_list.add_argument('--category', help='Filter by category')
    p_list.add_argument('--area', help='Filter by product area')
    p_list.add_argument('--limit', type=int, default=20, help='Max items to return')

    # show
    p_show = subparsers.add_parser('show', help='Show feedback item details')
    p_show.add_argument('id', help='Full UUID or prefix (min 6 chars)')

    # update
    p_update = subparsers.add_parser('update', help='Update feedback item')
    p_update.add_argument('id', help='Full UUID or prefix (min 6 chars)')
    p_update.add_argument('--status', help='New status')
    p_update.add_argument('--priority', help='New priority')
    p_update.add_argument('--resolution-note', dest='resolution_note', help='Add a resolution note')

    # resolve
    p_resolve = subparsers.add_parser('resolve', help='Mark feedback as resolved')
    p_resolve.add_argument('id', help='Full UUID or prefix (min 6 chars)')
    p_resolve.add_argument('--commit', help='Commit hash')
    p_resolve.add_argument('--note', help='Resolution note')

    # stats
    subparsers.add_parser('stats', help='Show feedback statistics')

    args = parser.parse_args()
    commands = {
        'list': cmd_list,
        'show': cmd_show,
        'update': cmd_update,
        'resolve': cmd_resolve,
        'stats': cmd_stats,
    }
    commands[args.command](args)


if __name__ == '__main__':
    main()
