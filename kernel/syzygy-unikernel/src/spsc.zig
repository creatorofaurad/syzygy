// ============================================================================
// PROJECT SYZYGY: Sovereign Lock-Free SPSC Ring Buffer Monolith
// Target: x86_64-freestanding-none (64-Byte Cache-Line Aligned / Zero False Sharing)
// ============================================================================

const std = @import("std");

pub fn SpscQueue(comptime T: type, comptime Capacity: usize) type {
    return struct {
        const Self = @This();
        const CacheLine = 64;

        // Force tail, head, and data buffer onto separate 64-byte cache lines
        // to eliminate cross-core cache bounce and L1 invalidation storms.
        head: usize align(CacheLine) = 0,
        tail: usize align(CacheLine) = 0,
        buffer: [Capacity]T align(CacheLine) = undefined,

        pub fn push(self: *Self, item: T) bool {
            const current_tail = @atomicLoad(usize, &self.tail, .monotonic);
            const current_head = @atomicLoad(usize, &self.head, .acquire);

            if ((current_tail + 1) % Capacity == current_head) {
                return false; // Queue full
            }

            self.buffer[current_tail] = item;
            @atomicStore(usize, &self.tail, (current_tail + 1) % Capacity, .release);
            return true;
        }

        pub fn pop(self: *Self) ?T {
            const current_head = @atomicLoad(usize, &self.head, .monotonic);
            const current_tail = @atomicLoad(usize, &self.tail, .acquire);

            if (current_head == current_tail) {
                return null; // Queue empty
            }

            const item = self.buffer[current_head];
            @atomicStore(usize, &self.head, (current_head + 1) % Capacity, .release);
            return item;
        }
    };
}
