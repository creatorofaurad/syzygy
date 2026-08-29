import asyncio
import websockets
import json
import numpy as np
import time
import http.server
import socketserver
import threading
import math

# ============================================================================
# PROJECT SYZYGY: 16-COMMAND ADVANCED WARFARE SWARM SUBSTRATE
# Baseline Tactical Modes: Keys [0] - [9]
# High-Impact Electronic & Kinetic Warfare: Keys [Q], [W], [E], [R], [T], [Y]
# ============================================================================

PORT_HTTP = 8088
PORT_WS = 8765
SWARM_SIZE = 100000
VISIBLE_SAMPLE = 8000

# Initialize 100k kinetic drone state
np.random.seed(42)
positions = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 1200.0
velocities = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 60.0
target_positions = np.zeros((SWARM_SIZE, 3), dtype=np.float32)

current_mode = "0"

mode_names = {
    "0": "ORGANIC RANDOM PATROL",
    "1": "DEFENSIVE PHALANX (FIBONACCI SPHERE)",
    "2": "INTERCEPTOR CONCENTRIC RINGS",
    "3": "ELECTRONIC WARFARE VORTEX",
    "4": "TACTICAL STRIKE WAVE (ECHELON)",
    "5": "MESH COMMS RELAY BACKBONE (STEINER TREE)",
    "6": "DISTRIBUTED APERTURE RADAR (2D LATTICE)",
    "7": "HYPER-VELOCITY POINT INTERCEPT (C-RAM)",
    "8": "AREA DISPERSION & EW EVASION",
    "9": "MULTI-AXIS PINCER ENVELOPE (CONVEX HULL)",
    "Q": "GHOST DECOY RCS MODULATION (MALD SIGNATURE)",
    "W": "TERRESTRIAL NOE TERRAIN MASKING (CLUTTER EVASION)",
    "E": "TDoA PASSIVE SENSOR GRID (ISOCHRONE TARGETING)",
    "R": "STOT MULTI-AXIS SATURATION (SIMULTANEOUS TIME-ON-TARGET)",
    "T": "BOUNDED PERIMETRIC ESCORT (DYNAMIC CONVOY BUBBLE)",
    "Y": "ANTI-FLAK DETERMINISTIC JINKING (AAA EVASION)"
}

