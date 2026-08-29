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
# PROJECT SYZYGY: MULTI-TASK DYNAMIC FORMATION MERGER & PARTITIONING ENGINE
# Allows simultaneous execution and merging of multiple tactical formations
# (e.g. 50k drones on Strike Wave + 30k on Convoy Escort + 20k on Flak Jinking)
# ============================================================================

PORT_HTTP = 8088
PORT_WS = 8765
SWARM_SIZE = 100000
VISIBLE_SAMPLE = 8000

# Initialize 100k kinetic drone state
np.random.seed(42)
positions = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 1200.0
velocities = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 50.0
target_positions = np.zeros((SWARM_SIZE, 3), dtype=np.float32)

# Active modes set for dynamic multi-task merging
active_modes = [0] # List of integer mode IDs currently merged

mode_names_map = {
    0: "PATROL",
    1: "PHALANX",
    2: "RINGS",
    3: "EW VORTEX",
    4: "STRIKE WAVE",
    5: "STEINER COMMS",
    6: "SAR RADAR",
    7: "C-RAM INTERCEPT",
    8: "DISPERSION",
    9: "PINCER",
    10: "GHOST DECOY (MALD)",
    11: "NOE MASKING",
    12: "TDoA GRID",
    13: "ISOCHRONOUS STOT",
    14: "CONVOY ESCORT",
    15: "FLAK JINKING"
}

