`timescale 1s / 1ms
//////////////////////////////////////////////////////////////////////////////////
// Formal Verification Properties for Watchdog Timer
// ===================================================
// DEMO VERSION: CLK_FREQ=1 so counter counts in whole seconds (0-5)
// Waveform output matches presentation slide timing diagram
// Note: -1 offsets compensate for non-blocking assignment delay
//////////////////////////////////////////////////////////////////////////////////
module watchdog_timer #(
    parameter CLK_FREQ    = 1,    // 1 tick = 1 second (for clean waveform)
    parameter TIMEOUT_SEC = 5     // 5 seconds timeout (matches real system)
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
    localparam TIMEOUT_CYCLES = CLK_FREQ * TIMEOUT_SEC;                   // = 5
    localparam WARNING_CYCLES = (CLK_FREQ * TIMEOUT_SEC * 8) / 10 - 1;  // = 3, appears at 4
    localparam DISPLAY_TIMEOUT = CLK_FREQ * TIMEOUT_SEC;                 // = 5, for time_remaining display
    localparam COUNTER_WIDTH  = 32;

    reg [COUNTER_WIDTH-1:0] counter;

    initial begin
        counter   = 0;
        triggered = 0;
        warning   = 0;
    end

    wire [31:0] remaining_cycles = (counter < TIMEOUT_CYCLES) ? (DISPLAY_TIMEOUT - counter) : 0;
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

    initial assume(rstn == 0);

    reg f_past_valid;
    initial f_past_valid = 0;
    always @(posedge clk)
        f_past_valid <= 1;

    // INPUT CONSTRAINTS
    always @(posedge clk) begin
        if (f_past_valid && $past(heartbeat))
            assume(!heartbeat);
    end

    // PROPERTY 1: Reset clears everything
    always @(posedge clk) begin
        if (f_past_valid && $past(!rstn)) begin
            assert(counter == 0);
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // PROPERTY 2: Heartbeat prevents trigger
    always @(posedge clk) begin
        if (f_past_valid && $past(rstn) && $past(enable) && $past(heartbeat)) begin
            assert(counter == 0);
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // PROPERTY 3: Trigger ONLY happens after timeout
    always @(posedge clk) begin
        if (counter < TIMEOUT_CYCLES)
            assert(triggered == 0);
    end

    // PROPERTY 4: Trigger ALWAYS happens at timeout
    always @(posedge clk) begin
        if (f_past_valid
            && $past(rstn) && $past(enable)
            && !$past(heartbeat) && !$past(force_reset)
            && $past(counter) >= TIMEOUT_CYCLES)
            assert(triggered == 1);
    end

    // PROPERTY 5: Warning comes before trigger
    always @(posedge clk) begin
        if (triggered)
            assert(warning == 1);
    end

    // PROPERTY 5b: Contrapositive
    always @(posedge clk) begin
        if (!warning)
            assert(!triggered);
    end

    // PROPERTY 6: Disable kills everything
    always @(posedge clk) begin
        if (f_past_valid && $past(!enable)) begin
            assert(counter == 0);
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // PROPERTY 7: Counter never exceeds timeout
    always @(posedge clk) begin
        assert(counter <= TIMEOUT_CYCLES);
    end

    // PROPERTY 8: Force reset clears trigger
    always @(posedge clk) begin
        if (f_past_valid && $past(rstn) && $past(enable) && $past(force_reset)) begin
            assert(counter == 0);
            assert(triggered == 0);
            assert(warning == 0);
        end
    end

    // PROPERTY 9: Warning timing — negative
    always @(posedge clk) begin
        if (counter < WARNING_CYCLES && !triggered)
            assert(warning == 0);
    end

    // PROPERTY 10: Warning timing — positive
    always @(posedge clk) begin
        if (counter > WARNING_CYCLES && counter < TIMEOUT_CYCLES)
            assert(warning == 1);
    end

    // PROPERTY 11: Counter increments correctly
    always @(posedge clk) begin
        if (f_past_valid
            && $past(rstn) && $past(enable)
            && !$past(heartbeat) && !$past(force_reset)
            && $past(counter) < TIMEOUT_CYCLES)
            assert(counter == $past(counter) + 1);
    end

    // PROPERTY 12: time_remaining correct at counter == 0
    always @(posedge clk) begin
        if (counter == 0)
            assert(time_remaining == TIMEOUT_SEC);
    end

    // PROPERTY 13: time_remaining == 0 when triggered
    always @(posedge clk) begin
        if (triggered)
            assert(time_remaining == 0);
    end

    // PROPERTY 14: time_remaining monotonically decreases
    always @(posedge clk) begin
        if (f_past_valid
            && $past(rstn) && $past(enable)
            && !$past(heartbeat) && !$past(force_reset)
            && $past(counter) < TIMEOUT_CYCLES)
            assert(time_remaining <= $past(time_remaining));
    end

    // COVER STATEMENTS
    always @(posedge clk) cover(triggered == 1);
    always @(posedge clk) cover(warning == 1 && triggered == 0);
    always @(posedge clk) cover(counter == TIMEOUT_CYCLES - 1 && heartbeat);
    always @(posedge clk) cover(f_past_valid && $past(triggered) && !triggered);
    always @(posedge clk) cover(counter == TIMEOUT_CYCLES);
    always @(posedge clk) cover(f_past_valid && $past(warning) && !$past(triggered) && triggered);

`endif

endmodule