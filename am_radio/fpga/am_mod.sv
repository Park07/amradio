`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/01/19 11:51:53
// Design Name: 
// Module Name: am_mod
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module am_mod #(
   parameter signed [13:0] M_Q = 14'sd6554 // m = 0.8
)(
    input  wire signed [13:0] carrier_q13,   // Q1.13
    input  wire signed [13:0] audio_q13,     // Q1.13  (-1..+1)
    output reg  signed [13:0] am_q13         // Q1.13
);

    // 1) m * audio  -> Q2.26 (Q1.13 * Q1.13)
    wire signed [27:0] mx_q26 = M_Q * audio_q13;

    // 2) back to Q2.13
    wire signed [15:0] mx_q13 = mx_q26 >>> 13; // Q2.13

    // 3) env = 1 + m*audio   (DSB-FC)
    // 1.0 in Q2.13 = 8192
    wire signed [15:0] env_q13 = 16'sd8192 + mx_q13;

    // 4) env * carrier -> Q3.26
    wire signed [31:0] prod_q26 = env_q13 * carrier_q13;

    // 5) 
       wire signed [18:0] y_q13_wide = prod_q26 >>> 14; // extra /2 headroom for DSB-FC
      
    // 6) saturate to signed 14-bit
    always @* begin
        if (y_q13_wide > 19'sd8191)
            am_q13 = 14'sd8191;
        else if (y_q13_wide < -19'sd8192)
            am_q13 = -14'sd8192;
        else
            am_q13 = y_q13_wide[13:0];
    end

endmodule

