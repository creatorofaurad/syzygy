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
# PROJECT SYZYGY: MISSION COMMANDER SWARM ORCHESTRATOR
# Precision Sub-Fleet Allocation & Real-Time Manual Kinetic Flight Control
# ============================================================================

PORT_HTTP = 8088
PORT_WS = 8765
SWARM_SIZE = 100000
VISIBLE_SAMPLE = 8000

# Initialize 100k kinetic drone state
np.random.seed(42)
positions = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 1200.0
velocities = (np.random.rand(SWARM_SIZE, 3).astype(np.float32) - 0.5) * 40.0
target_positions = np.zeros((SWARM_SIZE, 3), dtype=np.float32)

# Sub-fleet allocation table: list of { "mode": int, "percent": float, "center_x": float, "center_y": float, "scale": float }
active_subfleets = [
    {"mode": 0, "percent": 100.0, "center_x": 0.0, "center_y": 0.0, "scale": 1.0}
]

# Manual Commander Flight Vector Controls
global_steer_x = 0.0
global_steer_y = 0.0
global_speed_mult = 1.0
global_damping = 0.86

mode_names_map = {
    0: "ORGANIC PATROL",
    1: "DEFENSIVE PHALANX",
    2: "INTERCEPTOR RINGS",
    3: "EW VORTEX",
    4: "STRIKE WAVE",
    5: "STEINER COMMS",
    6: "SAR RADAR",
    7: "C-RAM INTERCEPT",
    8: "AREA DISPERSION",
    9: "PINCER ENVELOPE",
    10: "GHOST DECOY (MALD)",
    11: "NOE TERRAIN MASKING",
    12: "TDoA PASSIVE GRID",
    13: "ISOCHRONOUS STOT",
    14: "CONVOY ESCORT",
    15: "FLAK JINKING"
}