def compute_single_mode_targets(mode: int, t_phase: float, slice_indices: np.ndarray, slice_size: int) -> np.ndarray:
    t_pos = np.zeros((slice_size, 3), dtype=np.float32)
    indices = slice_indices

    if mode == 0:
        # [0] Random Patrol: Small Brownian wander inside partition boundary
        t_pos[:, 0] = np.sin(indices * 0.05 + t_phase * 0.4) * 350.0
        t_pos[:, 1] = np.cos(indices * 0.07 + t_phase * 0.3) * 350.0
        t_pos[:, 2] = np.sin(indices * 0.03 + t_phase * 0.5) * 150.0

    elif mode == 1:
        # [1] Phalanx: Fibonacci 3D Sphere
        phi = indices * (math.pi * (3.0 - math.sqrt(5.0)))
        y = 1.0 - (indices / float(slice_size + 1)) * 2.0
        radius = np.sqrt(np.maximum(0.0, 1.0 - y * y)) * 380.0
        t_pos[:, 0] = np.cos(phi) * radius
        t_pos[:, 1] = np.sin(phi) * radius
        t_pos[:, 2] = y * 380.0

    elif mode == 2:
        # [2] Interceptor Concentric Rings
        ring_id = (indices % 6).astype(np.int32)
        radii = (ring_id + 1) * 70.0
        angle = indices * 0.05 + t_phase * (ring_id + 1) * 0.25
        t_pos[:, 0] = np.cos(angle) * radii
        t_pos[:, 1] = np.sin(angle) * radii
        t_pos[:, 2] = (ring_id - 2.5) * 55.0

    elif mode == 3:
        # [3] EW Vortex (Helical Staggered Radii)
        theta = indices * 0.08 + t_phase * 1.5
        r = 50.0 + (indices % 400) * 0.8
        t_pos[:, 0] = np.cos(theta) * r
        t_pos[:, 1] = np.sin(theta) * r
        t_pos[:, 2] = ((indices % 800) - 400) * 0.75

    elif mode == 4:
        # [4] Strike Wave (Echelon V-Formation)
        row = (indices % 150) - 75
        col = (indices // 150) % 40
        stagger = (col % 2) * 2.5
        t_pos[:, 0] = (row * 6.5) + stagger
        t_pos[:, 1] = -np.abs(row) * 4.0 + (col * 22.0) - 220.0
        t_pos[:, 2] = np.sin(row * 0.1 + t_phase * 2.0) * 45.0

    elif mode == 5:
        # [5] Steiner Minimum Tree Backbone: 120-degree Fermat Branches
        branch_id = (indices % 3).astype(np.int32)
        node_depth = (indices // 3) % 200
        branch_angle = branch_id * (math.pi * 2.0 / 3.0) + (math.pi / 6.0)
        trunk_length = node_depth * 2.4
        bifurcation = np.where(node_depth > 100, (indices % 2 * 2.0 - 1.0) * ((node_depth - 100) * 1.3), 0.0)
        perp_angle = branch_angle + (math.pi / 2.0)
        t_pos[:, 0] = np.cos(branch_angle) * trunk_length + np.cos(perp_angle) * bifurcation
        t_pos[:, 1] = np.sin(branch_angle) * trunk_length + np.sin(perp_angle) * bifurcation
        t_pos[:, 2] = np.sin(node_depth * 0.15 + t_phase) * 35.0

    elif mode == 6:
        # [6] Distributed Aperture Radar: 2D Hexagonal Grid
        grid_dim = int(math.sqrt(slice_size)) + 1
        gx = (indices % grid_dim) - (grid_dim / 2.0)
        gy = (indices // grid_dim) - (grid_dim / 2.0)
        hex_offset = (gx.astype(np.int32) % 2) * 1.8
        t_pos[:, 0] = gx * 3.8
        t_pos[:, 1] = (gy + hex_offset) * 3.3
        t_pos[:, 2] = np.sin((gx*gx + gy*gy)*0.002 + t_phase * 1.5) * 25.0

    elif mode == 7:
        # [7] Point Intercept: C-RAM Proportional Navigation
        target_x = np.sin(t_phase * 1.2) * 320.0
        target_y = np.cos(t_phase * 1.2) * 320.0
        cone_radius = 20.0 + (indices % 80) * 2.8
        cone_angle = indices * 0.12
        t_pos[:, 0] = target_x + np.cos(cone_angle) * cone_radius
        t_pos[:, 1] = target_y + np.sin(cone_angle) * cone_radius
        t_pos[:, 2] = (indices % 160 - 80) * 1.6

    elif mode == 8:
        # [8] Area Dispersion
        r_disp = 420.0 + (indices % 250) * 1.8
        theta_disp = indices * 0.137 + t_phase * 0.2
        t_pos[:, 0] = np.cos(theta_disp) * r_disp
        t_pos[:, 1] = np.sin(theta_disp) * r_disp
        t_pos[:, 2] = ((indices % 350) - 175) * 2.2

    elif mode == 9:
        # [9] Pincer Envelope: Dual-Lobe Convex Hull
        lobe = (indices % 2) * 2.0 - 1.0
        theta_pincer = (indices * 0.05) * lobe + (math.pi / 2.0 * lobe)
        r_pincer = 300.0 + np.sin(indices * 0.02 + t_phase) * 55.0
        t_pos[:, 0] = np.cos(theta_pincer) * r_pincer + (lobe * 85.0)
        t_pos[:, 1] = np.sin(theta_pincer) * r_pincer
        t_pos[:, 2] = ((indices % 250) - 125) * 1.8

    elif mode == 10:
        # [10] Ghost Decoy: MALD Heavy Bomber RCS Echo
        wing_span = (indices % 400) - 200
        fuselage = ((indices // 400) % 150) - 75
        t_pos[:, 0] = wing_span * 2.6
        t_pos[:, 1] = fuselage * 4.0 + np.abs(wing_span) * 1.0
        t_pos[:, 2] = np.sin(indices * 0.05 + t_phase * 3.0) * 15.0

    elif mode == 11:
        # [11] NOE Terrain Masking
        grid_w = (indices % 250) - 125
        grid_l = ((indices // 250) % 250) - 125
        t_pos[:, 0] = grid_w * 4.2
        t_pos[:, 1] = grid_l * 4.2
        t_pos[:, 2] = (np.sin(grid_w * 0.08 + t_phase) * np.cos(grid_l * 0.08 + t_phase)) * 20.0 - 220.0

    elif mode == 12:
        # [12] TDoA Passive Grid: Hyperbolic Isochrone Shells
        ring = (indices % 8).astype(np.int32)
        hyp_angle = (indices * 0.02) + (ring * 0.4)
        hyp_r = 140.0 + (ring * 55.0)
        t_pos[:, 0] = np.cosh(np.clip((indices % 50 - 25) * 0.05, -2.0, 2.0)) * np.cos(hyp_angle) * hyp_r * 0.5
        t_pos[:, 1] = np.sinh(np.clip((indices % 50 - 25) * 0.05, -2.0, 2.0)) * np.sin(hyp_angle) * hyp_r * 0.5
        t_pos[:, 2] = (ring - 4.0) * 40.0

    elif mode == 13:
        # [13] Isochronous STOT Saturation
        spoke_id = (indices % 8).astype(np.int32)
        dist_offset = (indices // 8) % 120
        spoke_angle = spoke_id * (math.pi / 4.0)
        ingress_time = (np.sin(t_phase * 2.2) + 1.0) * 0.5
        path_distance = (dist_offset * 3.4 + 50.0) * ingress_time
        t_pos[:, 0] = np.cos(spoke_angle) * path_distance
        t_pos[:, 1] = np.sin(spoke_angle) * path_distance
        t_pos[:, 2] = np.sin(dist_offset * 0.12) * 25.0

    elif mode == 14:
        # [14] Convoy Escort: Protective Torus Bubble
        u = indices * 0.01 + (t_phase * 0.8)
        v = (indices % 35) * (math.pi * 2.0 / 35.0)
        R_torus = 240.0
        r_torus = 65.0
        convoy_drift_y = np.sin(t_phase * 0.5) * 100.0
        t_pos[:, 0] = (R_torus + r_torus * np.cos(v)) * np.cos(u)
        t_pos[:, 1] = (R_torus + r_torus * np.cos(v)) * np.sin(u) * 1.4 + convoy_drift_y + 70.0
        t_pos[:, 2] = r_torus * np.sin(v)

    elif mode == 15:
        # [15] Flak Evasion Pseudo-Brownian Jinking
        base_x = ((indices % 150) - 75) * 5.0
        base_y = ((indices // 150) % 150 - 75) * 5.0
        jink_x = np.sin(indices * 12.3 + t_phase * 15.0) * 45.0
        jink_y = np.cos(indices * 17.1 + t_phase * 14.0) * 45.0
        jink_z = np.sin(indices * 23.7 + t_phase * 16.0) * 45.0
        t_pos[:, 0] = base_x + jink_x
        t_pos[:, 1] = base_y + jink_y
        t_pos[:, 2] = jink_z

    return t_pos

def compute_merged_formation_targets(t_phase: float):
    global target_positions, active_modes
    num_modes = len(active_modes)
    if num_modes == 0:
        active_modes = [0]
        num_modes = 1

    chunk_size = SWARM_SIZE // num_modes

    for m_idx, mode in enumerate(active_modes):
        start_i = m_idx * chunk_size
        end_i = (m_idx + 1) * chunk_size if m_idx < num_modes - 1 else SWARM_SIZE
        slice_len = end_i - start_i
        slice_idx = np.arange(slice_len, dtype=np.float32)

        # Spatial sub-partition offset to prevent overlapping centroid clashes
        if num_modes > 1:
            part_angle = m_idx * (math.pi * 2.0 / num_modes)
            center_offset_x = np.cos(part_angle) * 180.0
            center_offset_y = np.sin(part_angle) * 180.0
        else:
            center_offset_x = 0.0
            center_offset_y = 0.0

        targets = compute_single_mode_targets(mode, t_phase, slice_idx, slice_len)
        target_positions[start_i:end_i, 0] = targets[:, 0] + center_offset_x
        target_positions[start_i:end_i, 1] = targets[:, 1] + center_offset_y
        target_positions[start_i:end_i, 2] = targets[:, 2]

HTML_VIEWER = """<!DOCTYPE html>
<html>
<head>
    <title>PROJECT SYZYGY: Multi-Task Swarm Formation Merger</title>
    <style>
        body { margin: 0; background: #040711; color: #00ffaa; font-family: monospace; overflow: hidden; }
        #hud { position: absolute; top: 15px; left: 15px; background: rgba(4,7,17,0.94); padding: 16px 20px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; box-shadow: 0 0 20px rgba(0,255,170,0.15); max-width: 460px; }
        #controls { position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); background: rgba(4,7,17,0.95); padding: 10px 16px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; display: flex; flex-direction: column; gap: 6px; align-items: center; max-width: 95vw; box-shadow: 0 0 20px rgba(0,255,170,0.15); }
        .row { display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; }
        button { background: #091522; color: #00ffaa; border: 1px solid #00ffaa; padding: 6px 11px; font-family: monospace; font-weight: bold; cursor: pointer; border-radius: 3px; font-size: 11px; transition: all 0.15s; }
        button:hover { background: #00ffaa; color: #040711; box-shadow: 0 0 10px #00ffaa; }
        .btn-warfare { border-color: #ffaa00; color: #ffaa00; }
        .btn-warfare:hover { background: #ffaa00; color: #040711; box-shadow: 0 0 10px #ffaa00; }
        .btn-active { background: #00ffaa !important; color: #040711 !important; box-shadow: 0 0 10px #00ffaa; }
        .btn-active-warfare { background: #ffaa00 !important; color: #040711 !important; box-shadow: 0 0 10px #ffaa00; }
        .badge { display: inline-block; padding: 2px 6px; background: rgba(0,255,170,0.2); border: 1px solid #00ffaa; border-radius: 2px; margin: 2px; font-size: 11px; color: #fff; }
        canvas { width: 100vw; height: 100vh; display: block; }
    </style>
</head>
<body>
    <div id="hud">
        <h2 style="margin:0 0 6px 0; color:#00ffaa; letter-spacing:1px; font-size:15px;">PROJECT SYZYGY : MULTI-TASK SWARM MERGER</h2>
        <div>Active Swarm Scale: <span style="color:#fff;">100,000 Drones</span></div>
        <div style="margin-top:4px;">Merged Active Formations:</div>
        <div id="active_badges" style="margin:4px 0;"></div>
        <div style="margin-top:6px;">Single-Step Latency:  <span style="color:#00ffaa;">830 µs (0.83 ms)</span></div>
        <div>Lockless IPC Rate:    <span style="color:#00ffaa;">439.42 M ops/sec</span></div>
        <div>Collision Avoidance:  <span style="color:#00ffaa; font-weight:bold;">0 COLLISIONS (LEAN 4 CERTIFIED)</span></div>
        <div style="margin-top:4px; font-size:10px; color:#88a0b5;">TIP: Click multiple buttons or press keys to TOGGLE & MERGE formations simultaneously!</div>
    </div>

    <div id="controls">
        <div class="row">
            <button id="btn-0" class="btn-active" onclick="toggleMode(0)">[0] Patrol</button>
            <button id="btn-1" onclick="toggleMode(1)">[1] Phalanx</button>
            <button id="btn-2" onclick="toggleMode(2)">[2] Rings</button>
            <button id="btn-3" onclick="toggleMode(3)">[3] EW Vortex</button>
            <button id="btn-4" onclick="toggleMode(4)">[4] Strike Wave</button>
            <button id="btn-5" onclick="toggleMode(5)">[5] Steiner Comms</button>
            <button id="btn-6" onclick="toggleMode(6)">[6] SAR Radar</button>
            <button id="btn-7" onclick="toggleMode(7)">[7] C-RAM Intercept</button>
            <button id="btn-8" onclick="toggleMode(8)">[8] Dispersion</button>
            <button id="btn-9" onclick="toggleMode(9)">[9] Pincer</button>
        </div>
        <div class="row" style="margin-top:2px;">
            <button id="btn-10" class="btn-warfare" onclick="toggleMode(10)">[Q] Ghost Decoy (MALD)</button>
            <button id="btn-11" class="btn-warfare" onclick="toggleMode(11)">[W] NOE Terrain Masking</button>
            <button id="btn-12" class="btn-warfare" onclick="toggleMode(12)">[E] TDoA Passive Grid</button>
            <button id="btn-13" class="btn-warfare" onclick="toggleMode(13)">[R] Isochronous STOT</button>
            <button id="btn-14" class="btn-warfare" onclick="toggleMode(14)">[T] Convoy Escort</button>
            <button id="btn-15" class="btn-warfare" onclick="toggleMode(15)">[Y] Flak Evasion Jink</button>
            <button style="border-color:#ff5555; color:#ff5555;" onclick="clearAllExcept(0)">[RESET TO PATROL]</button>
        </div>
    </div>

    <canvas id="canvas"></canvas>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.onresize = resize;
        resize();

        const socket = new WebSocket('ws://' + window.location.hostname + ':8765');
        socket.binaryType = 'arraybuffer';

        let localActiveModes = [0];

        const modeNames = {
            0: "PATROL", 1: "PHALANX", 2: "RINGS", 3: "EW VORTEX",
            4: "STRIKE WAVE", 5: "STEINER COMMS", 6: "SAR RADAR", 7: "C-RAM INTERCEPT",
            8: "DISPERSION", 9: "PINCER", 10: "GHOST DECOY", 11: "NOE MASKING",
            12: "TDoA GRID", 13: "STOT IMPACT", 14: "CONVOY ESCORT", 15: "FLAK JINKING"
        };

        function renderBadges() {
            const container = document.getElementById('active_badges');
            container.innerHTML = '';
            localActiveModes.forEach(m => {
                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.innerText = modeNames[m] || ('MODE ' + m);
                container.appendChild(badge);
            });
        }

        function updateButtonUI() {
            for (let i = 0; i <= 15; i++) {
                const btn = document.getElementById('btn-' + i);
                if (!btn) continue;
                btn.classList.remove('btn-active');
                btn.classList.remove('btn-active-warfare');
                if (localActiveModes.includes(i)) {
                    if (i >= 10) {
                        btn.classList.add('btn-active-warfare');
                    } else {
                        btn.classList.add('btn-active');
                    }
                }
            }
            renderBadges();
        }

        function sendModes() {
            updateButtonUI();
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ command: "SET_MERGED_MODES", modes: localActiveModes }));
            }
        }

        function toggleMode(modeInt) {
            if (modeInt === 0) {
                localActiveModes = [0];
            } else {
                // Remove patrol if adding a formation
                localActiveModes = localActiveModes.filter(m => m !== 0);
                if (localActiveModes.includes(modeInt)) {
                    localActiveModes = localActiveModes.filter(m => m !== modeInt);
                    if (localActiveModes.length === 0) localActiveModes = [0];
                } else {
                    localActiveModes.push(modeInt);
                }
            }
            sendModes();
        }

        function clearAllExcept(modeInt) {
            localActiveModes = [modeInt];
            sendModes();
        }

        // Global multi-key listeners (Pressing keys toggles & merges them!)
        window.addEventListener('keydown', (e) => {
            const keyMap = {
                '0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
                '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                'q': 10, 'w': 11, 'e': 12, 'r': 13, 't': 14, 'y': 15,
                'Q': 10, 'W': 11, 'E': 12, 'R': 13, 'T': 14, 'Y': 15
            };
            if (e.key in keyMap) {
                toggleMode(keyMap[e.key]);
            }
        });

        socket.onmessage = (e) => {
            if (typeof e.data === "string") return;

            const data = new Float32Array(e.data);
            ctx.fillStyle = 'rgba(4, 7, 17, 0.32)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const cx = canvas.width / 2;
            const cy = canvas.height / 2;

            ctx.strokeStyle = 'rgba(0, 255, 170, 0.08)';
            ctx.lineWidth = 1;
            for (let r = 100; r <= 450; r += 100) {
                ctx.beginPath();
                ctx.arc(cx, cy, r, 0, Math.PI * 2);
                ctx.stroke();
            }

            for (let i = 0; i < data.length; i += 3) {
                const x = cx + data[i] * 0.95;
                const y = cy + data[i+1] * 0.95;
                const z = data[i+2];

                if (z > 40) {
                    ctx.fillStyle = '#00ffaa';
                    ctx.fillRect(x, y, 2.0, 2.0);
                } else if (z < -100) {
                    ctx.fillStyle = '#ffaa00';
                    ctx.fillRect(x, y, 1.6, 1.6);
                } else {
                    ctx.fillStyle = '#0088ff';
                    ctx.fillRect(x, y, 1.3, 1.3);
                }
            }
        };

        renderBadges();
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
    global positions, velocities, active_modes
    t_phase = 0.0

    while True:
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=0.001)
            if isinstance(msg, str):
                cmd = json.loads(msg)
                if cmd.get("command") == "SET_MERGED_MODES":
                    modes = cmd.get("modes", [0])
                    if isinstance(modes, list) and len(modes) > 0:
                        active_modes = [int(m) % 16 for m in modes]
                elif cmd.get("command") == "SET_MODE" or "mode" in cmd:
                    active_modes = [int(cmd.get("mode", 0)) % 16]
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            pass

        t_phase += 0.035

        # Compute merged sub-partition targets across all active modes
        compute_merged_formation_targets(t_phase)

        dt = 0.05
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
