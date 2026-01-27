/**
 * Watchdog Timer - Fail-Safe Module
 * ==================================
 * 
 * Reddit advice (cannibal_catfish69):
 * "Controllers should be designed to anticipate loss of network connectivity 
 *  and FAIL SAFELY, maintain the state, or whatever should happen in the 
 *  absence of control."
 * 
 * Purpose:
 *   Auto-stops RF broadcast if control system stops communicating.
 *   Critical for tunnel emergency systems - can't have runaway transmitter.
 * 
 * Behavior:
 *   - Resets on any register write (proves control system is alive)
 *   - If no write for TIMEOUT seconds → forces broadcast OFF
 *   - Outputs watchdog_triggered flag for status reporting
 * 
 * Integration:
 *   broadcast_enable_safe = broadcast_enable_requested & ~watchdog_triggered;
 */

module watchdog_timer #(
    parameter CLK_FREQ = 125_000_000,  // 125 MHz for Red Pitaya
    parameter TIMEOUT_SEC = 5          // 5 second timeout
)(
    input  wire clk,
    input  wire rst_n,
    
    // Heartbeat input - resets watchdog
    input  wire heartbeat,             // Pulse on any register write
    
    // Manual control
    input  wire enable,                // Enable watchdog (can disable for testing)
    input  wire force_reset,           // Manual reset from control register
    
    // Status outputs
    output reg  watchdog_triggered,    // HIGH = timeout occurred, broadcast killed
    output reg  watchdog_warning,      // HIGH = 80% of timeout reached
    output wire [31:0] time_remaining  // Seconds until timeout (for status)
);

    // Calculate counter max value
    localparam TIMEOUT_CYCLES = CLK_FREQ * TIMEOUT_SEC;
    localparam WARNING_CYCLES = (CLK_FREQ * TIMEOUT_SEC * 8) / 10;  // 80% threshold
    
    // Counter width - need enough bits for timeout
    localparam COUNTER_WIDTH = $clog2(TIMEOUT_CYCLES + 1);
    
    reg [COUNTER_WIDTH-1:0] counter;
    
    // Calculate time remaining in seconds
    assign time_remaining = (TIMEOUT_CYCLES - counter) / CLK_FREQ;
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            watchdog_triggered <= 0;
            watchdog_warning <= 0;
        end
        else if (!enable) begin
            // Watchdog disabled - reset everything
            counter <= 0;
            watchdog_triggered <= 0;
            watchdog_warning <= 0;
        end
        else if (heartbeat || force_reset) begin
            // Heartbeat received - reset counter
            counter <= 0;
            watchdog_triggered <= 0;
            watchdog_warning <= 0;
        end
        else if (counter >= TIMEOUT_CYCLES) begin
            // TIMEOUT! Trigger fail-safe
            watchdog_triggered <= 1;
            watchdog_warning <= 1;
            // Counter stays at max (latched until reset)
        end
        else begin
            // Normal counting
            counter <= counter + 1;
            
            // Warning at 80% of timeout
            if (counter >= WARNING_CYCLES) begin
                watchdog_warning <= 1;
            end
        end
    end

endmodule


/**
 * Example integration in am_radio_ctrl.v:
 * =======================================
 *
 * // Instantiate watchdog
 * wire watchdog_triggered;
 * wire watchdog_warning;
 * wire [31:0] watchdog_time_remaining;
 * 
 * // Heartbeat = any AXI write
 * wire heartbeat = axi_wvalid && axi_wready;
 * 
 * watchdog_timer #(
 *     .CLK_FREQ(125_000_000),
 *     .TIMEOUT_SEC(5)
 * ) u_watchdog (
 *     .clk(clk),
 *     .rst_n(rst_n),
 *     .heartbeat(heartbeat),
 *     .enable(watchdog_enable),        // From control register
 *     .force_reset(watchdog_reset),    // From control register
 *     .watchdog_triggered(watchdog_triggered),
 *     .watchdog_warning(watchdog_warning),
 *     .time_remaining(watchdog_time_remaining)
 * );
 * 
 * // CRITICAL: Fail-safe broadcast control
 * // Broadcast only allowed if:
 * //   1. User requested it (broadcast_enable_reg)
 * //   2. Watchdog has NOT triggered
 * wire broadcast_enable_safe = broadcast_enable_reg && !watchdog_triggered;
 * 
 * // Use broadcast_enable_safe instead of broadcast_enable_reg
 * // in your NCO/modulator chain
 */
