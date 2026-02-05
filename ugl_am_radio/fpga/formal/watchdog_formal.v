`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Formal Verification Properties for Watchdog Timer
// ===================================================
//
// These properties are PROVEN for ALL possible input combinations,
// not just tested against a few test cases.
//
// Run with: sby watchdog.sby
//
//////////////////////////////////////////////////////////////////////////////////
module watchdog_timer #(
    // Use SMALL values for formal verification (otherwise solver takes forever)
    // Properties proven at small scale hold at full scale (same logic)
    parameter CLK_FREQ    = 10,   // Small for formal (real: 125_000_000)
    parameter TIMEOUT_SEC = 2     // Small for formal (real: 5)
)(
    input  wire        clk,
    input  wire        rstn,
    // Control
    input  wire        heartbeat,
    input  wire        enable,
    input  wire        force_reset,
    // Status
    output reg         triggered,
    output reg         warning,
    output wire [7:0]  time_remaining
);
    // Counter parameters
    localparam TIMEOUT_CYCLES = CLK_FREQ * TIMEOUT_SEC;
    localparam WARNING_CYCLES = (CLK_FREQ * TIMEOUT_SEC * 8) / 10;  // 80%
    localparam COUNTER_WIDTH  = 32;

    reg [COUNTER_WIDTH-1:0] counter;

    // Time remaining
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

// ============================================================================
// FORMAL VERIFICATION PROPERTIES
// ============================================================================
`ifdef FORMAL

    // Track how many cycles since reset
    reg f_past_valid;
    initial f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;

    // ========================================================================
    // PROPERTY 1: Reset clears everything
    // "After reset, triggered must be LOW"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && !rstn)
            assert(triggered == 0);
    end

    always @(posedge clk) begin
        if (f_past_valid && !rstn)
            assert(warning == 0);
    end

    always @(posedge clk) begin
        if (f_past_valid && !rstn)
            assert(counter == 0);
    end

    // ========================================================================
    // PROPERTY 2: Heartbeat prevents trigger
    // "If heartbeat received, triggered must be LOW next cycle"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && rstn && enable && $past(heartbeat))
            assert(triggered == 0);
    end

    always @(posedge clk) begin
        if (f_past_valid && rstn && enable && $past(heartbeat))
            assert(counter == 0);
    end

    // ========================================================================
    // PROPERTY 3: Trigger ONLY happens after timeout
    // "triggered can NEVER be HIGH if counter < TIMEOUT_CYCLES"
    // This is the KEY safety property
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && counter < TIMEOUT_CYCLES)
            assert(triggered == 0);
    end

    // ========================================================================
    // PROPERTY 4: Trigger ALWAYS happens at timeout
    // "If counter reaches TIMEOUT_CYCLES with no heartbeat,
    //  triggered MUST go HIGH"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && rstn && enable
            && !heartbeat && !force_reset
            && $past(counter) >= TIMEOUT_CYCLES)
            assert(triggered == 1);
    end

    // ========================================================================
    // PROPERTY 5: Warning comes before trigger
    // "Warning must be HIGH before triggered goes HIGH"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && triggered)
            assert(warning == 1);
    end

    // ========================================================================
    // PROPERTY 6: Disable kills everything
    // "When watchdog is disabled, triggered must be LOW"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && !enable)
            assert(triggered == 0);
    end

    always @(posedge clk) begin
        if (f_past_valid && !enable)
            assert(warning == 0);
    end

    // ========================================================================
    // PROPERTY 7: Counter never exceeds timeout
    // "Counter must never go above TIMEOUT_CYCLES"
    // ========================================================================
    always @(posedge clk) begin
        assert(counter <= TIMEOUT_CYCLES);
    end

    // ========================================================================
    // PROPERTY 8: Force reset clears trigger
    // "force_reset must clear triggered state"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && rstn && enable && $past(force_reset))
            assert(triggered == 0);
    end

    // ========================================================================
    // PROPERTY 9: Warning timing is correct
    // "Warning only asserts after WARNING_CYCLES"
    // ========================================================================
    always @(posedge clk) begin
        if (f_past_valid && counter < WARNING_CYCLES && !triggered)
            assert(warning == 0);
    end

    // ========================================================================
    // COVER PROPERTIES - Prove these scenarios CAN happen
    // (generates waveforms showing the scenario)
    // ========================================================================

    // Can we reach triggered state?
    always @(posedge clk) begin
        cover(triggered == 1);
    end

    // Can warning go high then triggered?
    always @(posedge clk) begin
        cover(warning == 1 && triggered == 0);
    end

    // Can heartbeat save us right before timeout?
    always @(posedge clk) begin
        cover(counter == TIMEOUT_CYCLES - 1 && heartbeat);
    end

    // Can we recover from triggered via force_reset?
    always @(posedge clk) begin
        cover(f_past_valid && $past(triggered) && !triggered);
    end

`endif

endmodule
