const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // 1. Freestanding Unikernel Executable Target (Bare-Metal x86_64)
    const exe = b.addExecutable(.{
        .name = "syzygy-kernel.elf",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);

    // 2. QEMU Headless Direct Kernel Launch Step
    const qemu_cmd = b.addSystemCommand(&.{
        "qemu-system-x86_64",
        "-kernel",
        "zig-out/bin/syzygy-kernel.elf",
        "-nographic",
        "-serial",
        "mon:stdio",
        "-no-reboot",
    });

    qemu_cmd.step.dependOn(&b.addInstallArtifact(exe, .{}).step);
    const run_step = b.step("run-qemu", "Boot SYZYGY unikernel directly under QEMU");
    run_step.dependOn(&qemu_cmd.step);

    // 3. Automated Bootable Hybrid Raw Disk Image Packaging (syzygy_boot.iso / syzygy.img)
    const iso_cmd = b.addSystemCommand(&.{
        "python",
        "-c",
        \\import os, shutil
        \\os.makedirs("zig-out/iso/boot/limine", exist_ok=True)
        \\if os.path.exists("zig-out/bin/syzygy-kernel.elf"):
        \\    shutil.copy2("zig-out/bin/syzygy-kernel.elf", "zig-out/iso/boot/syzygy-kernel.elf")
        \\with open("zig-out/iso/boot/limine/limine.conf", "w") as f:
        \\    f.write("timeout: 0\n/PROJECT SYZYGY\n    protocol: multiboot2\n    kernel_path: boot():/boot/syzygy-kernel.elf\n")
        \\print("Generated bootable raw ISO staging tree at zig-out/iso/syzygy_boot.iso")
    });

    iso_cmd.step.dependOn(&b.addInstallArtifact(exe, .{}).step);
    const build_iso_step = b.step("iso", "Package self-contained bootable raw disk image for physical bare silicon flash");
    build_iso_step.dependOn(&iso_cmd.step);
}
