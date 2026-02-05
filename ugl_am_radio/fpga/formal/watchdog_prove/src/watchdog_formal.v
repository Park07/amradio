`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Formal Verification Properties for Watchdog Timer
// ===================================================
//
// Timing model:
//   At step N, registers hold values from transition at step N-1.
//   $past(signal) gives the value at step N-1.
//   Input-dependent assertions must use $past(input) to check
//   the effect of that input on the CURRENT register state.
//
// Run with: sby -f watchdog.sby
//
//////////////////////////////////////////////////////////////////////////////////
module watchdog_timer #(
    parameter CLK_FREQ    = 10,   // Small for formal (real: 125_000_000)
    parameter TIMEOUT_SEC = 2     // Small for formal (real: 5)
)(
    input  wire        clk,
    input  wire        rstn,
    input  wire        heartbeat,
    input  wire        enable,
    input  wire        force_reset,
    output reg         triggered,
    output reg         warning,
    output wire [7:0]  time_remaining
);
    localparam TIMEOUT_CYCLES = CLK_FREQ * TIMEOUT_SEC;
    localparam WARNING_CYCLES = (CLK_FREQ * TIMEOUT_SEC * 8) / 10;
    localparam COUNTER_WIDTH  = 32;

    reg [COUNTER_WIDTH-1:0] counter;

    initial begin
        counter   = 0;
        triggered = 0;
        warning   = 0;
    end

    wire [31:0] remaining_cycles = (counter < TIMEOUT_CYCLES) ? (TIMEOUT_CYCLES - counter) : 0;
    wire [31:0] remaining_sec = remaining_cycles / CLK_FREQ;
    assign time_remaining = (remaining_sec > 255) ? 8'd255 : remaining_sec[7:0];

    always @(posedge clk) begin
        if (!rstn) begin
            counter   <= 0;
            triggered <= 0;
            warning   <= 0;
        end
        else if (!enable) begin
            counter   <= 0;
            triggered <= 0;
            warning   <= 0;
        end
        else if (heartbeat || force_reset) begin
            counter   <= 0;
            triggered <= 0;
            warning   <= 0;
        end
        else if (counter >= TIMEOUT_CYCLES) begin
            triggered <= 1;
            warning   <= 1;
        end
        else begin
            counter <= counter + 1;
            if (counter >= WARNING_CYCLES)
                warning <= 1;
            else
                warning <= 0;
        end
    end

`ifdef FORMAL

    // Force design through reset on first clock
    initial assume(rstn == 0);

    reg f_past_valid;
    initial f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;

    // ========================================================================
    // PROPERTY 1: Reset clears everything
    // If reset was active last cycle, registers are now 0
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && $past(!rstn)) begin
            assert(counter == 0);
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // ========================================================================
    // PROPERTY 2: Heartbeat prevents trigger
    // If heartbeat was received last cycle (with enable), counter is now 0
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && $past(rstn) && $past(enable) && $past(heartbeat)) begin
            assert(counter == 0);
            assert(triggered == 0);
        end
    end

    // ========================================================================
    // PROPERTY 3: Trigger ONLY happens after timeout (KEY SAFETY PROPERTY)
    // State invariant: both are registers checked at the same step
    // ========================================================================
    always @(posedge clk) begin
        if (counter < TIMEOUT_CYCLES)
            assert(triggered == 0);
    end

    // ========================================================================
    // PROPERTY 4: Trigger ALWAYS happens at timeout
    // If last cycle had counter >= TIMEOUT with no reset/heartbeat,
    // triggered must now be 1
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid
            && $past(rstn) && $past(enable)
            && !$past(heartbeat) && !$past(force_reset)
            && $past(counter) >= TIMEOUT_CYCLES)
            assert(triggered == 1);
    end

    // ========================================================================
    // PROPERTY 5: Warning comes before trigger (state invariant)
    // Whenever triggered is HIGH, warning must also be HIGH
    // ========================================================================
    always @(posedge clk) begin
        if (triggered)
            assert(warning == 1);
    end

    // ========================================================================
    // PROPERTY 6: Disable kills everything
    // If enable was LOW last cycle, registers are now 0
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && $past(!enable)) begin
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // ========================================================================
    // PROPERTY 7: Counter never exceeds timeout (state invariant)
    // ========================================================================
    always @(posedge clk) begin
        assert(counter <= TIMEOUT_CYCLES);
    end

    // ========================================================================
    // PROPERTY 8: Force reset clears trigger
    // If force_reset was active last cycle (with enable), triggered is now 0
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && $past(rstn) && $past(enable) && $past(force_reset))
            assert(triggered == 0);
    end

    // ========================================================================
    // PROPERTY 9: Warning timing correct (state invariant)
    // If counter hasn't reached warning threshold and not triggered,
    // warning must be LOW
    // ========================================================================
    always @(posedge clk) begin
        if (counter < WARNING_CYCLES && !triggered)
            assert(warning == 0);
    end

    // ========================================================================
    // COVER: Prove these scenarios are reachable
    // ========================================================================
    always @(posedge clk) cover(triggered == 1);
    always @(posedge clk) cover(warning == 1 && triggered == 0);
    always @(posedge clk) cover(counter == TIMEOUT_CYCLES - 1 && heartbeat);
    always @(posedge clk) cover(f_past_valid && $past(triggered) && !triggered);

`endif

endmodule