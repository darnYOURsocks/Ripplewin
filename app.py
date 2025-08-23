import React, { useState, useEffect } from ‘react’;
import { Search, Database, BarChart3, Download, Plus, Timer } from ‘lucide-react’;

// In-memory database simulation
class RippleDB {
constructor() {
this.assets = [];
this.sessions = [];
this.events = [];
this.assetCounter = 0;
this.sessionCounter = 0;
this.eventCounter = 0;
}

ingestRaw(rawText) {
const asset = {
id: ++this.assetCounter,
type: ‘conversation’,
created_at: Math.floor(Date.now() / 1000),
raw_text: rawText
};
this.assets.push(asset);
return asset.id;
}

search(query) {
if (!query || !query.trim()) {
return […this.assets].reverse();
}
return this.assets
.filter(asset => asset.raw_text.toLowerCase().includes(query.toLowerCase()))
.reverse();
}

startSession(label, stressBefore) {
const session = {
id: ++this.sessionCounter,
started_at: Math.floor(Date.now() / 1000),
ended_at: null,
label: label,
stress_before: stressBefore,
stress_after: null
};
this.sessions.push(session);
return session.id;
}

endSession(sessionId, stressAfter) {
const session = this.sessions.find(s => s.id === sessionId);
if (session) {
session.ended_at = Math.floor(Date.now() / 1000);
session.stress_after = stressAfter;
}
}

logEvent(sessionId, phase, name, ms, notes = null) {
const event = {
id: ++this.eventCounter,
session_id: sessionId,
ts: Math.floor(Date.now() / 1000),
phase: phase,
name: name,
ms: ms,
notes: notes
};
this.events.push(event);
}

exportData() {
return {
sessions: this.sessions,
events: this.events,
assets: this.assets,
exported_at: new Date().toISOString()
};
}
}

// Metrics helper class
class Metrics {
constructor(db) {
this.db = db;
this.sessionId = null;
this.startTimes = {};
}

startSession(label, stressBefore = 0) {
this.sessionId = this.db.startSession(label, stressBefore);
return this.sessionId;
}

endSession(stressAfter = 0) {
if (this.sessionId) {
this.db.endSession(this.sessionId, stressAfter);
this.sessionId = null;
}
}

begin(key) {
this.startTimes[key] = performance.now();
}

end(key, phase, name, notes = null) {
const start = this.startTimes[key];
if (start && this.sessionId) {
const ms = Math.round(performance.now() - start);
this.db.logEvent(this.sessionId, phase, name, ms, notes);
delete this.startTimes[key];
}
}
}

