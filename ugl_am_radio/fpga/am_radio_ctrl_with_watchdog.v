/**
 * AM Radio Controller with Fail-Safe Watchdog
 * ============================================
 * 
 * This shows how to integrate the watchdog into your existing am_radio_ctrl.v
 * 
 * Register Map (updated):
 *   0x00: Control Register
 *         [0]    - Broadcast enable (request)
 *         [1]    - Source select (0=ADC, 1=BRAM)
 *         [4]    - Watchdog enable
 *         [5]    - Watchdog manual reset
 *         [7:6]  - Reserved
 *         [15:8] - Message ID
 *   
 *   0x04: Status Register (READ-ONLY)
 *         [0]    - Broadcast active (actual, after watchdog)
 *         [1]    - Watchdog triggered (FAIL-SAFE ACTIVATED)
 *         [2]    - Watchdog warning (80% of timeout)
 *         [3]    - CH1 enabled
 *         [4]    - CH2 enabled
 *         [7:5]  - Reserved
 *         [15:8] - Watchdog time remaining (seconds)
 *   
 *   0x08: CH1 Frequency
 *   0x0C: CH2 Frequency
 *   0x10: CH1 Control ([0] = enable)
 *   0x14: CH2 Control ([0] = enable)
 */

module am_radio_ctrl_with_watchdog #(
    parameter CLK_FREQ = 125_000_000,
    parameter WATCHDOG_TIMEOUT = 5,      // 5 second fail-safe timeout
    parameter NUM_CHANNELS = 2
)(
    // Clock and reset
    input  wire        clk,
    input  wire        rst_n,
    
    // AXI-Lite interface (directly from existing code)
    input  wire [31:0] axi_awaddr,
    input  wire        axi_awvalid,
    output wire        axi_awready,
    input  wire [31:0] axi_wdata,
    input  wire        axi_wvalid,
    output wire        axi_wready,
    output wire [1:0]  axi_bresp,
    output wire        axi_bvalid,
    input  wire        axi_bready,
    input  wire [31:0] axi_araddr,
    input  wire        axi_arvalid,
    output wire        axi_arready,
    output wire [31:0] axi_rdata,
    output wire [1:0]  axi_rresp,
    output wire        axi_rvalid,
    input  wire        axi_rready,
    
    // Audio input
    input  wire [13:0] adc_data,
    input  wire [15:0] bram_data,
    
    // RF output to DAC
    output wire [13:0] dac_data,
    
    // Channel frequency outputs (to NCOs)
    output wire [31:0] ch1_freq,
    output wire [31:0] ch2_freq,
    output wire        ch1_enable,
    output wire        ch2_enable,
    
    // Status LEDs
    output wire        led_broadcasting,
    output wire        led_watchdog_warning,
    output wire        led_watchdog_triggered
);

    // =========================================================================
    // Registers
    // =========================================================================
    
    reg [31:0] ctrl_reg;           // 0x00: Control
    reg [31:0] ch1_freq_reg;       // 0x08: CH1 Frequency
    reg [31:0] ch2_freq_reg;       // 0x0C: CH2 Frequency
    reg [31:0] ch1_ctrl_reg;       // 0x10: CH1 Control
    reg [31:0] ch2_ctrl_reg;       // 0x14: CH2 Control
    
    // Control register bits
    wire broadcast_enable_req = ctrl_reg[0];
    wire source_select        = ctrl_reg[1];
    wire watchdog_enable      = ctrl_reg[4];
    wire watchdog_reset       = ctrl_reg[5];
    wire [7:0] message_id     = ctrl_reg[15:8];
    
    // Channel enables
    wire ch1_enable_req = ch1_ctrl_reg[0];
    wire ch2_enable_req = ch2_ctrl_reg[0];
    
    // =========================================================================
    // Watchdog Timer (FAIL-SAFE)
    // =========================================================================
    
    // Heartbeat = any successful AXI write
    wire axi_write_complete = axi_wvalid && axi_wready;
    
    wire watchdog_triggered;
    wire watchdog_warning;
    wire [31:0] watchdog_time_remaining;
    
    watchdog_timer #(
        .CLK_FREQ(CLK_FREQ),
        .TIMEOUT_SEC(WATCHDOG_TIMEOUT)
    ) u_watchdog (
        .clk(clk),
        .rst_n(rst_n),
        .heartbeat(axi_write_complete),
        .enable(watchdog_enable),
        .force_reset(watchdog_reset),
        .watchdog_triggered(watchdog_triggered),
        .watchdog_warning(watchdog_warning),
        .time_remaining(watchdog_time_remaining)
    );
    
    // =========================================================================
    // CRITICAL: Fail-Safe Broadcast Control
    // =========================================================================
    
    // Broadcast is ONLY active if:
    //   1. User requested it
    //   2. At least one channel is enabled
    //   3. Watchdog has NOT triggered
    
    wire any_channel_enabled = ch1_enable_req || ch2_enable_req;
    
    wire broadcast_active = broadcast_enable_req 
                         && any_channel_enabled 
                         && !watchdog_triggered;
    
    // Channel outputs (also gated by watchdog)
    assign ch1_enable = ch1_enable_req && !watchdog_triggered;
    assign ch2_enable = ch2_enable_req && !watchdog_triggered;
    assign ch1_freq = ch1_freq_reg;
    assign ch2_freq = ch2_freq_reg;
    
    // =========================================================================
    // Status Register (READ-ONLY)
    // =========================================================================
    
    wire [31:0] status_reg;
    assign status_reg[0]    = broadcast_active;          // Actual state (after watchdog)
    assign status_reg[1]    = watchdog_triggered;        // Fail-safe activated!
    assign status_reg[2]    = watchdog_warning;          // Warning - 80% timeout
    assign status_reg[3]    = ch1_enable;                // CH1 actual state
    assign status_reg[4]    = ch2_enable;                // CH2 actual state
    assign status_reg[7:5]  = 3'b0;                      // Reserved
    assign status_reg[15:8] = watchdog_time_remaining[7:0]; // Seconds remaining
    assign status_reg[31:16] = 16'b0;                    // Reserved
    
    // =========================================================================
    // AXI-Lite Register Access
    // =========================================================================
    
    // Write logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_reg     <= 32'h00000010;  // Watchdog enabled by default
            ch1_freq_reg <= 32'd700000;    // 700 kHz default
            ch2_freq_reg <= 32'd900000;    // 900 kHz default
            ch1_ctrl_reg <= 32'h0;
            ch2_ctrl_reg <= 32'h0;
        end
        else if (axi_wvalid && axi_wready) begin
            case (axi_awaddr[7:0])
                8'h00: ctrl_reg     <= axi_wdata;
                8'h08: ch1_freq_reg <= axi_wdata;
                8'h0C: ch2_freq_reg <= axi_wdata;
                8'h10: ch1_ctrl_reg <= axi_wdata;
                8'h14: ch2_ctrl_reg <= axi_wdata;
            endcase
        end
        
        // Auto-clear watchdog reset bit
        if (ctrl_reg[5])
            ctrl_reg[5] <= 0;
    end
    
    // Read logic
    reg [31:0] read_data;
    always @(*) begin
        case (axi_araddr[7:0])
            8'h00: read_data = ctrl_reg;
            8'h04: read_data = status_reg;     // Status is read-only
            8'h08: read_data = ch1_freq_reg;
            8'h0C: read_data = ch2_freq_reg;
            8'h10: read_data = ch1_ctrl_reg;
            8'h14: read_data = ch2_ctrl_reg;
            default: read_data = 32'hDEADBEEF;
        endcase
    end
    
    assign axi_rdata = read_data;
    
    // =========================================================================
    // Audio Path (simplified)
    // =========================================================================
    
    wire [15:0] audio_sample;
    assign audio_sample = source_select ? bram_data : {adc_data, 2'b0};
    
    // Your AM modulator chain goes here...
    // dac_data = modulated output when broadcast_active
    
    // =========================================================================
    // LED Outputs
    // =========================================================================
    
    assign led_broadcasting       = broadcast_active;
    assign led_watchdog_warning   = watchdog_warning;
    assign led_watchdog_triggered = watchdog_triggered;

endmodule
