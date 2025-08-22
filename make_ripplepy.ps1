$ErrorActionPreference = "Stop"

# Create folder
$root = "ripplepy"
if (Test-Path $root) { Remove-Item -Recurse -Force $root }
New-Item -ItemType Directory -Path $root | Out-Null

# ---------- db.py ----------
@'
# db.py
import os, sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "ripple.db")

def apply_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
    PRAGMA journal_mode=WAL;

    CREATE TABLE IF NOT EXISTS assets (
      id INTEGER PRIMARY KEY,
      type TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      raw_text TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS metrics_sessions (
      id INTEGER PRIMARY KEY,
      started_at INTEGER NOT NULL,
      ended_at INTEGER,
      label TEXT,
      stress_before INTEGER,
      stress_after INTEGER
    );

    CREATE TABLE IF NOT EXISTS metrics_events (
      id INTEGER PRIMARY KEY,
      session_id INTEGER NOT NULL,
      ts INTEGER NOT NULL,
      phase TEXT,
      name TEXT,
      ms INTEGER NOT NULL,
      notes TEXT,
      FOREIGN KEY(session_id) REFERENCES metrics_sessions(id)
    );
    """)
    conn.commit()

def get_conn() -> sqlite3.Connection:
    first = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if first:
        apply_schema(conn)
    return conn

@contextmanager
def open_conn():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()
'@ | Set-Content "$root\db.py" -Encoding UTF8

# ---------- metrics.py ----------
@'
# metrics.py
import time, sqlite3
from typing import Optional, Dict

class Metrics:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.session_id: Optional[int] = None
        self._start_times: Dict[str, float] = {}

    def start_session(self, label: str, stress_before: int = 0) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO metrics_sessions (started_at,label,stress_before) VALUES (strftime('%s','now'),?,?)",
            (label, stress_before),
        )
        self.session_id = cur.lastrowid
        self.conn.commit()
        return self.session_id

    def end_session(self, stress_after: int = 0):
        if not self.session_id:
            return
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE metrics_sessions SET ended_at=strftime('%s','now'), stress_after=? WHERE id=?",
            (stress_after, self.session_id),
        )
        self.conn.commit()
        self.session_id = None

    def begin(self, key: str):
        self._start_times[key] = time.perf_counter()

    def end(self, key: str, phase: str, name: str, notes: Optional[str] = None):
        start = self._start_times.get(key)
        if start is None or not self.session_id:
            return
        ms = int((time.perf_counter() - start) * 1000)
        self.log_event(phase, name, ms, notes)
        del self._start_times[key]

    def log_event(self, phase: str, name: str, ms: int, notes: Optional[str] = None):
        if not self.session_id:
            return
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO metrics_events (session_id,ts,phase,name,ms,notes) "
            "VALUES (?,?,?,?,?,?)",
            (self.session_id, int(time.time()), phase, name, ms, notes),
        )
        self.conn.commit()
'@ | Set-Content "$root\metrics.py" -Encoding UTF8

# ---------- search.py ----------
@'
# search.py
import sqlite3
from typing import List, Dict, Optional

def ingest_raw(conn: sqlite3.Connection, raw_text: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assets (type, created_at, raw_text) VALUES (\'conversation\', strftime(\'%s\',\'now\'), ?)",
        (raw_text,),
    )
    conn.commit()
    return cur.lastrowid

def search(conn: sqlite3.Connection, q: Optional[str]) -> List[Dict]:
    sql = "SELECT id, raw_text FROM assets WHERE 1=1"
    params = []
    if q and q.strip():
        sql += " AND raw_text LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC"
    cur = conn.cursor()
    rows = cur.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
'@ | Set-Content "$root\search.py" -Encoding UTF8

# ---------- exporter.py ----------
@'
# exporter.py
import sqlite3, os, json

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset='utf-8'><title>Ripple Metrics</title>
<style>
body{background:#0f1221;color:#e8ecff;font:14px system-ui;margin:0;padding:24px}
.card{background:#121636;border:1px solid #2a2f4a;border-radius:12px;padding:12px;margin:16px auto;max-width:980px}
.chart{height:420px;background:#0c1030;border:1px solid #202757;border-radius:12px}
</style></head><body>
<h2 style='text-align:center'>RipplePy – Metrics</h2>
<div class='card'><h3>Throughput by phase (dot‑line)</h3><svg id='a' class='chart' viewBox='0 0 900 420'></svg></div>
<div class='card'><h3>Sessions: code/time proxy & stress change</h3><svg id='b' class='chart' viewBox='0 0 900 420'></svg></div>
<script>
const sessions={sessions_json};
const events={events_json};

function draw(id, pts, color) {
  const svg=document.getElementById(id), W=900,H=420,p=50,w=W-2*p,h=H-2*p;
  const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y), xmin=0,xmax=Math.max(...xs,1), ymin=0,ymax=Math.max(...ys,1)*1.1;
  const sx=x=>p+(x-xmin)/(xmax-xmin||1)*w, sy=y=>H-p-(y-ymin)/(ymax-ymin||1)*h;
  const g=(t,a)=>{const e=document.createElementNS('http://www.w3.org/2000/svg',t); for(const k in a)e.setAttribute(k,a[k]); svg.appendChild(e); return e;};
  g('rect',{x:0,y:0,width:W,height:H,fill:'none'});
  for(let k=0;k<=5;k++){ const y=sy((ymax/5)*k); g('line',{x1:p,y1:y,x2:W-p,y2:y,stroke:'#2a2f4a'}); }
  g('line',{x1:p,y1:H-p,x2:W-p,y2:H-p,stroke:'#90a0ff'}); g('line',{x1:p,y1:p,x2:p,y2:H-p,stroke:'#90a0ff'});
  g('polyline',{points:pts.map(q=>sx(q.x)+','+sy(q.y)).join(' '), fill:'none', stroke:color, 'stroke-width':2.5});
  pts.forEach(q=>{ g('circle',{cx:sx(q.x), cy:sy(q.y), r:5, fill:'#7ce2a0'}); g('text',{x:sx(q.x)+6,y:sy(q.y)-8,fill:'#cfe0ff','font-size':12}).textContent=q.label; });
}

// A: last session phases
const last = sessions.length ? sessions[sessions.length-1] : null;
const phases = ['Search','Ingest','Validate','Fix'];
const evLast = last ? events.filter(e=>e.sid===last.id) : [];
const ptsA = phases.map((ph,i)=>({x:i,y:evLast.filter(e=>e.phase===ph).reduce((t,e)=>t+e.ms,0)/1000,label:ph}));
draw('a', ptsA, '#f6c177');

// B: each session dot (ms in Fix) & Δstress
const ptsB = sessions.map((s,i)=>{
  const ev = events.filter(e=>e.sid===s.id && e.phase==='Fix');
  const codeSec = Math.round(ev.reduce((t,e)=>t+e.ms,0)/1000);
  const d = (s.sb||0)-(s.sa||0);
  return {x:i+1,y:codeSec,label:`S${i+1} (Δ${d})`};
});
draw('b', ptsB, '#7ce2a0');
</script></body></html>
"""

def export_html(conn: sqlite3.Connection, out_path: str = "metrics.html"):
    cur = conn.cursor()
    sess = cur.execute(
        "SELECT id, started_at, ended_at, label, stress_before, stress_after FROM metrics_sessions ORDER BY id"
    ).fetchall()
    events = cur.execute(
        "SELECT session_id as sid, phase, name, ms FROM metrics_events ORDER BY id"
    ).fetchall()

    sessions_json = json.dumps([dict(x) for x in sess])
    events_json = json.dumps([dict(x) for x in events])

    html = HTML_TEMPLATE.format(sessions_json=sessions_json, events_json=events_json)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)