// Chart component for metrics visualization
const MetricsChart = ({ sessions, events }) => {
const createSVGElement = (type, attrs, parent) => {
const elem = document.createElementNS(‘http://www.w3.org/2000/svg’, type);
Object.entries(attrs).forEach(([key, value]) => {
elem.setAttribute(key, value);
});
if (parent) parent.appendChild(elem);
return elem;
};

useEffect(() => {
// Clear previous charts
const chartA = document.getElementById(‘chart-a’);
const chartB = document.getElementById(‘chart-b’);
if (chartA) chartA.innerHTML = ‘’;
if (chartB) chartB.innerHTML = ‘’;

```
if (sessions.length === 0) return;

const drawChart = (id, points, color) => {
  const svg = document.getElementById(id);
  if (!svg || points.length === 0) return;

  const W = 400, H = 200, padding = 30;
  const w = W - 2 * padding, h = H - 2 * padding;

  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const xmin = 0, xmax = Math.max(...xs, 1);
  const ymin = 0, ymax = Math.max(...ys, 1) * 1.1;

  const sx = x => padding + (x - xmin) / (xmax - xmin || 1) * w;
  const sy = y => H - padding - (y - ymin) / (ymax - ymin || 1) * h;

  // Grid lines
  for (let k = 0; k <= 5; k++) {
    const y = sy((ymax / 5) * k);
    createSVGElement('line', {
      x1: padding, y1: y, x2: W - padding, y2: y,
      stroke: '#2a2f4a', 'stroke-width': 1
    }, svg);
  }

  // Axes
  createSVGElement('line', {
    x1: padding, y1: H - padding, x2: W - padding, y2: H - padding,
    stroke: '#90a0ff', 'stroke-width': 2
  }, svg);
  createSVGElement('line', {
    x1: padding, y1: padding, x2: padding, y2: H - padding,
    stroke: '#90a0ff', 'stroke-width': 2
  }, svg);

  // Line
  if (points.length > 1) {
    const pathData = points.map((p, i) => 
      `${i === 0 ? 'M' : 'L'} ${sx(p.x)} ${sy(p.y)}`
    ).join(' ');
    createSVGElement('path', {
      d: pathData, fill: 'none', stroke: color, 'stroke-width': 2
    }, svg);
  }

  // Points and labels
  points.forEach(p => {
    createSVGElement('circle', {
      cx: sx(p.x), cy: sy(p.y), r: 4, fill: '#7ce2a0'
    }, svg);
    createSVGElement('text', {
      x: sx(p.x) + 6, y: sy(p.y) - 8, fill: '#cfe0ff',
      'font-size': 10, 'font-family': 'system-ui'
    }, svg).textContent = p.label;
  });
};

// Chart A: Last session phases
const lastSession = sessions[sessions.length - 1];
const phases = ['Search', 'Ingest', 'Validate', 'Fix'];
const lastEvents = events.filter(e => e.session_id === lastSession.id);
const pointsA = phases.map((phase, i) => ({
  x: i,
  y: lastEvents.filter(e => e.phase === phase).reduce((sum, e) => sum + e.ms, 0) / 1000,
  label: phase
}));
drawChart('chart-a', pointsA, '#f6c177');

// Chart B: Session performance
const pointsB = sessions.map((session, i) => {
  const sessionEvents = events.filter(e => e.session_id === session.id && e.phase === 'Fix');
  const codeSec = Math.round(sessionEvents.reduce((sum, e) => sum + e.ms, 0) / 1000);
  const stressDelta = (session.stress_before || 0) - (session.stress_after || 0);
  return {
    x: i + 1,
    y: codeSec,
    label: `S${i + 1} (Δ${stressDelta})`
  };
});
drawChart('chart-b', pointsB, '#7ce2a0');
```

}, [sessions, events]);

return (
<div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
<div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
<h4 className="text-sm font-semibold text-slate-300 mb-2">Phase Throughput (Last Session)</h4>
<svg id="chart-a" className="w-full h-48 bg-slate-900 rounded border border-slate-700" viewBox="0 0 400 200"></svg>
</div>
<div className="bg-slate-800 border border-slate-600 rounded-lg p-4">
<h4 className="text-sm font-semibold text-slate-300 mb-2">Session Performance & Stress Change</h4>
<svg id="chart-b" className="w-full h-48 bg-slate-900 rounded border border-slate-700" viewBox="0 0 400 200"></svg>
</div>
</div>
);
};

// Main RipplePy component
export default function RipplePy() {
const [db] = useState(() => new RippleDB());
const [inputText, setInputText] = useState(’’);
const [searchQuery, setSearchQuery] = useState(’’);
const [searchResults, setSearchResults] = useState([]);
const [stressBefore, setStressBefore] = useState(5);
const [stressAfter, setStressAfter] = useState(4);
const [sessions, setSessions] = useState([]);
const [events, setEvents] = useState([]);
const [isProcessing, setIsProcessing] = useState(false);

// Initialize with sample data
useEffect(() => {
const sampleData = [
“Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without explicit programming.”,
“Python is a versatile programming language widely used for data science, web development, automation, and artificial intelligence applications.”,
“The RipplePy application demonstrates local-first software principles with offline functionality and comprehensive metrics tracking.”,
“SQLite is a lightweight, serverless database engine that’s perfect for local applications and embedded systems.”,
“React hooks provide a way to use state and lifecycle methods in functional components, making code more reusable and easier to understand.”
];

```
sampleData.forEach((text, index) => {
  setTimeout(() => {
    const metrics = new Metrics(db);
    const sessionId = metrics.startSession('Sample', 5);
    metrics.begin('ingest');
    db.ingestRaw(text);
    metrics.end('ingest', 'Ingest', 'sample_data', `len=${text.length}`);
    metrics.endSession(4);
  }, index * 100);
});

setTimeout(() => {
  setSessions([...db.sessions]);
  setEvents([...db.events]);
  performSearch('');
}, 1000);
```

}, [db]);

const handleIngest = async () => {
if (!inputText.trim()) {
alert(‘Please enter some text to ingest.’);
return;
}

```
setIsProcessing(true);
const metrics = new Metrics(db);

try {
  const sessionId = metrics.startSession('Ingest', stressBefore);
  metrics.begin('ingest');
  
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 100));
  
  db.ingestRaw(inputText);
  metrics.end('ingest', 'Ingest', 'raw_text', `len=${inputText.length}`);
  metrics.endSession(stressAfter);
  
  setInputText('');
  setSessions([...db.sessions]);
  setEvents([...db.events]);
  
  alert('Text ingested successfully!');
} catch (error) {
  alert('Error ingesting text: ' + error.message);
} finally {
  setIsProcessing(false);
}
```

};

const performSearch = async (query = null) => {
const searchTerm = query !== null ? query : searchQuery;
setIsProcessing(true);
const metrics = new Metrics(db);

```
try {
  const sessionId = metrics.startSession('Search', stressBefore);
  metrics.begin('search');
  
  // Simulate search time
  await new Promise(resolve => setTimeout(resolve, 50));
  
  const results = db.search(searchTerm);
  metrics.end('search', 'Search', searchTerm || '(all)', `hits=${results.length}`);
  metrics.endSession(stressAfter);
  
  setSearchResults(results);
  setSessions([...db.sessions]);
  setEvents([...db.events]);
} catch (error) {
  alert('Error performing search: ' + error.message);
} finally {
  setIsProcessing(false);
}
```

};

const handleSearch = () => {
performSearch();
};

const exportMetrics = () => {
const data = db.exportData();
const blob = new Blob([JSON.stringify(data, null, 2)], { type: ‘application/json’ });
const url = URL.createObjectURL(blob);
const a = document.createElement(‘a’);
a.href = url;
a.download = ‘ripplepy-metrics.json’;
a.click();
URL.revokeObjectURL(url);
};

const exportHTML = () => {
const sessionsJson = JSON.stringify(sessions.map(s => ({
…s,
sb: s.stress_before,
sa: s.stress_after
})));
const eventsJson = JSON.stringify(events.map(e => ({
…e,
sid: e.session_id
})));

```
const htmlTemplate = `<!doctype html>
```

<html><head><meta charset='utf-8'><title>Ripple Metrics</title>
<style>
body{background:#0f1221;color:#e8ecff;font:14px system-ui;margin:0;padding:24px}
.card{background:#121636;border:1px solid #2a2f4a;border-radius:12px;padding:12px;margin:16px auto;max-width:980px}
.chart{height:420px;background:#0c1030;border:1px solid #202757;border-radius:12px}
</style></head><body>
<h2 style='text-align:center'>RipplePy - Metrics</h2>
<div class='card'><h3>Throughput by phase (dot-line)</h3><svg id='a' class='chart' viewBox='0 0 900 420'></svg></div>
<div class='card'><h3>Sessions: code/time proxy & stress change</h3><svg id='b' class='chart' viewBox='0 0 900 420'></svg></div>
<script>
const sessions=${sessionsJson};
const events=${eventsJson};

function draw(id, pts, color) {
const svg=document.getElementById(id), W=900,H=420,p=50,w=W-2*p,h=H-2*p;
const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y), xmin=0,xmax=Math.max(…xs,1), ymin=0,ymax=Math.max(…ys,1)*1.1;
const sx=x=>p+(x-xmin)/(xmax-xmin||1)*w, sy=y=>H-p-(y-ymin)/(ymax-ymin||1)*h;
const g=(t,a)=>{const e=document.createElementNS(‘http://www.w3.org/2000/svg’,t); for(const k in a)e.setAttribute(k,a[k]); svg.appendChild(e); return e;};
g(‘rect’,{x:0,y:0,width:W,height:H,fill:‘none’});
for(let k=0;k<=5;k++){ const y=sy((ymax/5)*k); g(‘line’,{x1:p,y1:y,x2:W-p,y2:y,stroke:’#2a2f4a’}); }
g(‘line’,{x1:p,y1:H-p,x2:W-p,y2:H-p,stroke:’#90a0ff’}); g(‘line’,{x1:p,y1:p,x2:p,y2:H-p,stroke:’#90a0ff’});
g(‘polyline’,{points:pts.map(q=>sx(q.x)+’,’+sy(q.y)).join(’ ‘), fill:‘none’, stroke:color, ‘stroke-width’:2.5});
pts.forEach(q=>{ g(‘circle’,{cx:sx(q.x), cy:sy(q.y), r:5, fill:’#7ce2a0’}); g(‘text’,{x:sx(q.x)+6,y:sy(q.y)-8,fill:’#cfe0ff’,‘font-size’:12}).textContent=q.label; });
}

const last = sessions.length ? sessions[sessions.length-1] : null;
const phases = [‘Search’,‘Ingest’,‘Validate’,‘Fix’];
const evLast = last ? events.filter(e=>e.sid===last.id) : [];
const ptsA = phases.map((ph,i)=>({x:i,y:evLast.filter(e=>e.phase===ph).reduce((t,e)=>t+e.ms,0)/1000,label:ph}));
draw(‘a’, ptsA, ‘#f6c177’);

const ptsB = sessions.map((s,i)=>{
const ev = events.filter(e=>e.sid===s.id && e.phase===‘Fix’);
const codeSec = Math.round(ev.reduce((t,e)=>t+e.ms,0)/1000);
const d = (s.sb||0)-(s.sa||0);
return {x:i+1,y:codeSec,label:`S${i+1} (Δ${d})`};
});
draw(‘b’, ptsB, ‘#7ce2a0’);
</script></body></html>`;

```
const blob = new Blob([htmlTemplate], { type: 'text/html' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'ripplepy-metrics.html';
a.click();
URL.revokeObjectURL(url);
```

};

const calculateMetrics = () => {
const completedSessions = sessions.filter(s => s.stress_after !== null);
const avgTime = events.length > 0 ? Math.round(events.reduce((sum, e) => sum + e.ms, 0) / events.length) : 0;
const avgStressReduction = completedSessions.length > 0
? (completedSessions.reduce((sum, s) => sum + (s.stress_before - s.stress_after), 0) / completedSessions.length).toFixed(1)
: 0;

```
return {
  totalSessions: sessions.length,
  totalItems: searchResults.length > 0 ? db.assets.length : 0,
  avgTime,
  avgStressReduction
};
```

};

const metrics = calculateMetrics();

return (
<div className="min-h-screen bg-slate-900 text-slate-100 p-6">
<div className="max-w-6xl mx-auto">
{/* Header */}
<div className="text-center mb-8">
<h1 className="text-3xl font-bold text-blue-400 mb-2">🌊 RipplePy</h1>
<p className="text-slate-400">Offline Retrieval + Metrics - Fully Interactive React Version</p>
</div>

```
    {/* Ingest Section */}
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Plus className="w-5 h-5" />
        Ingest Text
      </h2>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Enter text to ingest and store locally..."
            className="w-full h-32 bg-slate-900 border border-slate-600 rounded-lg p-3 text-slate-100 font-mono text-sm resize-none focus:outline-none focus:border-blue-500"
          />
          <div className="flex gap-4 mt-3">
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-400">Stress Before:</label>
              <input
                type="number"
                min="0"
                max="10"
                value={stressBefore}
                onChange={(e) => setStressBefore(parseInt(e.target.value))}
                className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-400">Stress After:</label>
              <input
                type="number"
                min="0"
                max="10"
                value={stressAfter}
                onChange={(e) => setStressAfter(parseInt(e.target.value))}
                className="w-16 bg-slate-900 border border-slate-600 rounded px-2 py-1 text-xs"
              />
            </div>
          </div>
        </div>
        <div className="flex flex-col justify-center">
          <button
            onClick={handleIngest}
            disabled={isProcessing}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2 justify-center"
          >
            {isProcessing ? <Timer className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
            Ingest
          </button>
        </div>
      </div>
    </div>

    {/* Search Section */}
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Search className="w-5 h-5" />
        Search
      </h2>
      <div className="flex gap-4 mb-4">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search stored text..."
          className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-blue-500"
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          disabled={isProcessing}
          className="bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
        >
          Search
        </button>
      </div>
      <div className="bg-slate-900 border border-slate-600 rounded-lg p-4 max-h-64 overflow-y-auto">
        {searchResults.length === 0 ? (
          <div className="text-slate-500 text-center py-8">No results found</div>
        ) : (
          <div className="space-y-2">
            {searchResults.map((result) => (
              <div key={result.id} className="border-b border-slate-700 pb-2 last:border-b-0">
                <div className="text-xs text-slate-400 mb-1">ID: {result.id}</div>
                <div className="text-sm font-mono text-slate-200">
                  {result.raw_text.length > 120 ? result.raw_text.substring(0, 120) + '...' : result.raw_text}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>

    {/* Metrics Section */}
    <div className="bg-slate-800 border border-slate-600 rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5" />
        Metrics
      </h2>
      
      {/* Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-900 border border-slate-600 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-400">{metrics.totalSessions}</div>
          <div className="text-xs text-slate-400">Total Sessions</div>
        </div>
        <div className="bg-slate-900 border border-slate-600 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-400">{metrics.totalItems}</div>
          <div className="text-xs text-slate-400">Items Stored</div>
        </div>
        <div className="bg-slate-900 border border-slate-600 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-400">{metrics.avgTime}ms</div>
          <div className="text-xs text-slate-400">Avg Response Time</div>
        </div>
        <div className="bg-slate-900 border border-slate-600 rounded-lg p-4">
          <div className="text-2xl font-bold text-green-400">{metrics.avgStressReduction}</div>
          <div className="text-xs text-slate-400">Avg Stress Reduction</div>
        </div>
      </div>

      {/* Charts */}
      {sessions.length > 0 && (
        <MetricsChart sessions={sessions} events={events} />
      )}

      {/* Export Buttons */}
      <div className="flex gap-4 mt-6">
        <button
          onClick={exportMetrics}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export JSON
        </button>
        <button
          onClick={exportHTML}
          className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export HTML
        </button>
      </div>
    </div>
  </div>
</div>
```

);
}