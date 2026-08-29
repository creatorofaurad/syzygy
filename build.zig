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

    // 2. Headless QEMU Runner Target (zig build run-qemu)
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());

    const run_step = b.step("run-qemu", "Boot SYZYGY unikernel directly under QEMU");
    run_step.dependOn(&run_cmd.step);

    // 3. Automated Bootable Hybrid ISO Generator (zig build iso)
    const iso_builder = b.addExecutable(.{
        .name = "make_iso",
        .root_module = b.createModule(.{
            .root_source_file = b.path("scripts/make_iso.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });

    const run_iso = b.addRunArtifact(iso_builder);
    run_iso.step.dependOn(b.getInstallStep());

    const iso_step = b.step("iso", "Package bootable hybrid UEFI/BIOS syzygy_boot.iso for USB flashing");
    iso_step.dependOn(&run_iso.step);
}
