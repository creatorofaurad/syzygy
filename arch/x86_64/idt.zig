// ============================================================================
// PROJECT SYZYGY: Freestanding 64-Bit Interrupt Descriptor Table (IDT) & ISRs
// Target: x86_64-freestanding-none (Triple-Fault Prevention & Fault Telemetry)
// ============================================================================

const std = @import("std");

// MMIO Serial UART logging primitives
const COM1_PORT: u16 = 0x3F8;

inline fn outb(port: u16, val: u8) void {
    asm volatile (
        "outb %[val], %[port]"
        :
        : [val] "{al}" (val),
          [port] "{dx}" (port),
    );
}

fn serialPrint(msg: []const u8) void {
    for (msg) |c| {
        if (c == '\n') outb(COM1_PORT, '\r');
        outb(COM1_PORT, c);
    }
}

// 64-bit IDT Entry Structure (16 bytes per gate descriptor)
pub const IdtEntry = extern struct {
    offset_low: u16,
    selector: u16,
    ist: u8,
    type_attr: u8,
    offset_mid: u16,
    offset_high: u32,
    reserved: u32 = 0,

    pub fn init(handler: *const fn () callconv(.naked) void, is_trap: bool) IdtEntry {
        const addr = @intFromPtr(handler);
        return IdtEntry{
            .offset_low = @as(u16, @truncate(addr)),
            .selector = 0x08, // Kernel 64-bit Code Segment
            .ist = 0,
            .type_attr = if (is_trap) 0x8F else 0x8E, // 0x8E = 64-bit Interrupt Gate, Present
            .offset_mid = @as(u16, @truncate(addr >> 16)),
            .offset_high = @as(u32, @truncate(addr >> 32)),
            .reserved = 0,
        };
    }
};

// IDTR Structure loaded via lidt instruction
pub const IdtPointer = extern struct {
    limit: u16,
    base: u64,
};

// 256 Entry Static IDT Arena
var idt: [256]IdtEntry align(16) = undefined;
var idtr: IdtPointer = undefined;

// ============================================================================
// HARDWARE EXCEPTION INTERRUPT SERVICE ROUTINES (ISRs)
// ============================================================================

// Vector 8: Double Fault (#DF)
pub fn isr_double_fault() callconv(.naked) void {
    asm volatile (
        \\ cli
        \\ pushq %rax
        \\ pushq %rcx
        \\ pushq %rdx
    );
    serialPrint("\n[CRITICAL HARDWARE TRAP] Exception #DF (Double Fault, Vector 8) Triggered!\n");
    serialPrint("[PANIC] Halting Substrate to prevent CPU Triple-Fault reset.\n");
    while (true) {
        asm volatile ("cli; hlt");
    }
}

// Vector 13: General Protection Fault (#GP)
pub fn isr_general_protection() callconv(.naked) void {
    asm volatile (
        \\ cli
        \\ pushq %rax
        \\ pushq %rcx
        \\ pushq %rdx
    );
    serialPrint("\n[CRITICAL HARDWARE TRAP] Exception #GP (General Protection Fault, Vector 13) Triggered!\n");
    serialPrint("[PANIC] Memory segment violation or privileged instruction trap.\n");
    while (true) {
        asm volatile ("cli; hlt");
    }
}

// Vector 14: Page Fault (#PF)
pub fn isr_page_fault() callconv(.naked) void {
    asm volatile (
        \\ cli
        \\ pushq %rax
        \\ pushq %rcx
        \\ pushq %rdx
    );
    // Read faulting linear address from CR2
    const cr2 = asm volatile (
        "mov %%cr2, %[ret]"
        : [ret] "=r" (-> u64),
    );
    _ = cr2;
    serialPrint("\n[CRITICAL HARDWARE TRAP] Exception #PF (Page Fault, Vector 14) Triggered!\n");
    serialPrint("[PANIC] Identity-mapped huge page boundary violation.\n");
    while (true) {
        asm volatile ("cli; hlt");
    }
}

// Initialize and load the IDT into the CPU
pub fn initIDT() void {
    // Fill all gates with default handler
    var i: usize = 0;
    while (i < 256) : (i += 1) {
        idt[i] = IdtEntry.init(isr_general_protection, false);
    }

    // Install Specific Hardware Exception Handlers
    idt[8] = IdtEntry.init(isr_double_fault, false);      // #DF (Double Fault)
    idt[13] = IdtEntry.init(isr_general_protection, false); // #GP (General Protection)
    idt[14] = IdtEntry.init(isr_page_fault, false);       // #PF (Page Fault)

    // Load IDTR
    idtr = IdtPointer{
        .limit = @as(u16, @sizeOf(@TypeOf(idt)) - 1),
        .base = @intFromPtr(&idt),
    };

    asm volatile (
        "lidt (%[ptr])"
        :
        : [ptr] "r" (&idtr),
    );

    serialPrint("[SYZYGY-IDT] 64-Bit Interrupt Descriptor Table Initialized (256 Gates Loaded).\n");
}
