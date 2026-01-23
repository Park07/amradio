`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: am_radio_dsp
// 
// DSP chain for 12-channel AM Radio Broadcast System
// Instantiates 12 NCOs and 12 AM modulators, sums output
//
// WARNING: This is for STRESS TESTING to find hardware limits
// Expected: Performance will degrade as channels are added
//
//////////////////////////////////////////////////////////////////////////////////

module am_radio_dsp (
    input  wire        clk,
    input  wire        rstn,
    
    // Audio input (from BRAM or ADC)
    input  wire signed [13:0] audio_in,
    
    // Control inputs (from am_radio_ctrl)
    input  wire        master_enable,
    input  wire [11:0] channel_enable,
    
    // Phase increments for each channel
    input  wire [31:0] ch1_phase_inc,
    input  wire [31:0] ch2_phase_inc,
    input  wire [31:0] ch3_phase_inc,
    input  wire [31:0] ch4_phase_inc,
    input  wire [31:0] ch5_phase_inc,
    input  wire [31:0] ch6_phase_inc,
    input  wire [31:0] ch7_phase_inc,
    input  wire [31:0] ch8_phase_inc,
    input  wire [31:0] ch9_phase_inc,
    input  wire [31:0] ch10_phase_inc,
    input  wire [31:0] ch11_phase_inc,
    input  wire [31:0] ch12_phase_inc,
    
    // RF output
    output wire signed [13:0] rf_out
);

    // =========================================================================
    // NCO outputs (carrier waves)
    // =========================================================================
    
    wire signed [13:0] carrier [0:11];
    
    // Instantiate 12 NCOs
    nco_sin u_nco_1  (.clk(clk), .rstn(rstn), .phase_inc(ch1_phase_inc),  .sin_out(carrier[0]));
    nco_sin u_nco_2  (.clk(clk), .rstn(rstn), .phase_inc(ch2_phase_inc),  .sin_out(carrier[1]));
    nco_sin u_nco_3  (.clk(clk), .rstn(rstn), .phase_inc(ch3_phase_inc),  .sin_out(carrier[2]));
    nco_sin u_nco_4  (.clk(clk), .rstn(rstn), .phase_inc(ch4_phase_inc),  .sin_out(carrier[3]));
    nco_sin u_nco_5  (.clk(clk), .rstn(rstn), .phase_inc(ch5_phase_inc),  .sin_out(carrier[4]));
    nco_sin u_nco_6  (.clk(clk), .rstn(rstn), .phase_inc(ch6_phase_inc),  .sin_out(carrier[5]));
    nco_sin u_nco_7  (.clk(clk), .rstn(rstn), .phase_inc(ch7_phase_inc),  .sin_out(carrier[6]));
    nco_sin u_nco_8  (.clk(clk), .rstn(rstn), .phase_inc(ch8_phase_inc),  .sin_out(carrier[7]));
    nco_sin u_nco_9  (.clk(clk), .rstn(rstn), .phase_inc(ch9_phase_inc),  .sin_out(carrier[8]));
    nco_sin u_nco_10 (.clk(clk), .rstn(rstn), .phase_inc(ch10_phase_inc), .sin_out(carrier[9]));
    nco_sin u_nco_11 (.clk(clk), .rstn(rstn), .phase_inc(ch11_phase_inc), .sin_out(carrier[10]));
    nco_sin u_nco_12 (.clk(clk), .rstn(rstn), .phase_inc(ch12_phase_inc), .sin_out(carrier[11]));

    // =========================================================================
    // AM Modulation outputs
    // =========================================================================
    
    wire signed [13:0] am_out [0:11];
    
    // Instantiate 12 AM modulators
    am_mod u_am_1  (.clk(clk), .audio(audio_in), .carrier(carrier[0]),  .am_out(am_out[0]));
    am_mod u_am_2  (.clk(clk), .audio(audio_in), .carrier(carrier[1]),  .am_out(am_out[1]));
    am_mod u_am_3  (.clk(clk), .audio(audio_in), .carrier(carrier[2]),  .am_out(am_out[2]));
    am_mod u_am_4  (.clk(clk), .audio(audio_in), .carrier(carrier[3]),  .am_out(am_out[3]));
    am_mod u_am_5  (.clk(clk), .audio(audio_in), .carrier(carrier[4]),  .am_out(am_out[4]));
    am_mod u_am_6  (.clk(clk), .audio(audio_in), .carrier(carrier[5]),  .am_out(am_out[5]));
    am_mod u_am_7  (.clk(clk), .audio(audio_in), .carrier(carrier[6]),  .am_out(am_out[6]));
    am_mod u_am_8  (.clk(clk), .audio(audio_in), .carrier(carrier[7]),  .am_out(am_out[7]));
    am_mod u_am_9  (.clk(clk), .audio(audio_in), .carrier(carrier[8]),  .am_out(am_out[8]));
    am_mod u_am_10 (.clk(clk), .audio(audio_in), .carrier(carrier[9]),  .am_out(am_out[9]));
    am_mod u_am_11 (.clk(clk), .audio(audio_in), .carrier(carrier[10]), .am_out(am_out[10]));
    am_mod u_am_12 (.clk(clk), .audio(audio_in), .carrier(carrier[11]), .am_out(am_out[11]));

    // =========================================================================
    // Channel gating (enable/disable each channel)
    // =========================================================================
    
    wire signed [13:0] gated [0:11];
    
    assign gated[0]  = channel_enable[0]  ? am_out[0]  : 14'sd0;
    assign gated[1]  = channel_enable[1]  ? am_out[1]  : 14'sd0;
    assign gated[2]  = channel_enable[2]  ? am_out[2]  : 14'sd0;
    assign gated[3]  = channel_enable[3]  ? am_out[3]  : 14'sd0;
    assign gated[4]  = channel_enable[4]  ? am_out[4]  : 14'sd0;
    assign gated[5]  = channel_enable[5]  ? am_out[5]  : 14'sd0;
    assign gated[6]  = channel_enable[6]  ? am_out[6]  : 14'sd0;
    assign gated[7]  = channel_enable[7]  ? am_out[7]  : 14'sd0;
    assign gated[8]  = channel_enable[8]  ? am_out[8]  : 14'sd0;
    assign gated[9]  = channel_enable[9]  ? am_out[9]  : 14'sd0;
    assign gated[10] = channel_enable[10] ? am_out[10] : 14'sd0;
    assign gated[11] = channel_enable[11] ? am_out[11] : 14'sd0;

    // =========================================================================
    // Sum all channels
    // =========================================================================
    
    // Use wider intermediate to prevent overflow
    // 12 channels * 14 bits = need 14 + 4 = 18 bits
    wire signed [17:0] sum_all;
    
    assign sum_all = gated[0] + gated[1] + gated[2] + gated[3] +
                     gated[4] + gated[5] + gated[6] + gated[7] +
                     gated[8] + gated[9] + gated[10] + gated[11];
    
    // =========================================================================
    // Scale down and saturate
    // =========================================================================
    
    // Divide by number of active channels to prevent clipping
    // For simplicity, divide by 16 (shift right 4 bits)
    wire signed [13:0] sum_scaled;
    assign sum_scaled = sum_all[17:4];  // Divide by 16
    
    // =========================================================================
    // Master enable gate
    // =========================================================================
    
    assign rf_out = master_enable ? sum_scaled : 14'sd0;

endmodule
