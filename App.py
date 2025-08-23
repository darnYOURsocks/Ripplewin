import os, json, time, sqlite3, math
from contextlib import contextmanager
from typing import Optional, List, Dict

import streamlit as st
import altair as alt

DB_PATH = os.path.join(os.path.dirname(__file__), "ripple.db")

# ---------------- DB helpers ----------------
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
    new_db = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if new_db:
        apply_schema(conn)
    return conn

@contextmanager
def open_conn():
    conn = get_conn()
    try:
        yield conn
    finally:
        pass  # keep global connection alive for Streamlit reloads

# ---------------- Data API ----------------
def ingest_raw(conn: sqlite3.Connection, raw_text: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assets (type, created_at, raw_text) VALUES ('conversation', strftime('%s','now'), ?)",
        (raw_text,),
    )
    conn.commit()
    return cur.lastrowid

def search_assets(conn: sqlite3.Connection, q: Optional[str]) -> List[Dict]:
    sql = "SELECT id, raw_text FROM assets WHERE 1=1"
    params = []
    if q and q.strip():
        sql += " AND raw_text LIKE ?"
        params.append(f"%{q}%")
    sql += " ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def start_session(conn: sqlite3.Connection, label: str, stress_before: int) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO metrics_sessions (started_at,label,stress_before) VALUES (strftime('%s','now'),?,?)",
        (label, stress_before),
    )
    conn.commit()
    return cur.lastrowid

def end_session(conn: sqlite3.Connection, session_id: int, stress_after: int):
    conn.execute(
        "UPDATE metrics_sessions SET ended_at=strftime('%s','now'), stress_after=? WHERE id=?",
        (stress_after, session_id),
    )
    conn.commit()

def log_event(conn: sqlite3.Connection, session_id: int, phase: str, name: str, ms: int, notes: Optional[str] = None):
    conn.execute(
        "INSERT INTO metrics_events (session_id,ts,phase,name,ms,notes) VALUES (?,?,?, ?,?,?)",
        (session_id, int(time.time()), phase, name, ms, notes),
    )
    conn.commit()

