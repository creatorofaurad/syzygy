# ============================================================================
# PROJECT SYZYGY: Sovereign Bare-Metal Unikernel QEMU Sandbox
# One-Command Reproduction: docker run --rm ghcr.io/creatorofaurad/syzygy:latest
# ============================================================================

FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    xz-utils \
    build-essential \
    qemu-system-x86 \
    && rm -rf /var/lib/apt/lists/*

# Install Zig 0.13.0
RUN curl -LO https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz \
    && tar -xf zig-linux-x86_64-0.13.0.tar.xz \
    && mv zig-linux-x86_64-0.13.0 /usr/local/zig \
    && ln -s /usr/local/zig/zig /usr/local/bin/zig \
    && rm zig-linux-x86_64-0.13.0.tar.xz

WORKDIR /workspace
COPY . .

# Build Freestanding ELF Kernel
RUN cd kernel/syzygy-unikernel && zig build -Doptimize=ReleaseFast

# Runtime Sandbox Layer
FROM ubuntu:24.04 AS runner
RUN apt-get update && apt-get install -y qemu-system-x86 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /workspace/kernel/syzygy-unikernel/zig-out/bin/syzygy_unikernel.elf ./syzygy_kernel.elf

ENTRYPOINT ["qemu-system-x86_64", "-kernel", "syzygy_kernel.elf", "-display", "none", "-serial", "stdio", "-no-reboot"]
