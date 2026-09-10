.syntax unified
.thumb
.cpu cortex-m4

.section .entry_hook,"ax",%progbits
.global bt_entry_hook
.thumb_func
bt_entry_hook:
    b.w bt_dual_dispatch

.section .bt_dual,"ax",%progbits
.global bt_dual_dispatch
.thumb_func
bt_dual_dispatch:
    /* r0: BLE payload length
       r1: BLE payload pointer */

    /* Keep an active programming session on the OEM path. */
    ldr     r2, =0x2000AFC4
    ldrb    r3, [r2, #2]
    cbnz    r3, .Loem

    /* RTX1 packets use BLE KISS. */
    cmp     r0, #4
    blo     .Loem
    ldr     r2, [r1]
    ldr     r3, =0x31585452      /* "RTX1" */
    cmp     r2, r3
    bne     .Loem

.Lkiss:
    /* Original BLE KISS entry prologue. */
    push    {r4, r5, r6, lr}
    mov     r4, r0
    ldr     r3, =0x0800BE89
    bx      r3

.Loem:
    /* OEM Bluetooth programming receive path. */
    push    {r4, r5, r6, lr}
    mov     r4, r0
    cmp     r4, #0x40
    bls     1f
    movs    r4, #0x40
1:
    mov     r2, r4
    ldr     r0, =0x2000AFD4
    ldr     r3, =0x08003AE5
    blx     r3

    ldr     r5, =0x2000AFC4
    movw    r0, #0x07D0
    strh    r0, [r5, #6]
    strh    r4, [r5, #4]

    ldr     r3, =0x0800C3AD
    blx     r3
    cmp     r0, #1
    bne     .Loem_return

    lsls    r1, r0, #8
    ldr     r0, =0x40010800
    ldr     r3, =0x080156E7
    blx     r3

    ldr     r1, =0x2000A3FC
    movs    r0, #1
    strb.w  r0, [r1, #0x47]
    strb    r0, [r5, #2]

    pop     {r4, r5, r6, lr}
    ldr     r3, =0x0801C899
    bx      r3

.Loem_return:
    pop     {r4, r5, r6, pc}