def load_sessions(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        "SELECT id, started_at, ended_at, label, stress_before, stress_after FROM metrics_sessions ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]

def load_events(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        "SELECT id, session_id, ts, phase, name, ms, notes FROM metrics_events ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]

def export_json_blob(conn: sqlite3.Connection) -> bytes:
    payload = {
        "sessions": load_sessions(conn),
        "events": load_events(conn),
        "assets": search_assets(conn, None),
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    return json.dumps(payload, indent=2).encode("utf-8")

# ---------------- HTML report (inline SVG/JS) ----------------
def generate_metrics_html(sessions: List[Dict], events: List[Dict]) -> str:
    # Map keys to short names used in the embedded JS
    for s in sessions:
        s["sb"] = s.get("stress_before")
        s["sa"] = s.get("stress_after")
    for e in events:
        e["sid"] = e.get("session_id")

    sessions_json = json.dumps(sessions)
    events_json = json.dumps(events)

    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Ripple Metrics</title>
<style>
body{{background:#0f1221;color:#e8ecff;font:14px system-ui;margin:0;padding:24px}}
.card{{background:#121636;border:1px solid #2a2f4a;border-radius:12px;padding:12px;margin:16px auto;max-width:980px}}
.chart{{height:420px;background:#0c1030;border:1px solid #202757;border-radius:12px}}
</style></head><body>
<h2 style='text-align:center'>Ripple (Streamlit) – Metrics</h2>
<div class='card'><h3>Throughput by phase (dot‑line)</h3><svg id='a' class='chart' viewBox='0 0 900 420'></svg></div>
<div class='card'><h3>Sessions: code/time proxy & stress change</h3><svg id='b' class='chart' viewBox='0 0 900 420'></svg></div>
<script>
const sessions={sessions_json};
const events={events_json};

function draw(id, pts, color) {{
  const svg=document.getElementById(id), W=900,H=420,p=50,w=W-2*p,h=H-2*p;
  const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y), xmin=0,xmax=Math.max(...xs,1), ymin=0,ymax=Math.max(...ys,1)*1.1;
  const sx=x=>p+(x-xmin)/(xmax-xmin||1)*w, sy=y=>H-p-(y-ymin)/(ymax-ymin||1)*h;
  const g=(t,a)=>{{const e=document.createElementNS('http://www.w3.org/2000/svg',t); for(const k in a)e.setAttribute(k,a[k]); svg.appendChild(e); return e;}};
  g('rect',{{x:0,y:0,width:W,height:H,fill:'none'}});
  for(let k=0;k<=5;k++){{ const y=sy((ymax/5)*k); g('line',{{x1:p,y1:y,x2:W-p,y2:y,stroke:'#2a2f4a'}}); }}
  g('line',{{x1:p,y1:H-p,x2:W-p,y2:H-p,stroke:'#90a0ff'}}); g('line',{{x1:p,y1:p,x2:p,y2:H-p,stroke:'#90a0ff'}});
  g('polyline',{{points:pts.map(q=>sx(q.x)+','+sy(q.y)).join(' '), fill:'none', stroke:color, 'stroke-width':2.5}});
  pts.forEach(q=>{{ g('circle',{{cx:sx(q.x), cy:sy(q.y), r:5, fill:'#7ce2a0'}}); g('text',{{x:sx(q.x)+6,y:sy(q.y)-8,fill:'#cfe0ff','font-size':12}}).textContent=q.label; }});
}}

// A: Last session's phases
const last = sessions.length ? sessions[sessions.length-1] : null;
const phases = ['Search','Ingest','Validate','Fix'];
const evLast = last ? events.filter(e=>e.sid===last.id) : [];
const ptsA = phases.map((ph,i)=>({{x:i,y:evLast.filter(e=>e.phase===ph).reduce((t,e)=>t+e.ms,0)/1000,label:ph}}));
draw('a', ptsA, '#f6c177');

// B: Each session dot (Fix ms proxy) & Δstress
const ptsB = sessions.map((s,i)=>{{
  const ev = events.filter(e=>e.sid===s.id && e.phase==='Fix');
  const codeSec = Math.round(ev.reduce((t,e)=>t+e.ms,0)/1000);
  const d = (s.sb||0)-(s.sa||0);
  return {{x:i+1,y:codeSec,label:`S${{i+1}} (Δ${{d}})`}};
}});
draw('b', ptsB, '#7ce2a0');
</script></body></html>"""
    return html

# ---------------- Page setup ----------------
st.set_page_config(page_title="Ripple (Streamlit)", page_icon="🌊", layout="wide")

if "conn" not in st.session_state:
    st.session_state.conn = get_conn()

conn = st.session_state.conn

st.title("🌊 Ripple • Streamlit Offline Retrieval + Metrics")

with st.expander("Seed sample data (optional)"):
    if st.button("Insert 5 sample rows"):
        texts = [
            "Machine learning is a subset of AI that learns patterns from data.",
            "Python is widely used for data science, web dev, and automation.",
            "Ripple app demonstrates local-first principles and offline metrics.",
            "SQLite is perfect for embedded/local apps; zero server required.",
            "React and Streamlit can both drive rich UI for the same knowledge base."
        ]
        sid = start_session(conn, "Seed", 5)
        t0 = time.perf_counter()
        for t in texts:
            t1 = time.perf_counter()
            ingest_raw(conn, t)
            ms = int((time.perf_counter() - t1) * 1000)
            log_event(conn, sid, "Ingest", "seed_row", ms, f"len={len(t)}")
        log_event(conn, sid, "Search", "post_seed", int((time.perf_counter() - t0) * 1000), "initial")
        end_session(conn, sid, 4)
        st.success("Seeded.")

colL, colR = st.columns([2,1])

with colL:
    st.subheader("Ingest Text")
    input_text = st.text_area("Enter text to store", height=140, label_visibility="collapsed", placeholder="Paste or type any note/chat/code…")
    c1, c2, c3 = st.columns(3)
    with c1:
        stress_before = st.number_input("Stress Before", 0, 10, 5)
    with c2:
        stress_after = st.number_input("Stress After", 0, 10, 4)
    with c3:
        st.write("")
        if st.button("Ingest", use_container_width=True):
            if not input_text.strip():
                st.warning("Please enter some text.")
            else:
                sid = start_session(conn, "Ingest", int(stress_before))
                t1 = time.perf_counter()
                time.sleep(0.1)  # simulate minor work
                ingest_raw(conn, input_text.strip())
                ms = int((time.perf_counter() - t1) * 1000)
                log_event(conn, sid, "Ingest", "raw_text", ms, f"len={len(input_text.strip())}")
                end_session(conn, sid, int(stress_after))
                st.success("Saved.")

with colR:
    st.subheader("Search")
    q = st.text_input("Query", "", placeholder="keyword…")
    if st.button("Search", use_container_width=True):
        sid = start_session(conn, "Search", 5)
        t1 = time.perf_counter()
        time.sleep(0.05)
        results = search_assets(conn, q)
        ms = int((time.perf_counter() - t1) * 1000)
        log_event(conn, sid, "Search", q or "(all)", ms, f"hits={len(results)}")
        end_session(conn, sid, 4)
        st.session_state.last_results = results

# Results list
st.markdown("### Results")
results = st.session_state.get("last_results", search_assets(conn, None))
if not results:
    st.info("No results yet.")
else:
    for r in results[:200]:
        st.markdown(f"**ID {r['id']}** — { (r['raw_text'][:180] + '…') if len(r['raw_text'])>180 else r['raw_text'] }")
    if len(results) > 200:
        st.caption(f"Showing first 200 of {len(results)}.")

# Load metrics
sessions = load_sessions(conn)
events = load_events(conn)

# Summary KPIs
st.markdown("### Metrics")
col1, col2, col3, col4 = st.columns(4)
avg_ms = int(sum(e["ms"] for e in events)/len(events)) if events else 0
completed = [s for s in sessions if s.get("stress_after") is not None]
avg_d = (sum((s["stress_before"] or 0) - (s["stress_after"] or 0) for s in completed)/len(completed)) if completed else 0.0
with col1: st.metric("Total Sessions", len(sessions))
with col2: st.metric("Items Stored", len(search_assets(conn, None)))
with col3: st.metric("Avg Response Time", f"{avg_ms} ms")
with col4: st.metric("Avg Stress Reduction", f"{avg_d:.1f}")

# Charts (Altair)
st.markdown("### Charts")

if sessions:
    last = sessions[-1]
    phases = ["Search", "Ingest", "Validate", "Fix"]
    ev_last = [e for e in events if e["session_id"] == last["id"]]
    dataA = [{"phase": ph,
              "seconds": round(sum(e["ms"] for e in ev_last if e["phase"]==ph)/1000, 2)}
             for ph in phases]

    chartA = alt.Chart(alt.Data(values=dataA)).mark_line(point=True, interpolate='linear').encode(
        x=alt.X('phase:N', title='Phase'),
        y=alt.Y('seconds:Q', title='Seconds'),
        tooltip=['phase','seconds']
    ).properties(width=500, height=280, title="Phase Throughput (Last Session)")

    # Session performance: Fix ms as code proxy
    dataB = []
    for i, s in enumerate(sessions, start=1):
        fix_ms = sum(e["ms"] for e in events if e["session_id"]==s["id"] and e["phase"]=="Fix")
        code_sec = int(round(fix_ms/1000))
        delta = (s.get("stress_before") or 0) - (s.get("stress_after") or 0)
        dataB.append({"session": f"S{i}", "code_sec": code_sec, "delta": delta})

    chartB = alt.Chart(alt.Data(values=dataB)).mark_line(point=True).encode(
        x=alt.X('session:N', title='Session'),
        y=alt.Y('code_sec:Q', title='Code Seconds (proxy)'),
        tooltip=['session','code_sec','delta']
    ).properties(width=500, height=280, title="Session Performance & ΔStress")

    c1, c2 = st.columns(2)
    with c1: st.altair_chart(chartA, use_container_width=True)
    with c2: st.altair_chart(chartB, use_container_width=True)
else:
    st.info("Charts will appear after you run at least one session (Ingest or Search).")

# Export buttons
st.markdown("### Export")
json_bytes = export_json_blob(conn)
st.download_button("⬇️ Export JSON", data=json_bytes, file_name="ripple-metrics.json", mime="application/json")

html_report = generate_metrics_html(sessions, events)
st.download_button("⬇️ Export HTML report", data=html_report, file_name="ripple-metrics.html", mime="text/html")