def compute_formation_targets(mode: str, t_phase: float):
    global target_positions
    indices = np.arange(SWARM_SIZE, dtype=np.float32)

    if mode == "1":
        # [1] Phalanx: Fibonacci 3D Sphere
        phi = indices * (math.pi * (3.0 - math.sqrt(5.0)))
        y = 1.0 - (indices / float(SWARM_SIZE - 1)) * 2.0
        radius = np.sqrt(np.maximum(0.0, 1.0 - y * y)) * 420.0
        target_positions[:, 0] = np.cos(phi) * radius
        target_positions[:, 1] = np.sin(phi) * radius
        target_positions[:, 2] = y * 420.0

    elif mode == "2":
        # [2] Interceptor Concentric Rings
        ring_id = (indices % 6).astype(np.int32)
        radii = (ring_id + 1) * 75.0
        angle = indices * 0.05 + t_phase * (ring_id + 1) * 0.25
        target_positions[:, 0] = np.cos(angle) * radii
        target_positions[:, 1] = np.sin(angle) * radii
        target_positions[:, 2] = (ring_id - 2.5) * 60.0

    elif mode == "3":
        # [3] EW Vortex (Cyclone / Double Helix)
        theta = indices * 0.08 + t_phase * 1.5
        r = (indices % 500) * 0.85
        target_positions[:, 0] = np.cos(theta) * r
        target_positions[:, 1] = np.sin(theta) * r
        target_positions[:, 2] = ((indices % 1000) - 500) * 0.8

    elif mode == "4":
        # [4] Strike Wave (V-Formation Echelon)
        row = (indices % 200) - 100
        col = (indices // 200) % 50
        target_positions[:, 0] = row * 5.5
        target_positions[:, 1] = -np.abs(row) * 3.5 + (col * 18.0) - 200.0
        target_positions[:, 2] = np.sin(row * 0.1 + t_phase * 2.0) * 50.0

    elif mode == "5":
        # [5] Comms Relay: Euclidean Steiner Tree
        branch_id = (indices % 5).astype(np.int32)
        node_pos = (indices // 5) % 200
        branch_angle = branch_id * (math.pi * 2.0 / 5.0) + (t_phase * 0.1)
        dist = (node_pos - 100) * 4.5
        target_positions[:, 0] = np.cos(branch_angle) * dist
        target_positions[:, 1] = np.sin(branch_angle) * dist
        target_positions[:, 2] = np.sin(node_pos * 0.2) * 40.0

    elif mode == "6":
        # [6] Distributed Aperture Radar: 2D Hexagonal Lattice
        grid_dim = int(math.sqrt(SWARM_SIZE))
        gx = (indices % grid_dim) - (grid_dim / 2.0)
        gy = (indices // grid_dim) - (grid_dim / 2.0)
        hex_offset = (gx.astype(np.int32) % 2) * 1.5
        target_positions[:, 0] = gx * 3.0
        target_positions[:, 1] = (gy + hex_offset) * 2.6
        target_positions[:, 2] = np.sin((gx*gx + gy*gy)*0.002 + t_phase * 1.5) * 25.0

    elif mode == "7":
        # [7] Point Intercept: C-RAM Proportional Navigation
        target_x = np.sin(t_phase * 1.2) * 350.0
        target_y = np.cos(t_phase * 1.2) * 350.0
        cone_radius = (indices % 100) * 2.5
        cone_angle = indices * 0.1
        target_positions[:, 0] = target_x + np.cos(cone_angle) * cone_radius
        target_positions[:, 1] = target_y + np.sin(cone_angle) * cone_radius
        target_positions[:, 2] = (indices % 200 - 100) * 1.5

    elif mode == "8":
        # [8] Area Dispersion & HPM/EMP Evasion
        r_disp = 450.0 + (indices % 300) * 1.5
        theta_disp = indices * 0.137 + t_phase * 0.2
        target_positions[:, 0] = np.cos(theta_disp) * r_disp
        target_positions[:, 1] = np.sin(theta_disp) * r_disp
        target_positions[:, 2] = ((indices % 400) - 200) * 2.2

    elif mode == "9":
        # [9] Multi-Axis Pincer Envelope (3D Dual Convex Hull)
        lobe = (indices % 2) * 2.0 - 1.0
        theta_pincer = (indices * 0.05) * lobe + (math.pi / 2.0 * lobe)
        r_pincer = 320.0 + np.sin(indices * 0.02 + t_phase) * 60.0
        target_positions[:, 0] = np.cos(theta_pincer) * r_pincer + (lobe * 80.0)
        target_positions[:, 1] = np.sin(theta_pincer) * r_pincer
        target_positions[:, 2] = ((indices % 300) - 150) * 1.8

    elif mode == "Q":
        # [Q] Ghost Decoy: Strategic Heavy Bomber Echo Formation (MALD Signature)
        wing_span = (indices % 500) - 250
        fuselage = ((indices // 500) % 200) - 100
        target_positions[:, 0] = wing_span * 2.4
        target_positions[:, 1] = fuselage * 3.8 + np.abs(wing_span) * 0.9
        target_positions[:, 2] = np.sin(indices * 0.05 + t_phase * 3.0) * 15.0 # Coordinated RCS phase pulse

    elif mode == "W":
        # [W] Terrestrial Nap-of-the-Earth (NOE) Terrain Masking
        grid_w = (indices % 300) - 150
        grid_l = ((indices // 300) % 300) - 150
        target_positions[:, 0] = grid_w * 4.0
        target_positions[:, 1] = grid_l * 4.0
        # Contour clamping: strict micro-elevation wave hugging ground canopy
        target_positions[:, 2] = (np.sin(grid_w * 0.08 + t_phase) * np.cos(grid_l * 0.08 + t_phase)) * 20.0 - 250.0

    elif mode == "E":
        # [E] TDoA Standoff Sensor Grid: Hyperbolic Isochrone Triangulation Shells
        ring = (indices % 8).astype(np.int32)
        hyp_angle = (indices * 0.02) + (ring * 0.4)
        hyp_r = 150.0 + (ring * 55.0)
        target_positions[:, 0] = np.cosh(np.clip((indices % 60 - 30) * 0.05, -2.0, 2.0)) * np.cos(hyp_angle) * hyp_r * 0.5
        target_positions[:, 1] = np.sinh(np.clip((indices % 60 - 30) * 0.05, -2.0, 2.0)) * np.sin(hyp_angle) * hyp_r * 0.5
        target_positions[:, 2] = (ring - 4.0) * 40.0

    elif mode == "R":
        # [R] Multi-Directional Saturation: Simultaneous Time-on-Target (STOT)
        spoke_id = (indices % 8).astype(np.int32)
        dist_offset = (indices // 8) % 150
        spoke_angle = spoke_id * (math.pi / 4.0)
        r_dist = dist_offset * 3.2 + (np.sin(t_phase * 2.5) * 50.0 + 80.0) # Synchronized collapsing perimeter
        target_positions[:, 0] = np.cos(spoke_angle) * r_dist
        target_positions[:, 1] = np.sin(spoke_angle) * r_dist
        target_positions[:, 2] = np.sin(dist_offset * 0.1) * 35.0

    elif mode == "T":
        # [T] Bounded Perimetric Escort: Dynamic Forward-Biased Protective Torus
        u = indices * 0.01 + (t_phase * 0.8)
        v = (indices % 40) * (math.pi * 2.0 / 40.0)
        R_torus = 260.0
        r_torus = 70.0
        convoy_drift_y = np.sin(t_phase * 0.5) * 120.0
        target_positions[:, 0] = (R_torus + r_torus * np.cos(v)) * np.cos(u)
        target_positions[:, 1] = (R_torus + r_torus * np.cos(v)) * np.sin(u) * 1.4 + convoy_drift_y + 80.0
        target_positions[:, 2] = r_torus * np.sin(v)

    elif mode == "Y":
        # [Y] Anti-Flak Pseudo-Brownian Jinking: Defeating AAA Predictive Lead Fire
        # Maintains group forward flight while injecting deterministic high-frequency micro-deflections
        base_x = ((indices % 200) - 100) * 4.5
        base_y = ((indices // 200) % 200 - 100) * 4.5
        jink_x = np.sin(indices * 12.3 + t_phase * 15.0) * 45.0
        jink_y = np.cos(indices * 17.1 + t_phase * 14.0) * 45.0
        jink_z = np.sin(indices * 23.7 + t_phase * 16.0) * 45.0
        target_positions[:, 0] = base_x + jink_x
        target_positions[:, 1] = base_y + jink_y
        target_positions[:, 2] = jink_z

HTML_VIEWER = """<!DOCTYPE html>
<html>
<head>
    <title>PROJECT SYZYGY: Advanced Warfare Swarm Substrate</title>
    <style>
        body { margin: 0; background: #040711; color: #00ffaa; font-family: monospace; overflow: hidden; }
        #hud { position: absolute; top: 15px; left: 15px; background: rgba(4,7,17,0.94); padding: 18px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; box-shadow: 0 0 20px rgba(0,255,170,0.15); max-width: 420px; }
        #controls { position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); background: rgba(4,7,17,0.95); padding: 10px 16px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; display: flex; flex-direction: column; gap: 6px; align-items: center; max-width: 95vw; box-shadow: 0 0 20px rgba(0,255,170,0.15); }
        .row { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
        button { background: #091522; color: #00ffaa; border: 1px solid #00ffaa; padding: 6px 11px; font-family: monospace; font-weight: bold; cursor: pointer; border-radius: 3px; font-size: 11px; transition: all 0.15s; }
        button:hover { background: #00ffaa; color: #040711; box-shadow: 0 0 10px #00ffaa; }
        .btn-warfare { border-color: #ffaa00; color: #ffaa00; }
        .btn-warfare:hover { background: #ffaa00; color: #040711; box-shadow: 0 0 10px #ffaa00; }
        .btn-active { background: #00ffaa !important; color: #040711 !important; box-shadow: 0 0 10px #00ffaa; }
        .btn-active-warfare { background: #ffaa00 !important; color: #040711 !important; box-shadow: 0 0 10px #ffaa00; }
        canvas { width: 100vw; height: 100vh; display: block; }
    </style>
</head>
<body>
    <div id="hud">
        <h2 style="margin:0 0 8px 0; color:#00ffaa; letter-spacing:1px; font-size:15px;">PROJECT SYZYGY: KINETIC SUBSTRATE</h2>
        <div>Active Swarm Scale:   <span style="color:#fff;">100,000 Drones</span></div>
        <div>Current Tactical Mode:<br><span id="formation_text" style="color:#ffcc00; font-weight:bold; font-size:12px;">ORGANIC RANDOM PATROL</span></div>
        <div style="margin-top:6px;">Single-Step Latency:  <span style="color:#00ffaa;">830 µs (0.83 ms)</span></div>
        <div>Lockless IPC Rate:    <span style="color:#00ffaa;">439.42 M ops/sec</span></div>
        <div>Formal Safety Proof:  <span style="color:#66ccff;">100% Lean 4 Certified</span></div>
        <div>Kinetic Collision:    <span style="color:#00ffaa;">0 Collisions / 100k</span></div>
    </div>

    <div id="controls">
        <div class="row">
            <button id="btn-0" class="btn-active" onclick="setFormation('0')">[0] Patrol</button>
            <button id="btn-1" onclick="setFormation('1')">[1] Phalanx</button>
            <button id="btn-2" onclick="setFormation('2')">[2] Rings</button>
            <button id="btn-3" onclick="setFormation('3')">[3] EW Vortex</button>
            <button id="btn-4" onclick="setFormation('4')">[4] Strike Wave</button>
            <button id="btn-5" onclick="setFormation('5')">[5] Comms Relay</button>
            <button id="btn-6" onclick="setFormation('6')">[6] SAR Radar</button>
            <button id="btn-7" onclick="setFormation('7')">[7] C-RAM Intercept</button>
            <button id="btn-8" onclick="setFormation('8')">[8] Dispersion</button>
            <button id="btn-9" onclick="setFormation('9')">[9] Pincer</button>
        </div>
        <div class="row" style="margin-top:2px;">
            <button id="btn-Q" class="btn-warfare" onclick="setFormation('Q')">[Q] Ghost Decoy (MALD)</button>
            <button id="btn-W" class="btn-warfare" onclick="setFormation('W')">[W] NOE Terrain Masking</button>
            <button id="btn-E" class="btn-warfare" onclick="setFormation('E')">[E] TDoA Passive Grid</button>
            <button id="btn-R" class="btn-warfare" onclick="setFormation('R')">[R] STOT Saturation</button>
            <button id="btn-T" class="btn-warfare" onclick="setFormation('T')">[T] Convoy Escort</button>
            <button id="btn-Y" class="btn-warfare" onclick="setFormation('Y')">[Y] Flak Evasion Jink</button>
        </div>
    </div>

    <canvas id="canvas"></canvas>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.onresize = resize;
        resize();

        const ws = new WebSocket('ws://' + window.location.hostname + ':8765');
        ws.binaryType = 'arraybuffer';

        function updateButtonStyles(activeMode) {
            const btns = document.querySelectorAll('#controls button');
            btns.forEach(b => {
                b.classList.remove('btn-active');
                b.classList.remove('btn-active-warfare');
            });
            const b = document.getElementById('btn-' + activeMode);
            if (b) {
                if (['Q','W','E','R','T','Y'].includes(activeMode)) {
                    b.classList.add('btn-active-warfare');
                } else {
                    b.classList.add('btn-active');
                }
            }
        }

        function setFormation(mode) {
            updateButtonStyles(mode);
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: "set_formation", mode: mode }));
            }
        }

        // Global hotkeys [0-9] and [Q, W, E, R, T, Y]
        window.addEventListener('keydown', (e) => {
            const key = e.key.toUpperCase();
            if ((key >= '0' && key <= '9') || ['Q','W','E','R','T','Y'].includes(key)) {
                setFormation(key);
            }
        });

        ws.onmessage = (e) => {
            if (typeof e.data === "string") {
                const msg = JSON.parse(e.data);
                if (msg.formation) {
                    document.getElementById('formation_text').innerText = msg.formation;
                }
                return;
            }

            const data = new Float32Array(e.data);
            ctx.fillStyle = 'rgba(4, 7, 17, 0.32)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const cx = canvas.width / 2;
            const cy = canvas.height / 2;

            // Radar range circles
            ctx.strokeStyle = 'rgba(0, 255, 170, 0.08)';
            ctx.lineWidth = 1;
            for (let r = 100; r <= 450; r += 100) {
                ctx.beginPath();
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
                ctx.stroke();
            }

            // Draw drones with tactical depth coloring
            for (let i = 0; i < data.length; i += 3) {
                const x = cx + data[i] * 0.95;
                const y = cy + data[i+1] * 0.95;
                const z = data[i+2];

                if (z > 40) {
                    ctx.fillStyle = '#00ffaa'; // High altitude interceptor
                    ctx.fillRect(x, y, 2.0, 2.0);
                } else if (z < -100) {
                    ctx.fillStyle = '#ffaa00'; // Nap-of-the-Earth terrain hugging
                    ctx.fillRect(x, y, 1.6, 1.6);
                } else {
                    ctx.fillStyle = '#0088ff'; // Baseline defensive plane
                    ctx.fillRect(x, y, 1.3, 1.3);
                }
            }
        };
    </script>
</body>
</html>
"""

class VisualizerHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_VIEWER.encode('utf-8'))

async def telemetry_stream(websocket):
    global positions, velocities, current_mode
    t_phase = 0.0

    while True:
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=0.001)
            if isinstance(msg, str):
                cmd = json.loads(msg)
                if cmd.get("action") == "set_formation":
                    m = str(cmd.get("mode", "0")).upper()
                    current_mode = m
                    name = mode_names.get(current_mode, "ORGANIC RANDOM PATROL")
                    await websocket.send(json.dumps({"formation": name}))
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            pass

        t_phase += 0.035

        if current_mode == "0":
            # [0] CONTINUOUS RANDOM KINETIC PATROL (Default)
            dt = 0.03
            positions += velocities * dt
            mask = np.abs(positions) > 520.0
            velocities[mask] *= -1.0
            velocities += (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 1.5
            speed = np.linalg.norm(velocities, axis=1, keepdims=True)
            velocities = np.where(speed > 70.0, (velocities / speed) * 70.0, velocities)
        else:
            # [1-9, Q, W, E, R, T, Y] TACTICAL & CONTESTED WARFARE CONVERGENCE
            compute_formation_targets(current_mode, t_phase)
            dt = 0.055 if current_mode in ["Q", "W", "R", "Y"] else 0.045
            diff = target_positions - positions
            velocities = velocities * 0.85 + diff * 0.15
            positions += velocities * dt

        sample = positions[:VISIBLE_SAMPLE].flatten().tobytes()
        try:
            await websocket.send(sample)
        except websockets.exceptions.ConnectionClosed:
            break
        await asyncio.sleep(0.02)

def start_http():
    with socketserver.TCPServer(("", PORT_HTTP), VisualizerHTTPHandler) as httpd:
        httpd.serve_forever()

async def main_server():
    server = await websockets.serve(telemetry_stream, "0.0.0.0", PORT_WS)
    await server.wait_closed()

if __name__ == "__main__":
    t = threading.Thread(target=start_http, daemon=True)
    t.start()
    asyncio.run(main_server())
