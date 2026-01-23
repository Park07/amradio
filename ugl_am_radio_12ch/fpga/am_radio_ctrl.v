`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: am_radio_ctrl
// 
// SCPI Control Interface for AM Radio Broadcast System
// Updated: 12 channels for stress testing
//
// Register Map:
//   0x00: CTRL_REG
//         [0]     - master_enable
//         [1]     - source_sel (0=BRAM, 1=ADC)
//         [7:4]   - msg_select
//         [19:8]  - channel_enable (12 bits, one per channel)
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
//   0x34: STATUS_REG (read-only)
//
// Formula: phase_inc = (freq_hz * 2^32) / 125_000_000
//
//////////////////////////////////////////////////////////////////////////////////

module am_radio_ctrl #(
    parameter NUM_CHANNELS = 12
)(
    // System bus
    input  wire        clk,
    input  wire        rstn,
    input  wire [31:0] addr,
    input  wire [31:0] wdata,
    input  wire        wen,
    input  wire        ren,
    output reg  [31:0] rdata,
    output reg         rack,
    output reg         wack,

    // Control outputs
    output wire        master_enable,
    output wire        source_sel,
    output wire [3:0]  msg_select,
    output wire [11:0] channel_enable,
    
    // Frequency outputs (active low reset default values)
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
    output wire [31:0] ch12_phase_inc
);

    // =========================================================================
    // Registers
    // =========================================================================
    
    reg [31:0] ctrl_reg;
    reg [31:0] freq_reg [0:11];  // 12 frequency registers
    
    // Default phase increments (calculated for common frequencies)
    // phase_inc = (freq_hz * 2^32) / 125_000_000
    localparam [31:0] DEFAULT_FREQ_1  = 32'h01124528;  // 531 kHz
    localparam [31:0] DEFAULT_FREQ_2  = 32'h01480000;  // 600 kHz
    localparam [31:0] DEFAULT_FREQ_3  = 32'h016F0069;  // 700 kHz
    localparam [31:0] DEFAULT_FREQ_4  = 32'h01960000;  // 800 kHz
    localparam [31:0] DEFAULT_FREQ_5  = 32'h01BD0000;  // 900 kHz
    localparam [31:0] DEFAULT_FREQ_6  = 32'h01E40000;  // 1000 kHz
    localparam [31:0] DEFAULT_FREQ_7  = 32'h020B0000;  // 1100 kHz
    localparam [31:0] DEFAULT_FREQ_8  = 32'h02320000;  // 1200 kHz
    localparam [31:0] DEFAULT_FREQ_9  = 32'h02590000;  // 1300 kHz
    localparam [31:0] DEFAULT_FREQ_10 = 32'h02800000;  // 1400 kHz
    localparam [31:0] DEFAULT_FREQ_11 = 32'h02A70000;  // 1500 kHz
    localparam [31:0] DEFAULT_FREQ_12 = 32'h02CE0000;  // 1600 kHz

    // =========================================================================
    // Control register bits
    // =========================================================================
    
    assign master_enable  = ctrl_reg[0];
    assign source_sel     = ctrl_reg[1];
    assign msg_select     = ctrl_reg[7:4];
    assign channel_enable = ctrl_reg[19:8];
    
    // =========================================================================
    // Frequency outputs
    // =========================================================================
    
    assign ch1_phase_inc  = freq_reg[0];
    assign ch2_phase_inc  = freq_reg[1];
    assign ch3_phase_inc  = freq_reg[2];
    assign ch4_phase_inc  = freq_reg[3];
    assign ch5_phase_inc  = freq_reg[4];
    assign ch6_phase_inc  = freq_reg[5];
    assign ch7_phase_inc  = freq_reg[6];
    assign ch8_phase_inc  = freq_reg[7];
    assign ch9_phase_inc  = freq_reg[8];
    assign ch10_phase_inc = freq_reg[9];
    assign ch11_phase_inc = freq_reg[10];
    assign ch12_phase_inc = freq_reg[11];

    // =========================================================================
    // Register write logic
    // =========================================================================
    
    integer i;
    
    always @(posedge clk) begin
        if (!rstn) begin
            // Reset to defaults
            ctrl_reg <= 32'h0;
            freq_reg[0]  <= DEFAULT_FREQ_1;
            freq_reg[1]  <= DEFAULT_FREQ_2;
            freq_reg[2]  <= DEFAULT_FREQ_3;
            freq_reg[3]  <= DEFAULT_FREQ_4;
            freq_reg[4]  <= DEFAULT_FREQ_5;
            freq_reg[5]  <= DEFAULT_FREQ_6;
            freq_reg[6]  <= DEFAULT_FREQ_7;
            freq_reg[7]  <= DEFAULT_FREQ_8;
            freq_reg[8]  <= DEFAULT_FREQ_9;
            freq_reg[9]  <= DEFAULT_FREQ_10;
            freq_reg[10] <= DEFAULT_FREQ_11;
            freq_reg[11] <= DEFAULT_FREQ_12;
            wack <= 1'b0;
        end
        else begin
            wack <= 1'b0;
            
            if (wen) begin
                case (addr[7:0])
                    8'h00: ctrl_reg    <= wdata;
                    8'h04: freq_reg[0] <= wdata;
                    8'h08: freq_reg[1] <= wdata;
                    8'h0C: freq_reg[2] <= wdata;
                    8'h10: freq_reg[3] <= wdata;
                    8'h14: freq_reg[4] <= wdata;
                    8'h18: freq_reg[5] <= wdata;
                    8'h1C: freq_reg[6] <= wdata;
                    8'h20: freq_reg[7] <= wdata;
                    8'h24: freq_reg[8] <= wdata;
                    8'h28: freq_reg[9] <= wdata;
                    8'h2C: freq_reg[10] <= wdata;
                    8'h30: freq_reg[11] <= wdata;
                endcase
                wack <= 1'b1;
            end
        end
    end

    // =========================================================================
    // Register read logic
    // =========================================================================
    
    always @(posedge clk) begin
        if (!rstn) begin
            rdata <= 32'h0;
            rack  <= 1'b0;
        end
        else begin
            rack <= 1'b0;
            
            if (ren) begin
                case (addr[7:0])
                    8'h00: rdata <= ctrl_reg;
                    8'h04: rdata <= freq_reg[0];
                    8'h08: rdata <= freq_reg[1];
                    8'h0C: rdata <= freq_reg[2];
                    8'h10: rdata <= freq_reg[3];
                    8'h14: rdata <= freq_reg[4];
                    8'h18: rdata <= freq_reg[5];
                    8'h1C: rdata <= freq_reg[6];
                    8'h20: rdata <= freq_reg[7];
                    8'h24: rdata <= freq_reg[8];
                    8'h28: rdata <= freq_reg[9];
                    8'h2C: rdata <= freq_reg[10];
                    8'h30: rdata <= freq_reg[11];
                    8'h34: rdata <= {12'b0, channel_enable, msg_select, source_sel, master_enable};
                    default: rdata <= 32'h0;
                endcase
                rack <= 1'b1;
            end
        end
    end

endmodule
