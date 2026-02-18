`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: am_radio_ctrl (12-Channel Version)
// 
// SCPI Control Interface for AM Radio Broadcast System
// Updated for 12-channel stress testing
//
// Register Map:
//   0x00: CTRL_REG
//         [0]   - master_enable (OUTPUT:STATE ON/OFF)
//         [3]   - source_sel (0=BRAM, 1=ADC)
//         [7:4] - msg_select (SOURCE:MSG 1-4)
//
//   0x04: CH1_FREQ  - NCO phase increment for channel 1
//   0x08: CH2_FREQ  - NCO phase increment for channel 2
//   0x0C: CH3_FREQ  - NCO phase increment for channel 3
//   0x10: CH4_FREQ  - NCO phase increment for channel 4
//   0x14: CH5_FREQ  - NCO phase increment for channel 5
//   0x18: CH6_FREQ  - NCO phase increment for channel 6
//   0x1C: CH7_FREQ  - NCO phase increment for channel 7
//   0x20: CH8_FREQ  - NCO phase increment for channel 8
//   0x24: CH9_FREQ  - NCO phase increment for channel 9
//   0x28: CH10_FREQ - NCO phase increment for channel 10
//   0x2C: CH11_FREQ - NCO phase increment for channel 11
//   0x30: CH12_FREQ - NCO phase increment for channel 12
//
//   0x34: CH_ENABLE - [11:0] = channel enable bits (CH1=bit0, CH12=bit11)
//
//   0x38: STATUS_REG (read-only)
//
//////////////////////////////////////////////////////////////////////////////////


module am_radio_ctrl #(
    parameter CLK_FREQ = 125_000_000,
    parameter WD_TIMEOUT = 5 
    )(
    input  wire        clk,
    input  wire        rstn,
    input  wire [31:0] sys_addr,
    input  wire [31:0] sys_wdata,
    input  wire        sys_wen,
    input  wire        sys_ren,
    output reg  [31:0] sys_rdata,
    output reg         sys_err,
    output reg         sys_ack,
    
    output wire        master_enable,
    output wire        source_sel,
    output wire [3:0]  msg_select,
    output wire [11:0] ch_enable,
    output wire [31:0] ch1_phase_inc,
    output wire [31:0] ch2_phase_inc,
    output wire [31:0] ch3_phase_inc,
    output wire [31:0] ch4_phase_inc,
    output wire [31:0] ch5_phase_inc,
    output wire [31:0] ch6_phase_inc,
    output wire [31:0] ch7_phase_inc,
    output wire [31:0] ch8_phase_inc,
    output wire [31:0] ch9_phase_inc,
    output wire [31:0] ch10_phase_inc,
    output wire [31:0] ch11_phase_inc,
    output wire [31:0] ch12_phase_inc,
    
    output wire watchdog_triggered,
    output wire watchdog_warning
);

    // Address constants
    localparam ADDR_CTRL      = 8'h00;
    localparam ADDR_CH1_FREQ  = 8'h04;
    localparam ADDR_CH2_FREQ  = 8'h08;
    localparam ADDR_CH3_FREQ  = 8'h0C;
    localparam ADDR_CH4_FREQ  = 8'h10;
    localparam ADDR_CH5_FREQ  = 8'h14;
    localparam ADDR_CH6_FREQ  = 8'h18;
    localparam ADDR_CH7_FREQ  = 8'h1C;
    localparam ADDR_CH8_FREQ  = 8'h20;
    localparam ADDR_CH9_FREQ  = 8'h24;
    localparam ADDR_CH10_FREQ = 8'h28;
    localparam ADDR_CH11_FREQ = 8'h2C;
    localparam ADDR_CH12_FREQ = 8'h30;
    localparam ADDR_CH_ENABLE = 8'h34;
    localparam ADDR_STATUS    = 8'h38;


    // Formula: phase_inc = (freq_hz * 2^32) / 125_000_000
    localparam [31:0] DEFAULT_CH1_FREQ  = 32'h0108D032;  // 505 kHz
    localparam [31:0] DEFAULT_CH2_FREQ  = 32'h013D7799;  // 605 kHz
    localparam [31:0] DEFAULT_CH3_FREQ  = 32'h01718701;  // 705 kHz
    localparam [31:0] DEFAULT_CH4_FREQ  = 32'h01A59668;  // 805 kHz
    localparam [31:0] DEFAULT_CH5_FREQ  = 32'h01D9A5D0;  // 905 kHz
    localparam [31:0] DEFAULT_CH6_FREQ  = 32'h020DB538;  // 1005 kHz
    localparam [31:0] DEFAULT_CH7_FREQ  = 32'h0241C4A0;  // 1105 kHz
    localparam [31:0] DEFAULT_CH8_FREQ  = 32'h0275D407;  // 1205 kHz
    localparam [31:0] DEFAULT_CH9_FREQ  = 32'h02A9E36E;  // 1305 kHz
    localparam [31:0] DEFAULT_CH10_FREQ = 32'h02DDF2D6;  // 1405 kHz
    localparam [31:0] DEFAULT_CH11_FREQ = 32'h0312023E;  // 1505 kHz
    localparam [31:0] DEFAULT_CH12_FREQ = 32'h034611A5;  // 1605 kHz
    
    // =========================================================================
    // Control Register Bits
    // =========================================================================
    wire master_enable_req = ctrl_reg[0];
    wire source_sel_reg    = ctrl_reg[3];
    wire watchdog_enable   = ctrl_reg[4];
    wire watchdog_reset    = ctrl_reg[5];

    // =========================================================================
    // Watchdog Timer
    // =========================================================================
    wire heartbeat = sys_wen;  // Any write = heartbeat
    wire [7:0] watchdog_time_remaining;

    watchdog_timer #(
        .CLK_FREQ(CLK_FREQ),
        .TIMEOUT_SEC(WD_TIMEOUT)
    ) u_watchdog (
        .clk(clk),
        .rstn(rstn),
        .heartbeat(heartbeat),
        .enable(watchdog_enable),
        .force_reset(watchdog_reset),
        .triggered(watchdog_triggered),
        .warning(watchdog_warning),
        .time_remaining(watchdog_time_remaining)
    );
    // Registers
    reg [31:0] ctrl_reg;
    reg [31:0] ch1_freq_reg,  ch2_freq_reg,  ch3_freq_reg,  ch4_freq_reg;
    reg [31:0] ch5_freq_reg,  ch6_freq_reg,  ch7_freq_reg,  ch8_freq_reg;
    reg [31:0] ch9_freq_reg,  ch10_freq_reg, ch11_freq_reg, ch12_freq_reg;
    reg [11:0] ch_enable_reg;

    // Write logic
    always @(posedge clk) begin
        if (!rstn) begin
            ctrl_reg      <= 32'h00000010;
            ch1_freq_reg  <= DEFAULT_CH1_FREQ;
            ch2_freq_reg  <= DEFAULT_CH2_FREQ;
            ch3_freq_reg  <= DEFAULT_CH3_FREQ;
            ch4_freq_reg  <= DEFAULT_CH4_FREQ;
            ch5_freq_reg  <= DEFAULT_CH5_FREQ;
            ch6_freq_reg  <= DEFAULT_CH6_FREQ;
            ch7_freq_reg  <= DEFAULT_CH7_FREQ;
            ch8_freq_reg  <= DEFAULT_CH8_FREQ;
            ch9_freq_reg  <= DEFAULT_CH9_FREQ;
            ch10_freq_reg <= DEFAULT_CH10_FREQ;
            ch11_freq_reg <= DEFAULT_CH11_FREQ;
            ch12_freq_reg <= DEFAULT_CH12_FREQ;
            ch_enable_reg <= 12'b0;
        end
        else begin
            if (ctrl_reg[5])
                ctrl_reg[5] <= 1'b0;
            if (sys_wen) begin
                case (sys_addr[7:0])
                    ADDR_CTRL:      ctrl_reg      <= sys_wdata;
                    ADDR_CH1_FREQ:  ch1_freq_reg  <= sys_wdata;
                    ADDR_CH2_FREQ:  ch2_freq_reg  <= sys_wdata;
                    ADDR_CH3_FREQ:  ch3_freq_reg  <= sys_wdata;
                    ADDR_CH4_FREQ:  ch4_freq_reg  <= sys_wdata;
                    ADDR_CH5_FREQ:  ch5_freq_reg  <= sys_wdata;
                    ADDR_CH6_FREQ:  ch6_freq_reg  <= sys_wdata;
                    ADDR_CH7_FREQ:  ch7_freq_reg  <= sys_wdata;
                    ADDR_CH8_FREQ:  ch8_freq_reg  <= sys_wdata;
                    ADDR_CH9_FREQ:  ch9_freq_reg  <= sys_wdata;
                    ADDR_CH10_FREQ: ch10_freq_reg <= sys_wdata;
                    ADDR_CH11_FREQ: ch11_freq_reg <= sys_wdata;
                    ADDR_CH12_FREQ: ch12_freq_reg <= sys_wdata;
                    ADDR_CH_ENABLE: ch_enable_reg <= sys_wdata[11:0];
                endcase
            end
        end
       end

    // Read logic
    always @(posedge clk) begin
        if (!rstn) begin
            sys_rdata <= 32'h0;
            sys_ack   <= 1'b0;
            sys_err   <= 1'b0;
        end
        else begin
            sys_ack <= sys_wen | sys_ren;
            sys_err <= 1'b0;
            
            if (sys_ren) begin
                case (sys_addr[7:0])
                    ADDR_CTRL:      sys_rdata <= ctrl_reg;
                    ADDR_CH1_FREQ:  sys_rdata <= ch1_freq_reg;
                    ADDR_CH2_FREQ:  sys_rdata <= ch2_freq_reg;
                    ADDR_CH3_FREQ:  sys_rdata <= ch3_freq_reg;
                    ADDR_CH4_FREQ:  sys_rdata <= ch4_freq_reg;
                    ADDR_CH5_FREQ:  sys_rdata <= ch5_freq_reg;
                    ADDR_CH6_FREQ:  sys_rdata <= ch6_freq_reg;
                    ADDR_CH7_FREQ:  sys_rdata <= ch7_freq_reg;
                    ADDR_CH8_FREQ:  sys_rdata <= ch8_freq_reg;
                    ADDR_CH9_FREQ:  sys_rdata <= ch9_freq_reg;
                    ADDR_CH10_FREQ: sys_rdata <= ch10_freq_reg;
                    ADDR_CH11_FREQ: sys_rdata <= ch11_freq_reg;
                    ADDR_CH12_FREQ: sys_rdata <= ch12_freq_reg;
                    ADDR_CH_ENABLE: sys_rdata <= {20'b0, ch_enable_reg};
                    ADDR_STATUS:    sys_rdata <= {4'b0, ch_enable_reg, watchdog_time_remaining, 
                                                  4'b0, watchdog_enable, watchdog_warning, 
                                                  watchdog_triggered, master_enable};
                    
                    
                    default:        sys_rdata <= 32'hDEADBEEF;
                endcase
            end
        end
    end

    // Outputs
    assign master_enable  = ctrl_reg[0] && !watchdog_triggered;
    assign source_sel     = ctrl_reg[3];
    assign msg_select     = ctrl_reg[7:4];
    assign ch_enable      = ch_enable_reg;
    assign ch1_phase_inc  = ch1_freq_reg;
    assign ch2_phase_inc  = ch2_freq_reg;
    assign ch3_phase_inc  = ch3_freq_reg;
    assign ch4_phase_inc  = ch4_freq_reg;
    assign ch5_phase_inc  = ch5_freq_reg;
    assign ch6_phase_inc  = ch6_freq_reg;
    assign ch7_phase_inc  = ch7_freq_reg;
    assign ch8_phase_inc  = ch8_freq_reg;
    assign ch9_phase_inc  = ch9_freq_reg;
    assign ch10_phase_inc = ch10_freq_reg;
    assign ch11_phase_inc = ch11_freq_reg;
    assign ch12_phase_inc = ch12_freq_reg;

endmodule