'@ | Set-Content "$root\exporter.py" -Encoding UTF8

# ---------- app.py ----------
@'
# app.py
import tkinter as tk
from tkinter import messagebox, ttk
from db import open_conn
from search import ingest_raw, search
from metrics import Metrics
from exporter import export_html

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RipplePy — Offline Retrieval + Metrics")
        self.geometry("820x520")
        self.minsize(820, 520)

        self.txt_input = tk.Text(self, height=5)
        self.btn_ingest = ttk.Button(self, text="Ingest", command=self.on_ingest)

        self.txt_search = ttk.Entry(self)
        self.btn_search = ttk.Button(self, text="Search", command=self.on_search)

        self.lst_results = tk.Listbox(self)
        self.btn_export = ttk.Button(self, text="Export Metrics (HTML)", command=self.on_export)

        self.lbl_sb = ttk.Label(self, text="Stress Before")
        self.sb = ttk.Spinbox(self, from_=0, to=10, width=5)
        self.sb.set("5")
        self.lbl_sa = ttk.Label(self, text="Stress After")
        self.sa = ttk.Spinbox(self, from_=0, to=10, width=5)
        self.sa.set("4")

        self.txt_input.place(x=20, y=20, width=560, height=100)
        self.btn_ingest.place(x=600, y=20, width=180, height=30)

        self.txt_search.place(x=20, y=140, width=460, height=28)
        self.btn_search.place(x=490, y=140, width=90, height=28)

        self.lst_results.place(x=20, y=180, width=760, height=260)
        self.btn_export.place(x=20, y=460, width=200, height=30)

        self.lbl_sb.place(x=600, y=60); self.sb.place(x=710, y=60)
        self.lbl_sa.place(x=600, y=90); self.sa.place(x=710, y=90)

    def on_ingest(self):
        txt = self.txt_input.get("1.0", "end").strip()
        if not txt:
            messagebox.showinfo("Info", "Type something first.")
            return
        with open_conn() as conn:
            m = Metrics(conn)
            m.start_session("Ingest", int(self.sb.get()))
            m.begin("ingest")
            ingest_raw(conn, txt)
            m.end("ingest", "Ingest", "raw_text", f"len={len(txt)}")
            m.end_session(int(self.sa.get()))
        self.txt_input.delete("1.0", "end")
        messagebox.showinfo("OK", "Saved.")

    def on_search(self):
        q = self.txt_search.get().strip()
        with open_conn() as conn:
            m = Metrics(conn)
            m.start_session("Search", int(self.sb.get()))
            m.begin("search")
            rows = search(conn, q)
            m.end("search", "Search", q if q else "(all)", f"hits={len(rows)}")
            m.end_session(int(self.sa.get()))
        self.lst_results.delete(0, "end")
        for r in rows:
            self.lst_results.insert("end", f'{r["id"]}: {r["raw_text"][:120]}')

    def on_export(self):
        with open_conn() as conn:
            path = export_html(conn, "metrics.html")
        messagebox.showinfo("Exported", f"Metrics written to:\\n{path}")