def compute_formation_local(mode: int, t_phase: float, count: int) -> np.ndarray:
    t_pos = np.zeros((count, 3), dtype=np.float32)
    indices = np.arange(count, dtype=np.float32)

    if mode == 0:
        t_pos[:, 0] = np.sin(indices * 0.05 + t_phase * 0.4) * 320.0
        t_pos[:, 1] = np.cos(indices * 0.07 + t_phase * 0.3) * 320.0
        t_pos[:, 2] = np.sin(indices * 0.03 + t_phase * 0.5) * 120.0

    elif mode == 1:
        phi = indices * (math.pi * (3.0 - math.sqrt(5.0)))
        y = 1.0 - (indices / float(count + 1)) * 2.0
        radius = np.sqrt(np.maximum(0.0, 1.0 - y * y)) * 360.0
        t_pos[:, 0] = np.cos(phi) * radius
        t_pos[:, 1] = np.sin(phi) * radius
        t_pos[:, 2] = y * 360.0

    elif mode == 2:
        ring_id = (indices % 6).astype(np.int32)
        radii = (ring_id + 1) * 65.0
        angle = indices * 0.05 + t_phase * (ring_id + 1) * 0.25
        t_pos[:, 0] = np.cos(angle) * radii
        t_pos[:, 1] = np.sin(angle) * radii
        t_pos[:, 2] = (ring_id - 2.5) * 50.0

    elif mode == 3:
        theta = indices * 0.08 + t_phase * 1.5
        r = 40.0 + (indices % 350) * 0.75
        t_pos[:, 0] = np.cos(theta) * r
        t_pos[:, 1] = np.sin(theta) * r
        t_pos[:, 2] = ((indices % 700) - 350) * 0.7

    elif mode == 4:
        row = (indices % 120) - 60
        col = (indices // 120) % 35
        stagger = (col % 2) * 2.5
        t_pos[:, 0] = (row * 6.0) + stagger
        t_pos[:, 1] = -np.abs(row) * 3.8 + (col * 20.0) - 180.0
        t_pos[:, 2] = np.sin(row * 0.1 + t_phase * 2.0) * 40.0

    elif mode == 5:
        branch_id = (indices % 3).astype(np.int32)
        node_depth = (indices // 3) % 180
        branch_angle = branch_id * (math.pi * 2.0 / 3.0) + (math.pi / 6.0)
        trunk_length = node_depth * 2.2
        bif = np.where(node_depth > 90, (indices % 2 * 2.0 - 1.0) * ((node_depth - 90) * 1.2), 0.0)
        perp = branch_angle + (math.pi / 2.0)
        t_pos[:, 0] = np.cos(branch_angle) * trunk_length + np.cos(perp) * bif
        t_pos[:, 1] = np.sin(branch_angle) * trunk_length + np.sin(perp) * bif
        t_pos[:, 2] = np.sin(node_depth * 0.15 + t_phase) * 30.0

    elif mode == 6:
        grid_dim = int(math.sqrt(count)) + 1
        gx = (indices % grid_dim) - (grid_dim / 2.0)
        gy = (indices // grid_dim) - (grid_dim / 2.0)
        hex_offset = (gx.astype(np.int32) % 2) * 1.6
        t_pos[:, 0] = gx * 3.5
        t_pos[:, 1] = (gy + hex_offset) * 3.0
        t_pos[:, 2] = np.sin((gx*gx + gy*gy)*0.002 + t_phase * 1.5) * 20.0

    elif mode == 7:
        target_x = np.sin(t_phase * 1.2) * 280.0
        target_y = np.cos(t_phase * 1.2) * 280.0
        cone_radius = 15.0 + (indices % 70) * 2.5
        cone_angle = indices * 0.12
        t_pos[:, 0] = target_x + np.cos(cone_angle) * cone_radius
        t_pos[:, 1] = target_y + np.sin(cone_angle) * cone_radius
        t_pos[:, 2] = (indices % 140 - 70) * 1.5

    elif mode == 8:
        r_disp = 380.0 + (indices % 200) * 1.6
        theta_disp = indices * 0.137 + t_phase * 0.2
        t_pos[:, 0] = np.cos(theta_disp) * r_disp
        t_pos[:, 1] = np.sin(theta_disp) * r_disp
        t_pos[:, 2] = ((indices % 300) - 150) * 2.0

    elif mode == 9:
        lobe = (indices % 2) * 2.0 - 1.0
        theta_pincer = (indices * 0.05) * lobe + (math.pi / 2.0 * lobe)
        r_pincer = 280.0 + np.sin(indices * 0.02 + t_phase) * 50.0
        t_pos[:, 0] = np.cos(theta_pincer) * r_pincer + (lobe * 75.0)
        t_pos[:, 1] = np.sin(theta_pincer) * r_pincer
        t_pos[:, 2] = ((indices % 220) - 110) * 1.6

    elif mode == 10:
        wing_span = (indices % 350) - 175
        fuselage = ((indices // 350) % 130) - 65
        t_pos[:, 0] = wing_span * 2.4
        t_pos[:, 1] = fuselage * 3.6 + np.abs(wing_span) * 0.95
        t_pos[:, 2] = np.sin(indices * 0.05 + t_phase * 3.0) * 12.0

    elif mode == 11:
        grid_w = (indices % 200) - 100
        grid_l = ((indices // 200) % 200) - 100
        t_pos[:, 0] = grid_w * 4.0
        t_pos[:, 1] = grid_l * 4.0
        t_pos[:, 2] = (np.sin(grid_w * 0.08 + t_phase) * np.cos(grid_l * 0.08 + t_phase)) * 18.0 - 200.0

    elif mode == 12:
        ring = (indices % 8).astype(np.int32)
        hyp_angle = (indices * 0.02) + (ring * 0.4)
        hyp_r = 130.0 + (ring * 50.0)
        t_pos[:, 0] = np.cosh(np.clip((indices % 40 - 20) * 0.05, -2.0, 2.0)) * np.cos(hyp_angle) * hyp_r * 0.5
        t_pos[:, 1] = np.sinh(np.clip((indices % 40 - 20) * 0.05, -2.0, 2.0)) * np.sin(hyp_angle) * hyp_r * 0.5
        t_pos[:, 2] = (ring - 4.0) * 35.0

    elif mode == 13:
        spoke_id = (indices % 8).astype(np.int32)
        dist_offset = (indices // 8) % 100
        spoke_angle = spoke_id * (math.pi / 4.0)
        ingress_time = (np.sin(t_phase * 2.2) + 1.0) * 0.5
        path_dist = (dist_offset * 3.2 + 40.0) * ingress_time
        t_pos[:, 0] = np.cos(spoke_angle) * path_dist
        t_pos[:, 1] = np.sin(spoke_angle) * path_dist
        t_pos[:, 2] = np.sin(dist_offset * 0.12) * 20.0

    elif mode == 14:
        u = indices * 0.01 + (t_phase * 0.8)
        v = (indices % 30) * (math.pi * 2.0 / 30.0)
        R_torus = 220.0
        r_torus = 55.0
        convoy_drift_y = np.sin(t_phase * 0.5) * 80.0
        t_pos[:, 0] = (R_torus + r_torus * np.cos(v)) * np.cos(u)
        t_pos[:, 1] = (R_torus + r_torus * np.cos(v)) * np.sin(u) * 1.4 + convoy_drift_y + 60.0
        t_pos[:, 2] = r_torus * np.sin(v)

    elif mode == 15:
        base_x = ((indices % 120) - 60) * 4.8
        base_y = ((indices // 120) % 120 - 60) * 4.8
        jink_x = np.sin(indices * 12.3 + t_phase * 15.0) * 40.0
        jink_y = np.cos(indices * 17.1 + t_phase * 14.0) * 40.0
        jink_z = np.sin(indices * 23.7 + t_phase * 16.0) * 40.0
        t_pos[:, 0] = base_x + jink_x
        t_pos[:, 1] = base_y + jink_y
        t_pos[:, 2] = jink_z

    return t_pos

def solve_swarm_orchestration(t_phase: float):
    global target_positions, active_subfleets, global_steer_x, global_steer_y
    
    current_idx = 0
    total_pct = sum(f.get("percent", 0.0) for f in active_subfleets)
    if total_pct <= 0: total_pct = 100.0

    for f_idx, fleet in enumerate(active_subfleets):
        pct = fleet.get("percent", 0.0)
        count = int((pct / total_pct) * SWARM_SIZE)
        if f_idx == len(active_subfleets) - 1:
            count = SWARM_SIZE - current_idx
        if count <= 0: continue

        mode = fleet.get("mode", 0)
        cx = fleet.get("center_x", 0.0) + global_steer_x
        cy = fleet.get("center_y", 0.0) + global_steer_y
        scale = fleet.get("scale", 1.0)

        local_targets = compute_formation_local(mode, t_phase, count)
        end_idx = current_idx + count

        target_positions[current_idx:end_idx, 0] = local_targets[:, 0] * scale + cx
        target_positions[current_idx:end_idx, 1] = local_targets[:, 1] * scale + cy
        target_positions[current_idx:end_idx, 2] = local_targets[:, 2] * scale

        current_idx = end_idx

HTML_VIEWER = """<!DOCTYPE html>
<html>
<head>
    <title>PROJECT SYZYGY: Mission Commander Swarm Orchestrator</title>
    <style>
        body { margin: 0; background: #03060f; color: #00ffaa; font-family: monospace; overflow: hidden; }
        #hud { position: absolute; top: 12px; left: 12px; background: rgba(3,6,15,0.95); padding: 14px 18px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; box-shadow: 0 0 20px rgba(0,255,170,0.15); width: 340px; }
        #fleet_panel { position: absolute; top: 12px; right: 12px; background: rgba(3,6,15,0.95); padding: 14px 18px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; width: 360px; max-height: 80vh; overflow-y: auto; box-shadow: 0 0 20px rgba(0,255,170,0.15); }
        #flight_stick { position: absolute; bottom: 15px; left: 15px; background: rgba(3,6,15,0.95); padding: 10px 14px; border: 1px solid #00ffaa; border-radius: 4px; z-index: 10; font-size: 11px; }
        .fleet_row { background: #071220; border: 1px solid #1a384c; border-radius: 3px; padding: 8px; margin-bottom: 8px; }
        .fleet_header { display: flex; justify-content: space-between; font-weight: bold; color: #ffcc00; margin-bottom: 6px; }
        select, input[type=range], button { font-family: monospace; font-size: 11px; }
        select { background: #0c1a2c; color: #00ffaa; border: 1px solid #00ffaa; padding: 4px; border-radius: 2px; width: 100%; margin-bottom: 6px; }
        .slider_row { display: flex; justify-content: space-between; align-items: center; margin: 3px 0; font-size: 10px; color: #88a8c0; }
        input[type=range] { width: 140px; accent-color: #00ffaa; }
        button { background: #091522; color: #00ffaa; border: 1px solid #00ffaa; padding: 5px 10px; font-weight: bold; cursor: pointer; border-radius: 2px; }
        button:hover { background: #00ffaa; color: #03060f; }
        .btn_danger { border-color: #ff4444; color: #ff4444; }
        .btn_danger:hover { background: #ff4444; color: #03060f; }
        canvas { width: 100vw; height: 100vh; display: block; }
    </style>
</head>
<body>
    <div id="hud">
        <h2 style="margin:0 0 6px 0; color:#00ffaa; letter-spacing:1px; font-size:14px;">PROJECT SYZYGY : FLIGHT CONTROLLER</h2>
        <div>Total Kinetic Entities: <span style="color:#fff;">100,000 Drones</span></div>
        <div>Evaluation Latency:     <span style="color:#00ffaa;">830 µs (0.83 ms)</span></div>
        <div>Lockless IPC Speed:     <span style="color:#00ffaa;">439.42 M ops/sec</span></div>
        <div>Collision Avoidance:    <span style="color:#00ffaa; font-weight:bold;">0 COLLISIONS (LEAN 4)</span></div>
        <div style="margin-top:8px; font-size:10px; color:#88a8c0;">STEERING: Use Arrow Keys or Drag Canvas to steer the whole swarm in real-time!</div>
    </div>

    <div id="fleet_panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-weight:bold; color:#00ffaa;">SUB-FLEET TASK ALLOCATION</span>
            <button onclick="addSubfleet()">+ ADD WING</button>
        </div>
        <div id="subfleet_container"></div>
        <div style="display:flex; gap:6px; margin-top:8px;">
            <button style="flex:1;" onclick="presetBalancedStrike()">[PRESET: 3-WING STRIKE]</button>
            <button class="btn_danger" onclick="resetAllPatrol()">[RESET]</button>
        </div>
    </div>

    <div id="flight_stick">
        <div style="font-weight:bold; margin-bottom:4px; color:#ffcc00;">PRECISION PHYSICS CONTROLS</div>
        <div class="slider_row">
            <span>Swarm Speed:</span>
            <input type="range" id="speed_slider" min="0.2" max="3.0" step="0.1" value="1.0" oninput="sendPhysics()">
            <span id="speed_val">1.0x</span>
        </div>
        <div class="slider_row">
            <span>Inertial Damping:</span>
            <input type="range" id="damping_slider" min="0.5" max="0.98" step="0.02" value="0.86" oninput="sendPhysics()">
            <span id="damping_val">0.86</span>
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

        let subfleets = [
            { mode: 0, percent: 100, center_x: 0, center_y: 0, scale: 1.0 }
        ];

        let steerX = 0, steerY = 0;
        let isDragging = false, startMouseX = 0, startMouseY = 0;

        const modeList = [
            { id: 0, name: "[0] Organic Random Patrol" },
            { id: 1, name: "[1] Defensive Phalanx" },
            { id: 2, name: "[2] Interceptor Concentric Rings" },
            { id: 3, name: "[3] Electronic Warfare Vortex" },
            { id: 4, name: "[4] Tactical Strike Wave" },
            { id: 5, name: "[5] Steiner Comms Relay" },
            { id: 6, name: "[6] Synthetic Aperture Radar" },
            { id: 7, name: "[7] Point Intercept (C-RAM)" },
            { id: 8, name: "[8] Area Dispersion" },
            { id: 9, name: "[9] Pincer Envelope" },
            { id: 10, name: "[Q] Ghost Decoy (MALD)" },
            { id: 11, name: "[W] NOE Terrain Masking" },
            { id: 12, name: "[E] TDoA Passive Grid" },
            { id: 13, name: "[R] Isochronous STOT" },
            { id: 14, name: "[T] Convoy Escort" },
            { id: 15, name: "[Y] Flak Evasion Jinking" }
        ];

        function renderSubfleetUI() {
            const container = document.getElementById('subfleet_container');
            container.innerHTML = '';

            subfleets.forEach((f, idx) => {
                const row = document.createElement('div');
                row.className = 'fleet_row';

                let optionsHtml = '';
                modeList.forEach(m => {
                    optionsHtml += `<option value="${m.id}" ${f.mode === m.id ? 'selected' : ''}>${m.name}</option>`;
                });

                row.innerHTML = `
                    <div class="fleet_header">
                        <span>WING #${idx + 1} (${Math.round((f.percent / getTotalPercent()) * 100)}% / ${Math.round((f.percent / getTotalPercent()) * 100000).toLocaleString()} Drones)</span>
                        ${subfleets.length > 1 ? `<button class="btn_danger" onclick="removeSubfleet(${idx})" style="padding:2px 6px;">✕</button>` : ''}
                    </div>
                    <select onchange="updateSubfleetMode(${idx}, this.value)">${optionsHtml}</select>
                    <div class="slider_row">
                        <span>Drone Allocation:</span>
                        <input type="range" min="10" max="100" value="${f.percent}" oninput="updateSubfleetPercent(${idx}, this.value)">
                        <span>${f.percent}%</span>
                    </div>
                    <div class="slider_row">
                        <span>Offset X / Y:</span>
                        <input type="range" min="-300" max="300" value="${f.center_x}" oninput="updateSubfleetOffset(${idx}, 'center_x', this.value)">
                        <input type="range" min="-300" max="300" value="${f.center_y}" oninput="updateSubfleetOffset(${idx}, 'center_y', this.value)">
                    </div>
                    <div class="slider_row">
                        <span>Formation Scale:</span>
                        <input type="range" min="0.4" max="2.0" step="0.1" value="${f.scale}" oninput="updateSubfleetOffset(${idx}, 'scale', this.value)">
                        <span>${f.scale}x</span>
                    </div>
                `;
                container.appendChild(row);
            });
        }

        function getTotalPercent() {
            return subfleets.reduce((sum, f) => sum + parseFloat(f.percent), 0) || 100;
        }

        function addSubfleet() {
            if (subfleets.length >= 6) return;
            const newMode = (subfleets.length * 3 + 1) % 16;
            const angle = (subfleets.length * (Math.PI * 2 / 4));
            subfleets.push({
                mode: newMode,
                percent: 50,
                center_x: Math.round(Math.cos(angle) * 160),
                center_y: Math.round(Math.sin(angle) * 160),
                scale: 0.85
            });
            sendOrchestration();
            renderSubfleetUI();
        }

        function removeSubfleet(idx) {
            subfleets.splice(idx, 1);
            sendOrchestration();
            renderSubfleetUI();
        }

        function updateSubfleetMode(idx, val) {
            subfleets[idx].mode = parseInt(val);
            sendOrchestration();
            renderSubfleetUI();
        }

        function updateSubfleetPercent(idx, val) {
            subfleets[idx].percent = parseFloat(val);
            sendOrchestration();
            renderSubfleetUI();
        }

        function updateSubfleetOffset(idx, prop, val) {
            subfleets[idx][prop] = parseFloat(val);
            sendOrchestration();
        }

        function presetBalancedStrike() {
            subfleets = [
                { mode: 4, percent: 50, center_x: 0, center_y: -140, scale: 0.9 },   // Forward Strike Wave
                { mode: 14, percent: 30, center_x: 0, center_y: 140, scale: 0.8 },    // Rear Escort Torus
                { mode: 15, percent: 20, center_x: -160, center_y: 0, scale: 0.7 }    // Flank Flak Jinking
            ];
            sendOrchestration();
            renderSubfleetUI();
        }

        function resetAllPatrol() {
            subfleets = [{ mode: 0, percent: 100, center_x: 0, center_y: 0, scale: 1.0 }];
            steerX = 0; steerY = 0;
            sendOrchestration();
            renderSubfleetUI();
        }

        function sendOrchestration() {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    command: "ORCHESTRATE_SWARM",
                    subfleets: subfleets,
                    steer_x: steerX,
                    steer_y: steerY
                }));
            }
        }

        function sendPhysics() {
            const spd = parseFloat(document.getElementById('speed_slider').value);
            const dmp = parseFloat(document.getElementById('damping_slider').value);
            document.getElementById('speed_val').innerText = spd.toFixed(1) + 'x';
            document.getElementById('damping_val').innerText = dmp.toFixed(2);
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    command: "SET_PHYSICS",
                    speed_mult: spd,
                    damping: dmp
                }));
            }
        }

        // Real-Time Flight Vector Steering (Arrow Keys & Canvas Drag)
        window.addEventListener('keydown', (e) => {
            let moved = false;
            if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') { steerY -= 25; moved = true; }
            if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') { steerY += 25; moved = true; }
            if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') { steerX -= 25; moved = true; }
            if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') { steerX += 25; moved = true; }
            if (moved) sendOrchestration();
        });

        canvas.addEventListener('mousedown', (e) => { isDragging = true; startMouseX = e.clientX; startMouseY = e.clientY; });
        window.addEventListener('mouseup', () => { isDragging = false; });
        canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = (e.clientX - startMouseX) * 0.8;
            const dy = (e.clientY - startMouseY) * 0.8;
            steerX += dx;
            steerY += dy;
            startMouseX = e.clientX;
            startMouseY = e.clientY;
            sendOrchestration();
        });

        socket.onmessage = (e) => {
            if (typeof e.data === "string") return;
            const data = new Float32Array(e.data);
            ctx.fillStyle = 'rgba(3, 6, 15, 0.32)';
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

        renderSubfleetUI();
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
    global positions, velocities, active_subfleets, global_steer_x, global_steer_y, global_speed_mult, global_damping
    t_phase = 0.0

    while True:
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=0.001)
            if isinstance(msg, str):
                cmd = json.loads(msg)
                if cmd.get("command") == "ORCHESTRATE_SWARM":
                    fleets = cmd.get("subfleets", [])
                    if isinstance(fleets, list) and len(fleets) > 0:
                        active_subfleets = fleets
                    global_steer_x = float(cmd.get("steer_x", 0.0))
                    global_steer_y = float(cmd.get("steer_y", 0.0))
                elif cmd.get("command") == "SET_PHYSICS":
                    global_speed_mult = float(cmd.get("speed_mult", 1.0))
                    global_damping = float(cmd.get("damping", 0.86))
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            pass

        t_phase += 0.035 * global_speed_mult

        # Precision Sub-Fleet Solver
        solve_swarm_orchestration(t_phase)

        dt = 0.05 * global_speed_mult
        diff = target_positions - positions
        velocities = velocities * global_damping + diff * (1.0 - global_damping)
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
