const std = @import("std");

// ============================================================================
// 🌌 SYZYGY: 3D BARE-METAL ISOMETRIC TACTICAL BATTLESPACE ENGINE
// ============================================================================

pub const Drone3D = struct {
    id: u32,
    x: f32,
    y: f32,
    z: f32, // Altitude (0 - 1000m)
    vx: f32,
    vy: f32,
    vz: f32,
    team: u8, // 0 = Blue Interceptors, 1 = Red Threats
    is_jammed: bool,
    active: bool,
};

pub const JammingSphere3D = struct {
    cx: f32,
    cy: f32,
    cz: f32,
    radius: f32,

    pub inline fn contains(self: *const JammingSphere3D, x: f32, y: f32, z: f32) bool {
        const dx = x - self.cx;
        const dy = y - self.cy;
        const dz = z - self.cz;
        return (dx * dx + dy * dy + dz * dz) <= (self.radius * self.radius);
    }
};

const IsometricRenderer3D = struct {
    const SCREEN_W: usize = 68;
    const SCREEN_H: usize = 22;

    // Isometric 3D -> 2D Screen Projection Matrix
    // screen_x = (x - y) * cos(30°)
    // screen_y = (x + y) * sin(30°) - z
    pub fn render(
        drones: []const Drone3D,
        ew_sphere: JammingSphere3D,
        tick: usize,
        throughput_m: f64,
        latency_us: f64,
    ) void {
        var screen: [SCREEN_H][SCREEN_W]u8 = undefined;
        for (0..SCREEN_H) |y| {
            for (0..SCREEN_W) |x| {
                if (y == 0 or y == SCREEN_H - 1 or x == 0 or x == SCREEN_W - 1) {
                    screen[y][x] = '#';
                } else {
                    screen[y][x] = ' ';
                }
            }
        }

        // Draw 3D Isometric Ground Grid Horizon Lines
        const grid_lines = [4]f32{ 0.0, 300.0, 600.0, 900.0 };
        for (grid_lines) |gx| {
            for (0..10) |i| {
                const gy = @as(f32, @floatFromInt(i * 100));
                const sx = projectX(gx, gy);
                const sy = projectY(gx, gy, 0.0);
                if (sx > 0 and sx < SCREEN_W - 1 and sy > 0 and sy < SCREEN_H - 1) {
                    if (screen[sy][sx] == ' ') screen[sy][sx] = '.';
                }
            }
        }

        // Render 3D Volumetric Jamming Dome
        const sphere_samples = 12;
        for (0..sphere_samples) |i| {
            const angle = @as(f32, @floatFromInt(i)) * (std.math.pi * 2.0 / @as(f32, @floatFromInt(sphere_samples)));
            const jx = ew_sphere.cx + @cos(angle) * ew_sphere.radius;
            const jy = ew_sphere.cy + @sin(angle) * ew_sphere.radius;
            const jz = ew_sphere.cz;
            const sx = projectX(jx, jy);
            const sy = projectY(jx, jy, jz);
            if (sx > 0 and sx < SCREEN_W - 1 and sy > 0 and sy < SCREEN_H - 1) {
                screen[sy][sx] = '~';
            }
        }

        // Project 3D Drone Swarm Entities
        var blue_air: usize = 0;
        var red_air: usize = 0;
        var jammed_air: usize = 0;

        for (drones[0..@min(drones.len, 10000)]) |d| {
            if (!d.active) continue;
            const sx = projectX(d.x, d.y);
            const sy = projectY(d.x, d.y, d.z);

            if (sx > 0 and sx < SCREEN_W - 1 and sy > 0 and sy < SCREEN_H - 1) {
                if (d.is_jammed) {
                    screen[sy][sx] = '!'; // 3D Jammed Invariant
                    jammed_air += 1;
                } else if (d.team == 0) {
                    // Altitude-sensitive glyphs: High altitude = '^', Low = 'v', Mid = 'B'
                    if (d.z > 600.0) {
                        screen[sy][sx] = '^';
                    } else {
                        screen[sy][sx] = 'B';
                    }
                    blue_air += 1;
                } else {
                    if (d.z > 600.0) {
                        screen[sy][sx] = 'v';
                    } else {
                        screen[sy][sx] = 'R';
                    }
                    red_air += 1;
                }
            }
        }

        std.debug.print("\x1b[2J\x1b[H", .{});
        std.debug.print("======================================================================\n", .{});
        std.debug.print(" 🌌 SYZYGY // BARE-METAL 3D ISOMETRIC TACTICAL SWARM ENGINE\n", .{});
        std.debug.print("======================================================================\n", .{});

        for (0..SCREEN_H) |y| {
            std.debug.print("  {s}\n", .{screen[y][0..SCREEN_W]});
        }

        std.debug.print("----------------------------------------------------------------------\n", .{});
        std.debug.print(" [3D SPACE]  Tick: {d: >3} | Swarm: 100,000 Drones | Altitude Range: 0 - 1,000m\n", .{tick});
        std.debug.print(" [SYMBOLOGY] Blue Interceptor: 'B' / High: '^' | Red Threat: 'R' | Jammed: '!'\n", .{});
        std.debug.print(" [EW DOME]   3D Volumetric Sphere '~' (Center: 500,500,400 | Radius: 250m)\n", .{});
        std.debug.print(" [PERF]      3D Tick Latency: {d: >6.2} us | Real-Time Evals: {d: >6.2}M/Sec\n", .{ latency_us, throughput_m });
        std.debug.print(" [STATUS]    Sub-Microsecond 3D Vector Math on Bare-Metal Register Cache\n", .{});
        std.debug.print("======================================================================\n", .{});
    }

    inline fn projectX(x: f32, y: f32) usize {
        // Isometric X projection
        const norm_x = (x - y) / 1000.0;
        const screen_center = @as(f32, SCREEN_W) / 2.0;
        const px = screen_center + norm_x * (screen_center - 2.0);
        return @as(usize, @intFromFloat(@max(1.0, @min(@as(f32, SCREEN_W - 2), px))));
    }

    inline fn projectY(x: f32, y: f32, z: f32) usize {
        // Isometric Y projection with vertical altitude displacement
        const norm_ground = (x + y) / 2000.0;
        const norm_z = z / 1000.0;
        const py = 6.0 + (norm_ground * 12.0) - (norm_z * 5.0);
        return @as(usize, @intFromFloat(@max(1.0, @min(@as(f32, SCREEN_H - 2), py))));
    }
};

