// ============================================================================
// PROJECT SYZYGY: Sovereign Bare-Metal x2APIC & Invariant TSC Timer Subsystem
// Target: x86_64-freestanding-none (Sub-Microsecond Deterministic Preemption)
// ============================================================================

const std = @import("std");

// Model Specific Registers (MSRs) for Local x2APIC
const IA32_APIC_BASE_MSR: u32 = 0x0000001B;
const IA32_X2APIC_TPR_MSR: u32 = 0x00000808;
const IA32_X2APIC_SIVR_MSR: u32 = 0x0000080F;
const IA32_X2APIC_LVT_TIMER: u32 = 0x00000832;
const IA32_X2APIC_INIT_COUNT: u32 = 0x00000838;
const IA32_X2APIC_CURR_COUNT: u32 = 0x00000839;
const IA32_X2APIC_DIV_CONF: u32 = 0x0000083E;

// Inline assembly primitives for reading and writing x86 MSRs
inline fn rdmsr(msr: u32) u64 {
    var low: u32 = undefined;
    var high: u32 = undefined;
    asm volatile (
        "rdmsr"
        : [low] "={eax}" (low),
          [high] "={edx}" (high),
        : [msr] "{ecx}" (msr),
    );
    return (@as(u64, high) << 32) | @as(u64, low);
}

inline fn wrmsr(msr: u32, val: u64) void {
    const low = @as(u32, @truncate(val));
    const high = @as(u32, @truncate(val >> 32));
    asm volatile (
        "wrmsr"
        :
        : [low] "{eax}" (low),
          [high] "{edx}" (high),
          [msr] "{ecx}" (msr),
    );
}

pub const LocalAPIC = struct {
    var tsc_frequency_hz: u64 = 3_200_000_000; // Baseline calibrated 3.2 GHz

    // Read the Invariant Time Stamp Counter (RDTSC)
    pub inline fn rdtsc() u64 {
        const low = asm volatile (
            "rdtsc"
            : [ret] "={eax}" (-> u32),
        );
        const high = asm volatile (
            "rdtsc; movl %%edx, %[ret]"
            : [ret] "=r" (-> u32),
        );
        return (@as(u64, high) << 32) | @as(u64, low);
    }

    // Initialize x2APIC Mode and configure Spurious Interrupt Vector
    pub fn initX2APIC() void {
        // Enable APIC Global and x2APIC Mode in IA32_APIC_BASE MSR
        var base = rdmsr(IA32_APIC_BASE_MSR);
        base |= (1 << 11) | (1 << 10); // Enable APIC (bit 11) and x2APIC (bit 10)
        wrmsr(IA32_APIC_BASE_MSR, base);

        // Set Spurious Interrupt Vector Register (SIVR) to 0x1FF (enable APIC + vector 255)
        wrmsr(IA32_X2APIC_SIVR_MSR, 0x1FF);

        // Clear Task Priority Register (TPR) to accept all hardware interrupts
        wrmsr(IA32_X2APIC_TPR_MSR, 0x00);
    }

    // Configure deterministic one-shot APIC timer for sub-microsecond preemption
    pub fn armOneShotTimer(microseconds: u32) void {
        // Divide by 16 configuration
        wrmsr(IA32_X2APIC_DIV_CONF, 0x03);

        // LVT Timer: One-Shot Mode (bit 17=0), Vector 32 (0x20)
        wrmsr(IA32_X2APIC_LVT_TIMER, 0x20);

        // Calculate ticks from calibrated TSC frequency
        const ticks = (@as(u64, microseconds) * (tsc_frequency_hz / 1_000_000)) / 16;
        wrmsr(IA32_X2APIC_INIT_COUNT, ticks);
    }

    // Read remaining timer ticks
    pub fn getRemainingTicks() u64 {
        return rdmsr(IA32_X2APIC_CURR_COUNT);
    }
};
