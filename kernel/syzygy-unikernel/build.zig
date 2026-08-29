const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // 1. Freestanding Unikernel Executable Target
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
}
