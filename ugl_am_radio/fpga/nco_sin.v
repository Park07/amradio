`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/01/15 10:13:13
// Design Name: 
// Module Name: nco_sin
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


module nco_sin #(
    parameter integer N = 32,          // phase accumulator width
    parameter integer AW = 12           // LUT address bits: 2^AW points per cycle (e.g., 1024)
)(
    input  wire               clk,     // use dac_clk_1x (125MHz)
    input  wire               rstn,    // active-low reset
    input  wire [N-1:0]       phase_inc,
    output reg  signed [13:0] y14      // signed 14-bit sine out
);

    reg [N-1:0] phase;

    // 1024-point sine LUT, signed 14-bit
    reg signed [13:0] sin_lut [0:(1<<AW)-1];

    initial begin
        // Make sure sine_lut_1024.mem is accessible in the run directory
        $readmemh("sine_lut_4096.mem", sin_lut);
    end

    wire [AW-1:0] addr = phase[N-1 -: AW];

    always @(posedge clk) begin
        if (!rstn) begin
            phase <= {N{1'b0}};
            y14   <= 14'sd0;
        end else begin
            phase <= phase + phase_inc;
            y14   <= sin_lut[addr];
        end
    end

endmodule
