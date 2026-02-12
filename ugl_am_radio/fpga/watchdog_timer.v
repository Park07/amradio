`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Watchdog Timer - Fail-Safe Module
// ==================================
// This is the actual version btw there are other watchdog after but those are for testing so u can ignore

// Purpose:
//   Auto-stops RF broadcast if control system stops communicating.
//   If no register write for TIMEOUT seconds → forces broadcast OFF
//
// Behaviour:
//   - Resets on any register write (heartbeat)
//   - Counts up every clock cycle
//   - At 80% timeout: warning flag
//   - At 100% timeout: triggered flag (KILLS BROADCAST)
//   - Triggered state latches until manual reset or disable
//
//////////////////////////////////////////////////////////////////////////////////

module watchdog_timer #(
    parameter CLK_FREQ    = 125_000_000,  // 125 MHz for Red Pitaya
    parameter TIMEOUT_SEC = 5             // 5 second timeout
)(
    input  wire        clk,
    input  wire        rstn,

    // Control
    input  wire        heartbeat,      // Pulse on any register write
    input  wire        enable,         // Enable watchdog
    input  wire        force_reset,    // Manual reset

    // Status
    output reg         triggered,      // HIGH = timeout, broadcast killed
    output reg         warning,        // HIGH = 80% of timeout reached
    output wire [7:0]  time_remaining  // Seconds until timeout
);

    // Counter parameters
    localparam TIMEOUT_CYCLES = CLK_FREQ * TIMEOUT_SEC;
    localparam WARNING_CYCLES = (CLK_FREQ * TIMEOUT_SEC * 8) / 10;  // 80%
    localparam COUNTER_WIDTH  = 32;  // Enough for 34 seconds at 125MHz

    reg [COUNTER_WIDTH-1:0] counter;

    // Time remaining in seconds (saturate at 255)
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
            // Watchdog disabled - reset everything
            counter   <= 0;
            triggered <= 0;
            warning   <= 0;
        end
        else if (heartbeat || force_reset) begin
            // Heartbeat received - reset counter
            counter   <= 0;
            triggered <= 0;
            warning   <= 0;
        end
        else if (counter >= TIMEOUT_CYCLES) begin
            // TIMEOUT! Trigger fail-safe (latched)
            triggered <= 1;
            warning   <= 1;
            // Counter stays at max
        end
        else begin
            // Normal counting
            counter <= counter + 1;

            // Warning at 80%
            if (counter >= WARNING_CYCLES)
                warning <= 1;
            else
                warning <= 0;
        end
    end

endmodule