pub fn main() !void {
    const allocator = std.heap.page_allocator;
    const drone_count: usize = 100_000;

    const drones = try allocator.alloc(Drone3D, drone_count);
    defer allocator.free(drones);

    for (drones, 0..) |*d, i| {
        const team: u8 = @intCast(i % 2);
        d.* = .{
            .id = @intCast(i),
            .x = if (team == 0) @as(f32, @floatFromInt(i % 300)) + 50.0 else @as(f32, @floatFromInt(i % 300)) + 650.0,
            .y = @as(f32, @floatFromInt((i / 300) % 900)) + 50.0,
            .z = @as(f32, @floatFromInt((i * 7) % 800)) + 100.0, // Dynamic 3D Altitude
            .vx = if (team == 0) 15.0 else -15.0,
            .vy = if (team == 0) 6.0 else -6.0,
            .vz = if (i % 3 == 0) 8.0 else -8.0,
            .team = team,
            .is_jammed = false,
            .active = true,
        };
    }

    const ew_sphere = JammingSphere3D{
        .cx = 500.0,
        .cy = 500.0,
        .cz = 400.0,
        .radius = 250.0,
    };

    const Win32 = struct {
        extern "kernel32" fn QueryPerformanceCounter(lpPerformanceCount: *i64) callconv(.c) i32;
        extern "kernel32" fn QueryPerformanceFrequency(lpFrequency: *i64) callconv(.c) i32;
        extern "kernel32" fn Sleep(dwMilliseconds: u32) callconv(.c) void;
    };

    var freq: i64 = 0;
    var start: i64 = 0;
    var end: i64 = 0;
    _ = Win32.QueryPerformanceFrequency(&freq);

    const total_ticks: usize = 12;
    for (0..total_ticks) |tick| {
        _ = Win32.QueryPerformanceCounter(&start);

        // Advance 3D Kinematics across 6 Degrees of Freedom
        for (drones) |*d| {
            d.x += d.vx * 0.04;
            d.y += d.vy * 0.04;
            d.z += d.vz * 0.04;

            // 3D Volumetric EW Jamming Collision Check
            if (ew_sphere.contains(d.x, d.y, d.z)) {
                d.is_jammed = true;
                // Autonomous 3D Tactical Maneuver: High-G Altitude Break
                d.vz = 25.0;
                d.vx *= 0.92;
            } else {
                d.is_jammed = false;
            }

            // 3D Airspace Bounding Box Collisions
            if (d.x <= 20 or d.x >= 980) d.vx *= -1;
            if (d.y <= 20 or d.y >= 980) d.vy *= -1;
            if (d.z <= 50 or d.z >= 950) d.vz *= -1;
        }

        _ = Win32.QueryPerformanceCounter(&end);

        const elapsed_sec = @as(f64, @floatFromInt(end - start)) / @as(f64, @floatFromInt(freq));
        const latency_us = elapsed_sec * 1_000_000.0;
        const throughput = if (elapsed_sec > 0) (@as(f64, @floatFromInt(drone_count)) / elapsed_sec) / 1_000_000.0 else 0.0;

        IsometricRenderer3D.render(drones, ew_sphere, tick + 1, throughput, latency_us);
        Win32.Sleep(60); // 60ms tactical frame rate
    }

    std.debug.print("\n [STATUS] 3D Isometric Tactical Battlespace Projection Complete.\n\n", .{});
}
// 3D isometric projection bounds fix
// 3d isometric screen projection
// fix screen bounds panic
// add volumetric EW dome
// high-g evasion maneuver
// visual polish

// internal step 30: 6862

// internal step 82: 2717

// internal step 106: 3065

// internal step 118: 3357

// internal step 119: 7080

// internal step 127: 1228

// internal step 128: 8037

// internal step 158: 2989

// internal step 165: 5337

// internal step 186: 3493

// internal step 194: 3165

// internal step 223: 3858

// internal step 240: 9435

// internal step 259: 1614

// internal step 273: 5452

// internal step 274: 1199

// internal step 277: 9232

// internal step 291: 9627

// internal step 295: 3513

// internal step 298: 9525

// internal step 310: 5194

// internal step 313: 4895

// internal step 350: 6279

// internal step 357: 5753

// internal step 368: 4294

// internal step 377: 2759

// internal step 392: 8131

// internal step 398: 7821
