// ============================================================================
// PROJECT SYZYGY: Sovereign Direct Memory-Mapped Huge Page Bump Arena
// Target: x86_64-freestanding-none (Zero-Fragmentation / Zero TLB Shootdowns)
// ============================================================================

const std = @import("std");

pub const HugePageArena = struct {
    // Invariants: 1GB Huge Page Backing (Base Address: 0x40000000 / 1GB Boundary)
    pub const PAGE_SIZE_1GB: usize = 1024 * 1024 * 1024;
    pub const PAGE_SIZE_2MB: usize = 2 * 1024 * 1024;
    pub const CACHE_LINE: usize = 64;

    base_ptr: [*]u8,
    capacity: usize,
    offset: usize align(CACHE_LINE) = 0,

    pub fn init(base_address: usize, size: usize) HugePageArena {
        return HugePageArena{
            .base_ptr = @as([*]u8, @ptrFromInt(base_address)),
            .capacity = size,
            .offset = 0,
        };
    }

    // Zero-overhead bump allocation with strict 64-byte L1 cache alignment
    pub fn alloc(self: *HugePageArena, comptime T: type, count: usize) ?[]T {
        const byte_size = @sizeOf(T) * count;
        const aligned_size = (byte_size + (CACHE_LINE - 1)) & ~(CACHE_LINE - 1);

        const current_offset = @atomicLoad(usize, &self.offset, .monotonic);
        if (current_offset + aligned_size > self.capacity) {
            return null; // Arena Out of Memory
        }

        const new_offset = current_offset + aligned_size;
        @atomicStore(usize, &self.offset, new_offset, .release);

        const ptr = @as([*]T, @ptrCast(@alignCast(self.base_ptr + current_offset)));
        return ptr[0..count];
    }

    // Reset arena without deallocating pages (instant O(1) frame clearance)
    pub fn reset(self: *HugePageArena) void {
        @atomicStore(usize, &self.offset, 0, .release);
    }

    // Query allocated bytes
    pub fn getAllocatedBytes(self: *const HugePageArena) usize {
        return @atomicLoad(usize, &self.offset, .monotonic);
    }
};
