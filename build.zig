const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // 1. Freestanding Kernel Executable
    const exe = b.addExecutable(.{
        .name = "syzygy-kernel.elf",
        .root_module = b.createModule(.{
            .root_source_file = b.path("kernel/syzygy-unikernel/src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);

    // 2. Headless QEMU Runner Target
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());

    const run_step = b.step("run-qemu", "Boot SYZYGY unikernel directly under QEMU");
    run_step.dependOn(&run_cmd.step);
}
