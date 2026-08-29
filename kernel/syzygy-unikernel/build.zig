const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // 1. Freestanding Unikernel Executable Target (Bare-Metal x86_64)
    const elf = b.addExecutable(.{
        .name = "syzygy_unikernel.elf",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Add Assembly Bootloader
    elf.addAssemblyFile(b.path("../../arch/x86_64/boot.s"));
    b.installArtifact(elf);

    // 2. Enterprise C-ABI Static Library (libsyzygy.a)
    const lib = b.addStaticLibrary(.{
        .name = "syzygy",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(lib);

    // 3. Headless QEMU Runner Step
    const qemu_cmd = b.addSystemCommand(&[_][]const u8{
        "qemu-system-x86_64",
        "-kernel",
        "zig-out/bin/syzygy_unikernel.elf",
        "-display",
        "none",
        "-serial",
        "stdio",
        "-no-reboot",
    });
    qemu_cmd.step.dependOn(&b.addInstallArtifact(elf, .{}).step);

    const run_qemu = b.step("run-qemu", "Execute the kernel inside headless QEMU");
    run_qemu.dependOn(&qemu_cmd.step);
}
