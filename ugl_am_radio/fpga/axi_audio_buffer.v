`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: axi_audio_buffer (FIXED - Proper BRAM inference)
// 
// AXI-Writable Audio Buffer for Runtime Audio Loading
// FIXED: Uses proper dual-port BRAM inference pattern
//
// Memory Map:
//   Offset 0x0000: CTRL register (bit0=play, bit1=loop, bit2=load_done)
//   Offset 0x0004: NUM_SAMPLES register
//   Offset 0x0008: SAMPLE_RATE_DIV register  
//   Offset 0x000C: STATUS register (read-only)
//   Offset 0x1000+: Audio sample buffer
//////////////////////////////////////////////////////////////////////////////////

module axi_audio_buffer #(
    parameter BUFFER_DEPTH = 16384,     // Max samples (16K = ~4 sec at 4kHz)
    // 65536
    parameter SAMPLE_WIDTH = 14         // 14-bit for Red Pitaya DAC
)(
    // System busS
    input  wire        clk,
    input  wire        rstn,
    input  wire [31:0] sys_addr,
    input  wire [31:0] sys_wdata,
    input  wire        sys_wen,
    input  wire        sys_ren,
    output reg  [31:0] sys_rdata,
    output reg         sys_err,
    output reg         sys_ack,
    
    // Audio output
    output reg signed [SAMPLE_WIDTH-1:0] audio_out,
    output wire        audio_valid,
    
    // Status
    output wire        playing,
    output wire        buffer_ready
);

    // =========================================================================
    // Address Decoding
    // =========================================================================
    
    localparam ADDR_CTRL        = 4'h0;  // 0x00
    localparam ADDR_NUM_SAMPLES = 4'h1;  // 0x04
    localparam ADDR_SAMPLE_DIV  = 4'h2;  // 0x08
    localparam ADDR_STATUS      = 4'h3;  // 0x0C
    
    wire is_buffer_access = sys_addr[15:12] >= 4'h1;  // 0x1000+
    wire [14:0] buffer_wr_addr = sys_addr[16:2] - 15'h400;      // Word address for writes
    wire [3:0]  reg_addr = sys_addr[5:2];             // Register address
    
    // =========================================================================
    // Control Registers
    // =========================================================================
    
    reg [31:0] ctrl_reg;
    reg [31:0] num_samples_reg;
    reg [31:0] sample_div_reg;
    
    wire play_enable = ctrl_reg[0];
    wire loop_enable = ctrl_reg[1];
    wire load_done   = ctrl_reg[2];
    
    localparam DEFAULT_SAMPLE_DIV = 32'd25000;  // 4kHz at 125MHz
    
    // =========================================================================
    // Audio Buffer - TRUE DUAL-PORT BRAM
    // Port A: Write from AXI (sys bus)
    // Port B: Read for playback
    // =========================================================================
    
    // BRAM inference - separate read and write ports
    (* ram_style = "block" *)
    reg [SAMPLE_WIDTH-1:0] audio_buffer [0:BUFFER_DEPTH-1];
    
    // Port A: AXI Write (directly in write logic below)
    // Port B: Playback Read
    reg signed [SAMPLE_WIDTH-1:0] playback_sample;
    reg [16:0] play_pos;
    
    // Registered read for BRAM inference (Port B)
    always @(posedge clk) begin
        playback_sample <= audio_buffer[play_pos];
    end
    
    // =========================================================================
    // Playback State Machine
    // =========================================================================
    
    reg [31:0] div_counter;
    reg        sample_tick;
    reg        is_playing;
    
    // Generate sample tick at configured rate
    always @(posedge clk) begin
        if (!rstn || !play_enable) begin
            div_counter <= 0;
            sample_tick <= 0;
        end else begin
            if (div_counter >= sample_div_reg - 1) begin
                div_counter <= 0;
                sample_tick <= 1;
            end else begin
                div_counter <= div_counter + 1;
                sample_tick <= 0;
            end
        end
    end
    
    // Playback position counter
    always @(posedge clk) begin
        if (!rstn) begin
            play_pos <= 0;
            is_playing <= 0;
        end else if (!play_enable || !load_done) begin
            play_pos <= 0;
            is_playing <= 0;
        end else if (sample_tick) begin
            is_playing <= 1;
            if (play_pos >= num_samples_reg - 1) begin
                if (loop_enable) begin
                    play_pos <= 0;
                end else begin
                    is_playing <= 0;
                end
            end else begin
                play_pos <= play_pos + 1;
            end
        end
    end
    
    // Output audio sample
    always @(posedge clk) begin
        if (!rstn) begin
            audio_out <= 0;
        end else if (is_playing) begin
            audio_out <= playback_sample;
        end else begin
            audio_out <= 0;
        end
    end
    
    assign playing = is_playing;
    assign buffer_ready = load_done && (num_samples_reg > 0);
    assign audio_valid = is_playing;
    
    // =========================================================================
    // AXI Bus Interface
    // =========================================================================
    
    // Write logic - Port A of BRAM
    always @(posedge clk) begin
        if (!rstn) begin
            ctrl_reg        <= 32'h0;
            num_samples_reg <= 32'h0;
            sample_div_reg  <= DEFAULT_SAMPLE_DIV;
        end else if (sys_wen) begin
            if (is_buffer_access) begin
                // Write to audio buffer (BRAM Port A)
                if (buffer_wr_addr < BUFFER_DEPTH) begin
                    audio_buffer[buffer_wr_addr] <= sys_wdata[SAMPLE_WIDTH-1:0];
                end
            end else begin
                // Write to control registers
                case (reg_addr)
                    ADDR_CTRL:        ctrl_reg        <= sys_wdata;
                    ADDR_NUM_SAMPLES: num_samples_reg <= sys_wdata;
                    ADDR_SAMPLE_DIV:  sample_div_reg  <= sys_wdata;
                    default: ;
                endcase
            end
        end
    end
    
    // Read logic - registers only (buffer reads go through playback port)
    reg [SAMPLE_WIDTH-1:0] buffer_rd_data;
    reg [13:0] buffer_rd_addr_reg;
    
    // Registered buffer read address for BRAM
    always @(posedge clk) begin
        buffer_rd_addr_reg <= sys_addr[15:2];
    end
    
    // Separate BRAM read port for AXI reads
    always @(posedge clk) begin
        buffer_rd_data <= audio_buffer[buffer_rd_addr_reg];
    end
    
    always @(posedge clk) begin
        if (!rstn) begin
            sys_rdata <= 32'h0;
            sys_err   <= 1'b0;
            sys_ack   <= 1'b0;
        end else begin
            sys_err <= 1'b0;
            sys_ack <= sys_wen | sys_ren;
            
            if (sys_ren) begin
                if (is_buffer_access) begin
                    // Read from audio buffer (2-cycle latency for BRAM)
                    sys_rdata <= {{(32-SAMPLE_WIDTH){1'b0}}, buffer_rd_data};
                end else begin
                    // Read from control registers
                    case (reg_addr)
                        ADDR_CTRL:        sys_rdata <= ctrl_reg;
                        ADDR_NUM_SAMPLES: sys_rdata <= num_samples_reg;
                        ADDR_SAMPLE_DIV:  sys_rdata <= sample_div_reg;
                        ADDR_STATUS:      sys_rdata <= {13'b0, buffer_ready, is_playing, play_pos[16:0]};
                        default:          sys_rdata <= 32'h0;
                    endcase
                end
            end
        end
    end

endmodule