if __name__ == "__main__":
    App().mainloop()
'@ | Set-Content "$root\app.py" -Encoding UTF8

# ---------- build.ps1 ----------
@'
# build.ps1
# Requires: py -m pip install pyinstaller
$ErrorActionPreference = "Stop"

if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path build) { Remove-Item -Recurse -Force build }

py -m PyInstaller --noconfirm --onefile --windowed `
  --name RipplePy `
  app.py

Write-Host "`nDone. Find EXE in .\dist\RipplePy.exe" -ForegroundColor Green
'@ | Set-Content "$root\build.ps1" -Encoding UTF8

# ---------- README.md ----------
@'
# RipplePy (Python Desktop)

Local-first Tkinter app with SQLite. Ingest text, search, and export offline metrics charts (2D dot+line, inline SVG).

## Run
- Install Python 3.10+.
- `python app.py`

## Build EXE (Windows)
- `py -m pip install pyinstaller`
- `.\build.ps1` → produces `dist\RipplePy.exe`

## What it stores
- `assets(id, type, created_at, raw_text)`
- `metrics_sessions(...)`, `metrics_events(...)`

## Notes
- 100% offline. No external libs required to run (charts are inline SVG).
- The database file `ripple.db` is created next to the app.
'@ | Set-Content "$root\README.md" -Encoding UTF8

# Zip it up
if (Test-Path "ripplepy.zip") { Remove-Item -Force "ripplepy.zip" }
Compress-Archive -Path "$root\*" -DestinationPath "ripplepy.zip" -Force

Write-Host "`nAll set! Folder 'ripplepy' created and zipped to 'ripplepy.zip'." -ForegroundColor Green
Write-Host "Run app:" -ForegroundColor Cyan
Write-Host "  cd ripplepy; python app.py" -ForegroundColor Yellow