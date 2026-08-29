# Backup Strategy — بُنيان (Bunyan)

## Overview

This document describes the backup approach for the Bunyan platform (FastAPI + PostgreSQL on Supabase).

---

## 1. Database Backups

### Supabase Built-in Backups
- Supabase Pro plan: daily automated backups, 7-day retention (Point-in-Time Recovery available on higher tiers)
- Access via Supabase Dashboard → Project → Database → Backups

### Manual Snapshots (before migrations)
Before every schema migration, run a manual export:

```bash
pg_dump "$DATABASE_URL" --no-owner --no-acl -F c -f "backups/db_$(date +%Y%m%d_%H%M%S).dump"
```

Restore with:
```bash
pg_restore --clean --no-owner -d "$DATABASE_URL" backups/db_<timestamp>.dump
```

### Pre-migration File Backups
Before any code change, Python files and HTML files are copied to `backups/phase<N>_<timestamp>/`:

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item main.py, *.html, *.py backups\phaseN_$ts\ -Force
```

---

## 2. Code Backups

- Git repository: all commits tracked locally
- Before each phase, a snapshot is copied to `backups/phase<N>_<timestamp>/`
- Files included: `main.py`, all `*.html`, all `_migrate_*.py`, all `_test_*.py`

---

## 3. What Is NOT Backed Up Here

| Item | Where it lives |
|------|---------------|
| Images / uploads | ImageKit CDN (persistent, no action needed) |
| Environment variables | `.env` file (keep secure, never commit) |
| Supabase schema | Captured by `pg_dump` |

---

## 4. Restore Procedure

1. Stop the server: `Stop-Process -Name uvicorn -Force`
2. Restore DB: `pg_restore --clean --no-owner -d "$DATABASE_URL" backups/db_<ts>.dump`
3. Restore code: `Copy-Item backups\phase<N>_<ts>\main.py . -Force`
4. Start server: `.\venv\Scripts\uvicorn.exe main:app --reload`
5. Run health check: `curl http://localhost:8000/health`

---

## 5. Frequency

| Event | Action |
|-------|--------|
| Before each phase migration | Manual pg_dump + file copy |
| Weekly (production) | Verify Supabase backup exists |
| Before any admin operation | Manual pg_dump |

---

## 6. Security Notes

- `.env` file must NEVER be committed to git (already in `.gitignore`)
- Backup dumps may contain hashed passwords — store securely, not in public repos
- `security_audit_log` table retains login events and rate-limit hits for audit trail
