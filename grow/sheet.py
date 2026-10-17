"""The listening sheet: the only acceptance test.

Serves the archive as a map you can click to hear, with lineage, facts, and
the genome text. Every play and every vote is appended to archive/events.csv,
which is what the taste probe trains on. Replays count: the question Grow 2
asks is "how many clips would you play twice?"
"""

from __future__ import annotations

import csv
import html
import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ARCHIVE_DIR
from .archive import Archive, GRID

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Grow 2 listening sheet</title>
<style>
 body{font:14px/1.4 system-ui,sans-serif;margin:0;background:#141412;color:#e8e4da}
 #wrap{display:grid;grid-template-columns:1fr 380px;height:100vh}
 #map{overflow:auto;padding:12px}
 table{border-collapse:collapse}
 td{border:1px solid #2a2824;width:72px;height:56px;vertical-align:top;padding:2px;font-size:11px}
 td.empty{background:#191815}
 .chip{display:block;cursor:pointer;padding:1px 3px;margin:1px 0;border-radius:3px;background:#2d3a2f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .chip.seed{background:#3a3326}.chip.mind{background:#2c3550}.chip.cross{background:#4a2f3f}
 .chip.now{outline:2px solid #e8c36a}
 #side{border-left:1px solid #2a2824;padding:14px;overflow:auto}
 button{background:#262521;color:#e8e4da;border:1px solid #3a3833;border-radius:4px;padding:6px 10px;margin:2px;cursor:pointer}
 button:hover{background:#33312c}
 pre{font-size:11px;white-space:pre-wrap;background:#0f0f0d;padding:8px;max-height:40vh;overflow:auto}
 .lin{margin:2px 0}.lin span{cursor:pointer;text-decoration:underline dotted}
 h2{margin:4px 0 8px;font-size:18px} .muted{color:#9a948a}
 #axes{font-size:11px;color:#9a948a;margin-bottom:6px}
</style></head><body><div id="wrap">
<div id="map"><div id="axes">rows: bright at top, dark at bottom &nbsp;|&nbsp; columns: sparse on the left, dense on the right &nbsp;|&nbsp; colors: seed / blind / mind / cross</div>
<table id="grid"></table>
<p class="muted" id="status"></p>
<p><button onclick="surprise()">surprise me</button> <button onclick="reload()">refresh map</button></p>
</div>
<div id="side"><h2 id="name">pick a clip</h2>
<audio id="player" controls style="width:100%"></audio>
<p><button onclick="vote(1)">&#128077; keep</button><button onclick="vote(-1)">&#128078; meh</button><button onclick="again()">&#8635; again</button> <span class="muted" id="plays"></span></p>
<p id="facts" class="muted"></p>
<div id="lineage"></div>
<pre id="csd"></pre>
</div></div>
<script>
let data={}, now=null, plays={};
async function reload(){ data = await (await fetch('/data')).json(); draw(); }
function draw(){
  const g=document.getElementById('grid'); g.innerHTML='';
  for(let y=GRID-1;y>=0;y--){ const tr=document.createElement('tr');
    for(let x=0;x<GRID;x++){ const td=document.createElement('td'); const key=x+','+y; const cell=data.cells[key]||[];
      if(!cell.length) td.className='empty';
      for(const id of cell){ const c=data.clips[id]; const s=document.createElement('span');
        s.className='chip '+(c.author==='seed'?'seed':c.author==='mind'?'mind':c.author==='cross'?'cross':'')+(now===id?' now':'');
        s.textContent=c.name; s.title=c.name+' · gen '+c.generation+' · '+c.author; s.onclick=()=>show(id); td.appendChild(s);}
      tr.appendChild(td);} g.appendChild(tr);}
  document.getElementById('status').textContent=data.status;
}
function show(id, autoplay=true){ now=id; const c=data.clips[id]; draw();
  document.getElementById('name').textContent=c.name+'  ·  gen '+c.generation+'  ·  '+c.author+(c.note?('  ·  '+c.note):'');
  const p=document.getElementById('player'); p.src='/clips/'+id+'/clip.wav'; if(autoplay){p.play().catch(()=>{});}
  document.getElementById('facts').textContent=c.facts+'  ·  ear '+c.ear+' '+c.quality.toFixed(2);
  const lin=document.getElementById('lineage'); lin.innerHTML='<div class="muted">lineage</div>';
  for(const a of c.lineage){ const d=document.createElement('div'); d.className='lin';
    d.innerHTML='<span onclick="show(\\''+a.id+'\\')">'+(a.id===id?'<b>'+a.name+'</b>':a.name)+'</span> <span class="muted">gen '+a.generation+' · '+a.author+(a.note?' · '+a.note:'')+(a.status!=='alive'?' · '+a.status:'')+'</span>';
    lin.appendChild(d);}
  document.getElementById('csd').textContent=c.csd; }
document.getElementById('player').addEventListener('play',()=>{ if(!now) return; plays[now]=(plays[now]||0)+1;
  document.getElementById('plays').textContent='played '+plays[now]+'x'; send({kind:'play',clip:now,value:1}); });
function again(){ const p=document.getElementById('player'); p.currentTime=0; p.play(); }
function vote(v){ if(!now) return; send({kind:'vote',clip:now,value:v}); document.getElementById('plays').textContent=(v>0?'kept':'meh')+' · played '+(plays[now]||0)+'x'; }
function surprise(){ const ids=Object.keys(data.clips).filter(i=>data.clips[i].status==='alive'); if(!ids.length) return; show(ids[Math.floor(Math.random()*ids.length)]); }
function send(ev){ fetch('/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ev)}); }
const GRID=__GRID__; reload();
</script></body></html>
"""


def _payload(archive: Archive) -> dict:
    clips = {}
    cells: dict[str, list[str]] = {}
    for c in archive.clips.values():
        clips[c.id] = {
            "id": c.id, "name": c.genome.name or c.id, "generation": c.genome.generation,
            "author": c.genome.author, "note": c.genome.note, "status": c.status,
            "facts": c.descriptors.facts(), "quality": c.quality, "ear": c.ear,
            "csd": c.genome.text,
            "lineage": [
                {"id": a.id, "name": a.genome.name or a.id, "generation": a.genome.generation,
                 "author": a.genome.author, "note": a.genome.note, "status": a.status}
                for a in archive.lineage(c.id)
            ],
        }
        if c.status == "alive":
            cells.setdefault(f"{c.cell[0]},{c.cell[1]}", []).append(c.id)
    return {"clips": clips, "cells": cells, "status": archive.status_lines()[0]}


def serve(root: Path | str = ARCHIVE_DIR, port: int = 8765) -> None:
    root = Path(root).resolve()
    events = root / "events.csv"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):  # quiet
            pass

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                body = PAGE.replace("__GRID__", str(GRID)).encode()
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            elif self.path == "/data":
                body = json.dumps(_payload(Archive.open(root))).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            else:
                super().do_GET()

        def do_POST(self):
            if self.path != "/event":
                self.send_response(404); self.end_headers(); return
            n = int(self.headers.get("Content-Length", 0))
            try:
                ev = json.loads(self.rfile.read(n).decode())
            except json.JSONDecodeError:
                self.send_response(400); self.end_headers(); return
            new = not events.exists()
            with events.open("a", newline="") as fh:
                w = csv.writer(fh)
                if new:
                    w.writerow(["time", "clip", "kind", "value"])
                w.writerow([f"{time.time():.0f}", str(ev.get("clip", ""))[:16], str(ev.get("kind", ""))[:8], str(ev.get("value", ""))[:8]])
            self.send_response(204); self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"listening sheet at http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
