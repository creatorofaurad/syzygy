# SYZYGY REAL-WORLD USE-CASE DEMO: 100K DEFENSE DRONE SWARM UNDER EW JAMMING
import subprocess
print("Launching 100,000 Drone Swarm Electronic Warfare Kinetic Intercept Demo...")
subprocess.run(["zig", "run", "../syzygy-3d-tactical/src/main.zig", "-O", "ReleaseFast"])
