.syntax unified
.cpu cortex-m4
.thumb

.section .text.usbkiss,"ax",%progbits
.global usb_kiss_rx_byte
.type usb_kiss_rx_byte,%function
.thumb_func
usb_kiss_rx_byte:
    push    {r3-r7, lr}
    mov     r4, r0
    ldr     r5, =0x2000AE24
    ldrb    r1, [r5, #0x27]
    cmp     r1, #2
    beq     .Lkiss
    mov     r0, r4
    pop     {r3-r7, lr}
    ldr     r3, =0x0800C4ED
    bx      r3

.Lkiss:
    ldr     r6, =0x2000B22C
    ldrb    r0, [r6, #0x0C]
    cmp     r0, #5
    bhs     .Lret
    cmp     r0, #0
    beq     .Lidle
    cmp     r0, #1
    beq     .Lcommand
    cmp     r0, #2
    beq     .Lpayload_state
    cmp     r0, #3
    beq     .Lescape_state
    b       .Ldrop_state

.Lidle:
    cmp     r4, #0xC0
    bne     .Lret
    b       .Larm

.Lcommand:
    cmp     r4, #0xC0
    beq     .Larm
    cmp     r4, #0x00
    bne     .Lset_drop
    movs    r0, #2
    strb    r0, [r6, #0x0C]
    b       .Lret

.Lpayload_state:
    cmp     r4, #0xC0
    beq     .Lfinalize
    cmp     r4, #0xDB
    beq     .Lset_escape
    b       .Lappend

.Lescape_state:
    cmp     r4, #0xC0
    beq     .Larm
    cmp     r4, #0xDC
    beq     .Lesccaped_c0
    cmp     r4, #0xDD
    beq     .Lesccaped_db
    b       .Lset_drop

.Lesccaped_c0:
    movs    r4, #0xC0
    b       .Lappend

.Lesccaped_db:
    movs    r4, #0xDB
    b       .Lappend

.Lappend:
    ldrb    r7, [r6, #0x0D]
    cmp     r7, #182
    bhs     .Lset_drop
    sub.w   r0, r6, #0xE4
    adds    r0, #4
    strb    r4, [r0, r7]
    add     r1, r6, #0x0E
    mov     r0, r4
    ldr     r3, =0x080094C9
    blx     r3
    adds    r7, r7, #1
    strb    r7, [r6, #0x0D]
    movs    r0, #2
    strb    r0, [r6, #0x0C]
    b       .Lret

.Lset_escape:
    movs    r0, #3
    strb    r0, [r6, #0x0C]
    b       .Lret

.Ldrop_state:
    cmp     r4, #0xC0
    beq     .Larm
    b       .Lret

.Lset_drop:
    movs    r0, #4
    strb    r0, [r6, #0x0C]
    b       .Lret

.Lfinalize:
    ldrb    r7, [r6, #0x0D]
    cmp     r7, #16
    blo     .Larm
    sub.w   r1, r6, #0xE4
    adds    r1, #4
    ldrb    r0, [r1, #6]
    lsls    r0, r0, #31
    bmi     .Larm
    movs    r2, #13
.Laddr_scan:
    cmp     r7, r2
    bls     .Larm
    ldrb    r0, [r1, r2]
    lsls    r0, r0, #31
    bmi     .Laddr_found
    adds    r2, r2, #7
    cmp     r2, #55
    bls     .Laddr_scan
    b       .Larm

.Laddr_found:
    adds    r0, r2, #3
    cmp     r7, r0
    blo     .Larm
    subs    r3, r7, r0
    cmp     r3, #127
    bhi     .Larm
    ldr     r0, [r6, #0x08]
    cmp     r0, #0
    bne     .Lclear_state
    ldrh    r0, [r6, #0x0E]
    mvns    r0, r0
    uxth    r0, r0
    sub.w   r1, r6, #0xE4
    adds    r1, #4
    add     r1, r1, r7
    strb    r0, [r1]
    lsrs    r0, r0, #8
    strb    r0, [r1, #1]
    movs    r0, #5
    strb    r0, [r6, #0x0C]
    b       .Lret

.Lclear_state:
    movs    r0, #0
    strb    r0, [r6, #0x0C]
    strb    r0, [r6, #0x0D]
    strh    r0, [r6, #0x0E]
    b       .Lret

.Larm:
    ldr     r0, [r6, #0x08]
    cmp     r0, #0
    bne     .Lbusy_drop
    movs    r0, #1
    strb    r0, [r6, #0x0C]
    movs    r0, #0
    strb    r0, [r6, #0x0D]
    movw    r0, #0xFFFF
    strh    r0, [r6, #0x0E]
    ldr     r1, =0x31585452
    sub.w   r0, r6, #0xE4
    str     r1, [r0]
    b       .Lret

.Lbusy_drop:
    movs    r0, #4
    strb    r0, [r6, #0x0C]

.Lret:
    pop     {r3-r7, pc}
.size usb_kiss_rx_byte, .-usb_kiss_rx_byte

.global usb_kiss_dispatch_gate
.type usb_kiss_dispatch_gate,%function
.thumb_func
usb_kiss_dispatch_gate:
    push    {r3-r5, lr}
    ldr     r5, =0x2000B22C
    ldrb    r1, [r5, #0x0C]
    cmp     r1, #5
    beq     .Ldispatch_usb
    cmp     r1, #1
    beq     .Ldispatch_ret
    cmp     r1, #2
    beq     .Ldispatch_ret
    cmp     r1, #3
    beq     .Ldispatch_ret
    cmp     r1, #6
    beq     .Ldispatch_ret
    ldr     r1, [r5, #0x08]
    cmp     r1, #1
    bne     .Ldispatch_ret
    movs    r1, #6
    strb    r1, [r5, #0x0C]
    ldr     r4, [r5, #0x00]
    mov     r2, r4
    add     r1, r5, #0x10
    sub.w   r0, r5, #0xE4
    ldr     r3, =0x08003B6F
    blx     r3
    ldr     r3, =0x0800CD35
    blx     r3
    mov     r0, r4
    sub.w   r1, r5, #0xE4
    ldr     r3, =0x0800BE85
    blx     r3
    b       .Ldispatch_clear

.Ldispatch_usb:
    movs    r1, #6
    strb    r1, [r5, #0x0C]
    ldrb    r4, [r5, #0x0D]
    adds    r0, r4, #6
    sub.w   r1, r5, #0xE4
    ldr     r3, =0x0800BE85
    blx     r3

.Ldispatch_clear:
    movs    r0, #0
    strb    r0, [r5, #0x0C]
    strb    r0, [r5, #0x0D]
    strh    r0, [r5, #0x0E]

.Ldispatch_ret:
    pop     {r3-r5, pc}
.size usb_kiss_dispatch_gate, .-usb_kiss_dispatch_gate
