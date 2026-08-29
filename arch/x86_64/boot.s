/*
 * PROJECT SYZYGY: Sovereign Bare-Metal x86_64 Boot & Long Mode Initialization
 * Target: x86_64-freestanding-none (UEFI / Bare-Metal Hardware)
 *
 * Execution Invariants:
 * 1. Transition 32-bit Compatibility Mode -> 64-bit Long Mode (CR0.PG, CR4.PAE, EFER.LME).
 * 2. Identity-map first 4GB with 1GB / 2MB Huge Pages in PML4 (zero TLB shootdowns).
 * 3. Mask legacy 8259 PIC vectors to avoid timer contention.
 * 4. Program Local APIC (x2APIC/xAPIC) for deterministic TSC calibrated one-shot timers.
 * 5. Low-overhead MMIO UART 16550 Serial logging on COM1 (0x3F8) & VGA buffer (0xB8000).
 */

.section .boot_header, "a"
.align 8
.global _start
.global uefi_entry

.code32
_start:
    cli                         /* Disable maskable interrupts */
    cld

    /* 1. Mask Legacy 8259 PIC */
    movb $0xFF, %al
    outb %al, $0xA1             /* Mask Slave PIC */
    outb %al, $0x21             /* Mask Master PIC */

    /* 2. Setup Early Serial COM1 (16550 UART at 0x3F8) */
    movw $0x3F9, %dx            /* Disable interrupts */
    movb $0x00, %al
    outb %al, %dx

    movw $0x3FB, %dx            /* Enable DLAB (set baud rate divisor) */
    movb $0x80, %al
    outb %al, %dx

    movw $0x3F8, %dx            /* Set divisor to 1 (115200 baud) */
    movb $0x01, %al
    outb %al, %dx
    movw $0x3F9, %dx
    movb $0x00, %al
    outb %al, %dx

    movw $0x3FB, %dx            /* 8 bits, no parity, one stop bit */
    movb $0x03, %al
    outb %al, %dx

    /* Write Early Boot Banner to Serial Port */
    movw $0x3F8, %dx
    movb $'S', %al; outb %al, %dx
    movb $'Y', %al; outb %al, %dx
    movb $'Z', %al; outb %al, %dx
    movb $'Y', %al; outb %al, %dx
    movb $'G', %al; outb %al, %dx
    movb $'Y', %al; outb %al, %dx
    movb $'\n', %al; outb %al, %dx

    /* 3. Setup Identity-Mapped 4-Level PML4 Huge Pages */
    /* Point CR3 to PML4 Table Base */
    movl $pml4_table, %eax
    movl %eax, %cr3

    /* 4. Enable PAE (Physical Address Extension) in CR4 */
    movl %cr4, %eax
    orl $(1 << 5), %eax         /* CR4.PAE = bit 5 */
    orl $(1 << 7), %eax         /* CR4.PGE = bit 7 (Page Global Enable) */
    movl %eax, %cr4

    /* 5. Set Long Mode Enable (LME) in EFER MSR (0xC0000080) */
    movl $0xC0000080, %ecx
    rdmsr
    orl $(1 << 8), %eax         /* EFER.LME = bit 8 */
    wrmsr

    /* 6. Enable Paging & Protected Mode in CR0 */
    movl %cr0, %eax
    orl $(1 << 31 | 1 << 0), %eax /* CR0.PG = bit 31, CR0.PE = bit 0 */
    movl %eax, %cr0

    /* 7. Load 64-bit Global Descriptor Table (GDT) */
    lgdt (gdt64_ptr)

    /* Far jump to 64-bit Long Mode Kernel Entry */
    ljmp $0x08, $long_mode_entry

/* ========================================================================= */
/* 64-BIT LONG MODE EXECUTION SPACE                                          */
/* ========================================================================= */
.code64
long_mode_entry:
    /* Reload segment registers with 64-bit null/data selector */
    movw $0x10, %ax
    movw %ax, %ds
    movw %ax, %es
    movw %ax, %fs
    movw %ax, %gs
    movw %ax, %ss

    /* Setup 64-byte aligned Freestanding Stack */
    movabsq $stack_top, %rsp
    andq $-64, %rsp             /* Strict 64-byte L1 cache line alignment */

    /* Call the Zig Freestanding Monolith Entrypoint */
    callq syzygy_kernel_main

    /* Halt CPU if kernel returns */
hang:
    cli
    hlt
    jmp hang

/* ========================================================================= */
/* PAGE TABLES & GDT DATA STRUCTURES                                         */
/* ========================================================================= */
.section .bss
.align 4096
pml4_table:
    .quad pdpt_table + 0x03     /* Present + Writable */
    .fill 511, 8, 0

pdpt_table:
    /* Identity-map 4 x 1GB Huge Pages (0x83 = Present + Writable + PageSize 1GB) */
    .quad 0x00000000 + 0x83
    .quad 0x40000000 + 0x83
    .quad 0x80000000 + 0x83
    .quad 0xC0000000 + 0x83
    .fill 508, 8, 0

.align 64
stack_bottom:
    .fill 65536, 1, 0           /* 64 KB Initial Kernel Stack */
stack_top:

.section .data
.align 16
gdt64:
    .quad 0x0000000000000000    /* Null Descriptor */
    .quad 0x00AF9A000000FFFF    /* 64-bit Code Segment (Kernel Execution) */
    .quad 0x00CF92000000FFFF    /* 64-bit Data Segment */
gdt64_ptr:
    .word . - gdt64 - 1
    .quad gdt64
