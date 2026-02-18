////////////////////////////////////////////////////////////////////////////////
// Red Pitaya TOP module - 12-CHANNEL AM RADIO VERSION
// Authors: Matej Oblak, Iztok Jeras
// (c) Red Pitaya  http://www.redpitaya.com
//
// MODIFIED: 12-channel AM Radio for stress testing
////////////////////////////////////////////////////////////////////////////////

module red_pitaya_top #(
  bit [0:5*32-1] GITH = '0,
  parameter MNA = 2,
  parameter MNG = 2,
  parameter ADW_125 = 14,
  parameter ADW_122 = 16,
  parameter DWE_Z20 = 11,
  parameter DWE_Z10 = 8,
  parameter DDW     = 14,
`ifdef Z20_122
  parameter ADW=ADW_122,
  parameter ADC_DW=ADW_122,
`else
  parameter ADW=ADW_125,
  parameter ADC_DW=ADW_125,
`endif
`ifdef Z20_xx
  parameter DWE=DWE_Z20
`else
  parameter DWE=DWE_Z10
`endif
)(
  inout  logic [54-1:0] FIXED_IO_mio     ,
  inout  logic          FIXED_IO_ps_clk  ,
  inout  logic          FIXED_IO_ps_porb ,
  inout  logic          FIXED_IO_ps_srstb,
  inout  logic          FIXED_IO_ddr_vrn ,
  inout  logic          FIXED_IO_ddr_vrp ,
  inout  logic [15-1:0] DDR_addr   ,
  inout  logic [ 3-1:0] DDR_ba     ,
  inout  logic          DDR_cas_n  ,
  inout  logic          DDR_ck_n   ,
  inout  logic          DDR_ck_p   ,
  inout  logic          DDR_cke    ,
  inout  logic          DDR_cs_n   ,
  inout  logic [ 4-1:0] DDR_dm     ,
  inout  logic [32-1:0] DDR_dq     ,
  inout  logic [ 4-1:0] DDR_dqs_n  ,
  inout  logic [ 4-1:0] DDR_dqs_p  ,
  inout  logic          DDR_odt    ,
  inout  logic          DDR_ras_n  ,
  inout  logic          DDR_reset_n,
  inout  logic          DDR_we_n   ,
  input  logic [MNA-1:0] [16-1:0] adc_dat_i,
  input  logic           [ 2-1:0] adc_clk_i,
  output logic           [ 2-1:0] adc_clk_o,
  output logic                    adc_cdcs_o,
  output logic [ 14-1:0] dac_dat_o  ,
  output logic           dac_wrt_o  ,
  output logic           dac_sel_o  ,
  output logic           dac_clk_o  ,
  output logic           dac_rst_o  ,
  output logic [  4-1:0] dac_pwm_o  ,
  input  logic [  5-1:0] vinp_i     ,
  input  logic [  5-1:0] vinn_i     ,
  inout  logic [DWE-1:0] exp_p_io  ,
  inout  logic [DWE-1:0] exp_n_io  ,
  output logic [  2-1:0] daisy_p_o  ,
  output logic [  2-1:0] daisy_n_o  ,
  input  logic [  2-1:0] daisy_p_i  ,
  input  logic [  2-1:0] daisy_n_i  ,
  `ifdef Z20_G2
  output logic [  4-1:0] exp_e3p_o  ,
  output logic [  4-1:0] exp_e3n_o  ,
  input  logic [  4-1:0] exp_e3p_i  ,
  input  logic [  4-1:0] exp_e3n_i  ,
  input  logic           s1_orient_i ,
  input  logic           s1_link_i   ,
  `endif
  output  logic [  8-1:0] led_o
);

////////////////////////////////////////////////////////////////////////////////
// local signals
////////////////////////////////////////////////////////////////////////////////

localparam int unsigned GDW = DWE;
localparam RST_MAX = 64;
logic [4-1:0] fclk;
logic [4-1:0] frstn;
logic [16-1:0] par_dat;
logic          daisy_trig;
logic [ 3-1:0] daisy_mode;
logic          trig_ext;
logic          trig_output_sel;
logic          trig_asg_out;
logic [ 4-1:0] trig_ext_asg01;

logic                 adc_clk_in;
logic                 pll_adc_clk;
logic                 pll_dac_clk_1x;
logic                 pll_dac_clk_2x;
logic                 pll_dac_clk_2p;
logic                 pll_ser_clk;
logic                 pll_pwm_clk;
logic                 pll_locked;
logic                 pll_locked_r;
logic                 fpll_locked_r,fpll_locked_r2,fpll_locked_r3;

logic   [16-1:0]      rst_cnt = 'h0;
logic                 rst_after_locked;
logic                 rstn_pll;

logic                 ser_clk ;
logic                 pwm_clk ;
logic                 pwm_rstn;

logic                 adc_clk;
logic                 adc_rstn;
logic                 adc_clk_daisy;
logic                 scope_trigo;

logic                 CAN0_rx, CAN0_tx;
logic                 CAN1_rx, CAN1_tx;
logic                 can_on;

localparam type SBA_T = logic signed [ADW-1:0];
localparam type SBG_T = logic signed [ 14-1:0];

SBA_T [MNA-1:0]          adc_dat;

logic                    dac_clk_1x;
logic                    dac_clk_2x;
logic                    dac_clk_2p;
logic                    dac_axi_clk;
logic                    dac_rst;
logic                    dac_axi_rstn;

logic        [14-1:0] dac_dat_a, dac_dat_b;
logic        [14-1:0] dac_a    , dac_b    ;
logic signed [15-1:0] dac_a_sum, dac_b_sum;

////////////////////////////////////////////////////////////////////////////////
// 12-CHANNEL GUI CONTROL SIGNALS
////////////////////////////////////////////////////////////////////////////////
wire        ctrl_master_enable;
wire        ctrl_source_sel;
wire [3:0]  ctrl_msg_select;
wire [11:0] ctrl_ch_enable;

wire [31:0] ctrl_ch1_phase_inc,  ctrl_ch2_phase_inc,  ctrl_ch3_phase_inc,  ctrl_ch4_phase_inc;
wire [31:0] ctrl_ch5_phase_inc,  ctrl_ch6_phase_inc,  ctrl_ch7_phase_inc,  ctrl_ch8_phase_inc;
wire [31:0] ctrl_ch9_phase_inc,  ctrl_ch10_phase_inc, ctrl_ch11_phase_inc, ctrl_ch12_phase_inc;
wire watchdog_triggered;
wire watchdog_warning;
wire [7:0] hk_led;

// 12 NCO outputs
logic signed [13:0] nco_y [0:11];

// 12 AM modulator outputs
logic signed [13:0] am_y [0:11];

// 12 gated outputs
logic signed [13:0] am_gated [0:11];

// Audio and RF
logic signed [13:0] audio_source;
logic signed [13:0] rf_out;

// AXI Audio output
wire signed [13:0] axi_audio_out;

////////////////////////////////////////////////////////////////////////////////
// AXI Audio Buffer (sys[6] = 0x40600000)
////////////////////////////////////////////////////////////////////////////////
axi_audio_buffer i_axi_audio (
    .clk(adc_clk),
    .rstn(adc_rstn),
    .sys_addr(sys[6].addr),
    .sys_wdata(sys[6].wdata),
    .sys_wen(sys[6].wen),
    .sys_ren(sys[6].ren),
    .sys_rdata(sys[6].rdata),
    .sys_err(sys[6].err),
    .sys_ack(sys[6].ack),
    .audio_out(axi_audio_out),
    .audio_valid(),
    .playing(),
    .buffer_ready()
);

// Audio source: BRAM or ADC
assign audio_source = ctrl_source_sel ? $signed(adc_dat[0][13:0]) : axi_audio_out;

// ASG
SBG_T [2-1:0]            asg_dat;

// PID
SBA_T [2-1:0]            pid_dat;

// configuration
logic [2-1:0]            digital_loop;

// system bus
sys_bus_if   ps_sys      (.clk (fclk[0]), .rstn (frstn[0]));
sys_bus_if   sys [8-1:0] (.clk (adc_clk), .rstn (adc_rstn));

// GPIO interface
gpio_if #(.DW (3*GDW)) gpio ();

// AXI masters
axi_sys_if axi0_sys (.clk(adc_clk    ), .rstn(adc_rstn    ));
axi_sys_if axi1_sys (.clk(adc_clk    ), .rstn(adc_rstn    ));
axi_sys_if axi2_sys (.clk(dac_axi_clk), .rstn(dac_axi_rstn));
axi_sys_if axi3_sys (.clk(dac_axi_clk), .rstn(dac_axi_rstn));

////////////////////////////////////////////////////////////////////////////////
// PLL (clock and reset)
////////////////////////////////////////////////////////////////////////////////

IBUFDS i_clk (.I (adc_clk_i[1]), .IB (adc_clk_i[0]), .O (adc_clk_in));

assign rstn_pll = frstn[0] & ~(!fpll_locked_r2 && fpll_locked_r3);
red_pitaya_pll pll (
  .clk         (adc_clk_in),
  .rstn        (rstn_pll  ),
  .clk_adc     (pll_adc_clk   ),
  .clk_dac_1x  (pll_dac_clk_1x),
  .clk_dac_2x  (pll_dac_clk_2x),
  .clk_dac_2p  (pll_dac_clk_2p),
  .clk_ser     (pll_ser_clk   ),
  .clk_pdm     (pll_pwm_clk   ),
  .pll_locked  (pll_locked    )
);

BUFG bufg_adc_clk     (.O (adc_clk    ), .I (pll_adc_clk   ));
BUFG bufg_dac_clk_1x  (.O (dac_clk_1x ), .I (pll_dac_clk_1x));
BUFG bufg_dac_clk_2x  (.O (dac_clk_2x ), .I (pll_dac_clk_2x));
BUFG bufg_dac_axi_clk (.O (dac_axi_clk), .I (pll_dac_clk_2x));
BUFG bufg_dac_clk_2p (.O (dac_clk_2p), .I (pll_dac_clk_2p));
BUFG bufg_ser_clk    (.O (ser_clk   ), .I (pll_ser_clk   ));
BUFG bufg_pwm_clk    (.O (pwm_clk   ), .I (pll_pwm_clk   ));

always @(posedge fclk[0]) begin
  fpll_locked_r   <= pll_locked;
  fpll_locked_r2  <= fpll_locked_r;
  fpll_locked_r3  <= fpll_locked_r2;
end

always @(posedge adc_clk) begin
  pll_locked_r <= pll_locked;
  if ((pll_locked && !pll_locked_r) || rst_cnt > 0) begin
    if (rst_cnt < RST_MAX)
      rst_cnt <= rst_cnt + 1;
    else 
      rst_cnt <= 'h0;
  end else begin
    if (~pll_locked)
      rst_cnt <= 'h0;
  end
end

assign rst_after_locked = |rst_cnt;

always @(posedge adc_clk)
adc_rstn     <=  frstn[0] & ~rst_after_locked;

always @(posedge dac_clk_1x)
dac_rst      <= ~frstn[0] |  rst_after_locked;

always @(posedge dac_axi_clk)
dac_axi_rstn <=  frstn[0] & ~rst_after_locked;

always @(posedge pwm_clk)
pwm_rstn     <=  frstn[0] & ~rst_after_locked;

////////////////////////////////////////////////////////////////////////////////
//  Connections to PS
////////////////////////////////////////////////////////////////////////////////

red_pitaya_ps ps (
  .FIXED_IO_mio       (  FIXED_IO_mio                ),
  .FIXED_IO_ps_clk    (  FIXED_IO_ps_clk             ),
  .FIXED_IO_ps_porb   (  FIXED_IO_ps_porb            ),
  .FIXED_IO_ps_srstb  (  FIXED_IO_ps_srstb           ),
  .FIXED_IO_ddr_vrn   (  FIXED_IO_ddr_vrn            ),
  .FIXED_IO_ddr_vrp   (  FIXED_IO_ddr_vrp            ),
  .DDR_addr      (DDR_addr    ),
  .DDR_ba        (DDR_ba      ),
  .DDR_cas_n     (DDR_cas_n   ),
  .DDR_ck_n      (DDR_ck_n    ),
  .DDR_ck_p      (DDR_ck_p    ),
  .DDR_cke       (DDR_cke     ),
  .DDR_cs_n      (DDR_cs_n    ),
  .DDR_dm        (DDR_dm      ),
  .DDR_dq        (DDR_dq      ),
  .DDR_dqs_n     (DDR_dqs_n   ),
  .DDR_dqs_p     (DDR_dqs_p   ),
  .DDR_odt       (DDR_odt     ),
  .DDR_ras_n     (DDR_ras_n   ),
  .DDR_reset_n   (DDR_reset_n ),
  .DDR_we_n      (DDR_we_n    ),
  .fclk_clk_o    (fclk        ),
  .fclk_rstn_o   (frstn       ),
  .vinp_i        (vinp_i      ),
  .vinn_i        (vinn_i      ),
  .CAN0_rx       (CAN0_rx     ),
  .CAN0_tx       (CAN0_tx     ),
  .CAN1_rx       (CAN1_rx     ),
  .CAN1_tx       (CAN1_tx     ),
  .gpio          (gpio),
  .bus           (ps_sys      ),
  .axi0_sys      (axi0_sys    ),
  .axi1_sys      (axi1_sys    ),
  .axi2_sys      (axi2_sys    ),
  .axi3_sys      (axi3_sys    )
);

////////////////////////////////////////////////////////////////////////////////
// system bus decoder & multiplexer
////////////////////////////////////////////////////////////////////////////////

sys_bus_interconnect #(
  .SN (8),
  .SW (20)
) sys_bus_interconnect (
  .pll_locked_i(pll_locked),
  .bus_m (ps_sys),
  .bus_s (sys)
);


`ifndef SCOPE_ONLY

assign daisy_trig = |par_dat;
assign trig_ext   = gpio.i[GDW] & ~(daisy_mode[0] & daisy_trig);

////////////////////////////////////////////////////////////////////////////////
// Analog mixed signals (PDM analog outputs)
////////////////////////////////////////////////////////////////////////////////

logic [4-1:0] [8-1:0] pdm_cfg;

red_pitaya_ams i_ams (
  .clk_i           (adc_clk ),
  .rstn_i          (adc_rstn),
  .dac_a_o         (pdm_cfg[0]),
  .dac_b_o         (pdm_cfg[1]),
  .dac_c_o         (pdm_cfg[2]),
  .dac_d_o         (pdm_cfg[3]),
  .sys_addr        (sys[4].addr ),
  .sys_wdata       (sys[4].wdata),
  .sys_wen         (sys[4].wen  ),
  .sys_ren         (sys[4].ren  ),
  .sys_rdata       (sys[4].rdata),
  .sys_err         (sys[4].err  ),
  .sys_ack         (sys[4].ack  )
);

red_pitaya_pdm pdm (
  .clk   (adc_clk ),
  .rstn  (adc_rstn),
  .cfg   (pdm_cfg),
  .ena      (1'b1),
  .rng      (8'd255),
  .pdm (dac_pwm_o)
);

////////////////////////////////////////////////////////////////////////////////
// ADC IO
////////////////////////////////////////////////////////////////////////////////

ODDR i_adc_clk_p ( .Q(adc_clk_o[0]), .D1(1'b1), .D2(1'b0), .C(adc_clk_daisy), .CE(1'b1), .R(1'b0), .S(1'b0));
ODDR i_adc_clk_n ( .Q(adc_clk_o[1]), .D1(1'b0), .D2(1'b1), .C(adc_clk_daisy), .CE(1'b1), .R(1'b0), .S(1'b0));

assign adc_cdcs_o = 1'b1 ;

logic [2-1:0] [ADW-1:0] adc_dat_raw;

assign adc_dat_raw[0] = adc_dat_i[0][16-1 -: ADW];
assign adc_dat_raw[1] = adc_dat_i[1][16-1 -: ADW];

always @(posedge adc_clk) begin
  adc_dat[0] <= digital_loop[0] ? dac_a : {adc_dat_raw[0][ADW-1], ~adc_dat_raw[0][ADW-2:0]};
  adc_dat[1] <= digital_loop[0] ? dac_b : {adc_dat_raw[1][ADW-1], ~adc_dat_raw[1][ADW-2:0]};
end

////////////////////////////////////////////////////////////////////////////////
// DAC IO - 12-CHANNEL NCO and AM Modulation
////////////////////////////////////////////////////////////////////////////////

// Pack phase increments into array
wire [31:0] phase_inc [0:11];
assign phase_inc[0]  = ctrl_ch1_phase_inc;
assign phase_inc[1]  = ctrl_ch2_phase_inc;
assign phase_inc[2]  = ctrl_ch3_phase_inc;
assign phase_inc[3]  = ctrl_ch4_phase_inc;
assign phase_inc[4]  = ctrl_ch5_phase_inc;
assign phase_inc[5]  = ctrl_ch6_phase_inc;
assign phase_inc[6]  = ctrl_ch7_phase_inc;
assign phase_inc[7]  = ctrl_ch8_phase_inc;
assign phase_inc[8]  = ctrl_ch9_phase_inc;
assign phase_inc[9]  = ctrl_ch10_phase_inc;
assign phase_inc[10] = ctrl_ch11_phase_inc;
assign phase_inc[11] = ctrl_ch12_phase_inc;

// Generate 12 NCOs and AM modulators
genvar gi;
generate
    for (gi = 0; gi < 12; gi = gi + 1) begin : gen_nco_am
        nco_sin #(.N(32), .AW(12)) u_nco (
            .clk       (dac_clk_1x),
            .rstn      (~dac_rst),
            .phase_inc (phase_inc[gi]),
            .y14       (nco_y[gi])
        );
        
        am_mod #(.M_Q(14'sd6554)) u_am (
            .carrier_q13 (nco_y[gi]),
            .audio_q13   (audio_source),
            .am_q13      (am_y[gi])
        );
        
        assign am_gated[gi] = (ctrl_master_enable && ctrl_ch_enable[gi]) ? am_y[gi] : 14'sd0;
    end
endgenerate

// Sum all 12 channels (need 18 bits for headroom)
wire signed [17:0] sum_all = 
    $signed(am_gated[0])  + $signed(am_gated[1])  + $signed(am_gated[2])  + $signed(am_gated[3]) +
    $signed(am_gated[4])  + $signed(am_gated[5])  + $signed(am_gated[6])  + $signed(am_gated[7]) +
    $signed(am_gated[8])  + $signed(am_gated[9])  + $signed(am_gated[10]) + $signed(am_gated[11]);

// Count enabled channels for dynamic power scaling
wire [3:0] enabled_count = ctrl_ch_enable[0] + ctrl_ch_enable[1] + ctrl_ch_enable[2] + 
                           ctrl_ch_enable[3] + ctrl_ch_enable[4] + ctrl_ch_enable[5] +
                           ctrl_ch_enable[6] + ctrl_ch_enable[7] + ctrl_ch_enable[8] +
                           ctrl_ch_enable[9] + ctrl_ch_enable[10] + ctrl_ch_enable[11];

// Dynamic shift: fewer channels = more power per channel
reg [3:0] shift_amount;
always @* begin
    case (enabled_count)
        4'd0, 4'd1:                 shift_amount = 0;  // Full power
        4'd2:                       shift_amount = 1;  // /2
        4'd3, 4'd4:                 shift_amount = 2;  // /4
        4'd5, 4'd6, 4'd7, 4'd8:     shift_amount = 3;  // /8
        default:                    shift_amount = 4;  // /16
    endcase
end

wire signed [17:0] sum_scaled = sum_all >>> shift_amount;  // DYNAMIC divide!

// Saturate to 14-bit
always @* begin
    if (sum_scaled > 18'sd8191)
        rf_out = 14'sd8191;
    else if (sum_scaled < -18'sd8192)
        rf_out = -14'sd8192;
    else
        rf_out = sum_scaled[13:0];
end

// DAC output
assign dac_a_sum = {{1{rf_out[13]}}, rf_out};
assign dac_b_sum = {{1{rf_out[13]}}, rf_out};

// saturation
assign dac_a = (^dac_a_sum[15-1:15-2]) ? {dac_a_sum[15-1], {13{~dac_a_sum[15-1]}}} : dac_a_sum[14-1:0];
assign dac_b = (^dac_b_sum[15-1:15-2]) ? {dac_b_sum[15-1], {13{~dac_b_sum[15-1]}}} : dac_b_sum[14-1:0];

// output registers
always @(posedge dac_clk_1x) begin
  dac_dat_a <= digital_loop[1] ? {adc_dat[0][ADW-1], ~adc_dat[0][ADW-2 -: 13]} : {dac_a[14-1], ~dac_a[14-2:0]};
  dac_dat_b <= digital_loop[1] ? {adc_dat[1][ADW-1], ~adc_dat[1][ADW-2 -: 13]} : {dac_b[14-1], ~dac_b[14-2:0]};
end

// DDR outputs
ODDR oddr_dac_clk          (.Q(dac_clk_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2p), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_wrt          (.Q(dac_wrt_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_sel          (.Q(dac_sel_o), .D1(1'b1     ), .D2(1'b0     ), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));
ODDR oddr_dac_rst          (.Q(dac_rst_o), .D1(dac_rst  ), .D2(dac_rst  ), .C(dac_clk_1x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_dat [14-1:0] (.Q(dac_dat_o), .D1(dac_dat_b), .D2(dac_dat_a), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));

////////////////////////////////////////////////////////////////////////////////
//  House Keeping
////////////////////////////////////////////////////////////////////////////////

logic [DWE-1: 0] exp_p_in ,  exp_n_in ;
logic [DWE-1: 0] exp_p_out,  exp_n_out;
logic [DWE-1: 0] exp_p_dir,  exp_n_dir;
logic [DWE-1: 0] exp_p_otr,  exp_n_otr;
logic [DWE-1: 0] exp_p_dtr,  exp_n_dtr;
logic [DWE-1: 0] exp_p_alt,  exp_n_alt;
logic [DWE-1: 0] exp_p_altr, exp_n_altr;
logic [DWE-1: 0] exp_p_altd, exp_n_altd;

wire [7:0] hk_led;

red_pitaya_hk #(.DWE(DWE)) i_hk (
  .clk_i           (adc_clk    ),
  .rstn_i          (adc_rstn   ),
  .fclk_i          (fclk[0]    ),
  .frstn_i         (frstn[0]   ),
  .led_o           (  hk_led    ),
  .digital_loop    (digital_loop),
  .daisy_mode_o    (daisy_mode),
  .exp_p_dat_i     (exp_p_in ),
  .exp_p_dat_o     (exp_p_out),
  .exp_p_dir_o     (exp_p_dir),
  .exp_n_dat_i     (exp_n_in ),
  .exp_n_dat_o     (exp_n_out),
  .exp_n_dir_o     (exp_n_dir),
  .can_on_o        (can_on   ),
  .sys_addr        (sys[0].addr ),
  .sys_wdata       (sys[0].wdata),
  .sys_wen         (sys[0].wen  ),
  .sys_ren         (sys[0].ren  ),
  .sys_rdata       (sys[0].rdata),
  .sys_err         (sys[0].err  ),
  .sys_ack         (sys[0].ack  )
);

////////////////////////////////////////////////////////////////////////////////
// GPIO
////////////////////////////////////////////////////////////////////////////////

assign trig_output_sel = daisy_mode[2] ? trig_asg_out : scope_trigo;

assign exp_p_alt  = {DWE{1'b0}};
assign exp_n_alt  = {{DWE-8{1'b0}},  can_on,  can_on, 5'h0, daisy_mode[1]  };

assign exp_p_altr = {DWE{1'b0}};
assign exp_n_altr = {{DWE-8{1'b0}}, CAN0_tx, CAN1_tx, 5'h0, trig_output_sel};

assign exp_p_altd = {DWE{1'b0}};
assign exp_n_altd = {{DWE-8{1'b0}},   1'b1,   1'b1, 5'h0, 1'b1};

genvar GM;
generate
for(GM = 0 ; GM < DWE ; GM = GM + 1) begin : gpios
  assign exp_p_otr[GM] = exp_p_alt[GM] ? exp_p_altr[GM] : exp_p_out[GM];
  assign exp_n_otr[GM] = exp_n_alt[GM] ? exp_n_altr[GM] : exp_n_out[GM];
  assign exp_p_dtr[GM] = exp_p_alt[GM] ? exp_p_altd[GM] : exp_p_dir[GM];
  assign exp_n_dtr[GM] = exp_n_alt[GM] ? exp_n_altd[GM] : exp_n_dir[GM];
end
endgenerate

IOBUF i_iobufp [DWE-1:0] (.O(exp_p_in), .IO(exp_p_io), .I(exp_p_otr), .T(~exp_p_dtr) );
IOBUF i_iobufn [DWE-1:0] (.O(exp_n_in), .IO(exp_n_io), .I(exp_n_otr), .T(~exp_n_dtr) );

assign gpio.i[2*GDW-1:  GDW] = exp_p_in[GDW-1:0];
assign gpio.i[3*GDW-1:2*GDW] = exp_n_in[GDW-1:0];

assign CAN0_rx = can_on & exp_p_in[7];
assign CAN1_rx = can_on & exp_p_in[6];

////////////////////////////////////////////////////////////////////////////////
// oscilloscope
////////////////////////////////////////////////////////////////////////////////

wire [ 4-1:0] trig_ch_0_1;
wire [ 4-1:0] trig_ch_2_3 = 4'h0;
wire [16-1:0] trg_state_ch_0_1;
wire [16-1:0] trg_state_ch_2_3 = 16'h0;
wire [16-1:0] adc_state_ch_0_1;
wire [16-1:0] adc_state_ch_2_3 = 16'h0;
wire [16-1:0] axi_state_ch_0_1;
wire [16-1:0] axi_state_ch_2_3 = 16'h0;

rp_scope_com #(
  .CHN(0),
  .N_CH(2),
  .DW(14),
  .RSZ(14)) 
  i_scope (
  .adc_dat_i     ({adc_dat[1], adc_dat[0]}  ),
  .adc_clk_i     ({2{adc_clk}}  ),
  .adc_rstn_i    ({2{adc_rstn}} ),
  .trig_ext_i    (trig_ext    ),
  .trig_asg_i    (trig_asg_out),
  .trig_ch_o     (trig_ch_0_1 ),
  .trig_ch_i     (trig_ch_2_3 ),
  .trig_ext_asg_o(trig_ext_asg01),
  .trig_ext_asg_i(trig_ext_asg01),
  .daisy_trig_o  (scope_trigo ),
  .adc_state_o   (adc_state_ch_0_1),
  .adc_state_i   (adc_state_ch_2_3),
  .axi_state_o   (axi_state_ch_0_1),
  .axi_state_i   (axi_state_ch_2_3),
  .trg_state_o   (trg_state_ch_0_1),
  .trg_state_i   (trg_state_ch_2_3),
  .axi_waddr_o  ({axi1_sys.waddr,  axi0_sys.waddr} ),
  .axi_wdata_o  ({axi1_sys.wdata,  axi0_sys.wdata} ),
  .axi_wsel_o   ({axi1_sys.wsel,   axi0_sys.wsel}  ),
  .axi_wvalid_o ({axi1_sys.wvalid, axi0_sys.wvalid}),
  .axi_wlen_o   ({axi1_sys.wlen,   axi0_sys.wlen}  ),
  .axi_wfixed_o ({axi1_sys.wfixed, axi0_sys.wfixed}),
  .axi_werr_i   ({axi1_sys.werr,   axi0_sys.werr}  ),
  .axi_wrdy_i   ({axi1_sys.wrdy,   axi0_sys.wrdy}  ),
  .sys_addr      (sys[1].addr ),
  .sys_wdata     (sys[1].wdata),
  .sys_wen       (sys[1].wen  ),
  .sys_ren       (sys[1].ren  ),
  .sys_rdata     (sys[1].rdata),
  .sys_err       (sys[1].err  ),
  .sys_ack       (sys[1].ack  )
);

////////////////////////////////////////////////////////////////////////////////
//  DAC arbitrary signal generator
////////////////////////////////////////////////////////////////////////////////

red_pitaya_asg i_asg (
  .dac_a_o         (asg_dat[0]  ),
  .dac_b_o         (asg_dat[1]  ),
  .dac_clk_i       (adc_clk     ),
  .dac_rstn_i      (adc_rstn    ),
  .trig_a_i        (trig_ext    ),
  .trig_b_i        (trig_ext    ),
  .trig_out_o      (trig_asg_out),
  .axi_a_sys       (axi2_sys    ),
  .axi_b_sys       (axi3_sys    ),
  .sys_addr        (sys[2].addr ),
  .sys_wdata       (sys[2].wdata),
  .sys_wen         (sys[2].wen  ),
  .sys_ren         (sys[2].ren  ),
  .sys_rdata       (sys[2].rdata),
  .sys_err         (sys[2].err  ),
  .sys_ack         (sys[2].ack  )
);

////////////////////////////////////////////////////////////////////////////////
//  MIMO PID controller
////////////////////////////////////////////////////////////////////////////////

red_pitaya_pid i_pid (
  .clk_i           (adc_clk   ),
  .rstn_i          (adc_rstn  ),
  .dat_a_i         (adc_dat[0]),
  .dat_b_i         (adc_dat[1]),
  .dat_a_o         (pid_dat[0]),
  .dat_b_o         (pid_dat[1]),
  .sys_addr        (sys[3].addr ),
  .sys_wdata       (sys[3].wdata),
  .sys_wen         (sys[3].wen  ),
  .sys_ren         (sys[3].ren  ),
  .sys_rdata       (sys[3].rdata),
  .sys_err         (sys[3].err  ),
  .sys_ack         (sys[3].ack  )
);

////////////////////////////////////////////////////////////////////////////////
// Daisy test code
////////////////////////////////////////////////////////////////////////////////

wire daisy_rx_rdy ;
wire dly_clk = fclk[3];
wire [16-1:0] par_dati = daisy_mode[0] ? {16{trig_output_sel}} : 16'h1234;
wire          par_dvi  = daisy_mode[0] ? 1'b0 : daisy_rx_rdy;

red_pitaya_daisy i_daisy (
  .daisy_p_o       (  daisy_p_o                  ),
  .daisy_n_o       (  daisy_n_o                  ),
  .daisy_p_i       (  daisy_p_i                  ),
  .daisy_n_i       (  daisy_n_i                  ),
  .ser_clk_i       (  ser_clk                    ),
  .dly_clk_i       (  dly_clk                    ),
  .par_clk_i       (  adc_clk                    ),
  .par_rstn_i      (  adc_rstn                   ),
  .par_rdy_o       (  daisy_rx_rdy               ),
  .par_dv_i        (  par_dvi                    ),
  .par_dat_i       (  par_dati                   ),
  .par_clk_o       ( adc_clk_daisy               ),
  .par_rstn_o      (                             ),
  .par_dv_o        (                             ),
  .par_dat_o       ( par_dat                     ),
  .sync_mode_i     (  daisy_mode[0]              ),
  .debug_o         (/*led_o*/                    ),
  .sys_clk_i       (  adc_clk                    ),
  .sys_rstn_i      (  adc_rstn                   ),
  .sys_addr_i      (  sys[5].addr                ),
  .sys_sel_i       (                             ),
  .sys_wdata_i     (  sys[5].wdata               ),
  .sys_wen_i       (  sys[5].wen                 ),
  .sys_ren_i       (  sys[5].ren                 ),
  .sys_rdata_o     (  sys[5].rdata               ),
  .sys_err_o       (  sys[5].err                 ),
  .sys_ack_o       (  sys[5].ack                 )
);

////////////////////////////////////////////////////////////////////////////////
// AM Radio Control (12-Channel) - sys[7]
////////////////////////////////////////////////////////////////////////////////

am_radio_ctrl #(
    .CLK_FREQ       (125_000_000),
    .WD_TIMEOUT     (5)
    ) u_am_ctrl (
    .clk            (adc_clk),
    .rstn           (adc_rstn),
    .sys_addr       (sys[7].addr),
    .sys_wdata      (sys[7].wdata),
    .sys_wen        (sys[7].wen),
    .sys_ren        (sys[7].ren),
    .sys_rdata      (sys[7].rdata),
    .sys_err        (sys[7].err),
    .sys_ack        (sys[7].ack),
    
    .master_enable  (ctrl_master_enable),
    .source_sel     (ctrl_source_sel),
    .msg_select     (ctrl_msg_select),
    .ch_enable      (ctrl_ch_enable),
    .ch1_phase_inc  (ctrl_ch1_phase_inc),
    .ch2_phase_inc  (ctrl_ch2_phase_inc),
    .ch3_phase_inc  (ctrl_ch3_phase_inc),
    .ch4_phase_inc  (ctrl_ch4_phase_inc),
    .ch5_phase_inc  (ctrl_ch5_phase_inc),
    .ch6_phase_inc  (ctrl_ch6_phase_inc),
    .ch7_phase_inc  (ctrl_ch7_phase_inc),
    .ch8_phase_inc  (ctrl_ch8_phase_inc),
    .ch9_phase_inc  (ctrl_ch9_phase_inc),
    .ch10_phase_inc (ctrl_ch10_phase_inc),
    .ch11_phase_inc (ctrl_ch11_phase_inc),
    .ch12_phase_inc (ctrl_ch12_phase_inc),
    .watchdog_triggered (watchdog_triggered),
    .watchdog_warning (watchdog_warning)
);
assign led_o[7] = watchdog_triggered;
assign led_o[6] = watchdog_warning;
assign led_o[5:1] = hk_led[5:1];
assign led_o[0] = ctrl_master_enable;

`else
// SCOPE_ONLY mode - stub everything
IOBUF i_iobuf (.O(trig_ext), .IO(exp_p_io[0]), .I(1'b0), .T(1'b1) );

logic [2-1:0] [ADW-1:0] adc_dat_raw_scope;

always @(posedge adc_clk) begin
  adc_dat_raw_scope[0] <= adc_dat_i[0][16-1 -: ADW];
  adc_dat_raw_scope[1] <= adc_dat_i[1][16-1 -: ADW];
  adc_dat[0] <= {adc_dat_raw_scope[0][ADW-1], ~adc_dat_raw_scope[0][ADW-2:0]};
  adc_dat[1] <= {adc_dat_raw_scope[1][ADW-1], ~adc_dat_raw_scope[1][ADW-2:0]};
end

assign dac_dat_a = 14'h0;
assign dac_dat_b = 14'h0;

ODDR oddr_dac_clk_scope          (.Q(dac_clk_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2p), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_wrt_scope          (.Q(dac_wrt_o), .D1(1'b0     ), .D2(1'b1     ), .C(dac_clk_2x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_sel_scope          (.Q(dac_sel_o), .D1(1'b1     ), .D2(1'b0     ), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));
ODDR oddr_dac_rst_scope          (.Q(dac_rst_o), .D1(dac_rst  ), .D2(dac_rst  ), .C(dac_clk_1x), .CE(1'b1), .R(1'b0   ), .S(1'b0));
ODDR oddr_dac_dat_scope [14-1:0] (.Q(dac_dat_o), .D1(dac_dat_b), .D2(dac_dat_a), .C(dac_clk_1x), .CE(1'b1), .R(dac_rst), .S(1'b0));

ODDR i_adc_clk_p_scope ( .Q(adc_clk_o[0]), .D1(1'b1), .D2(1'b0), .C(1'b0), .CE(1'b1), .R(1'b0), .S(1'b0));
ODDR i_adc_clk_n_scope ( .Q(adc_clk_o[1]), .D1(1'b0), .D2(1'b1), .C(1'b0), .CE(1'b1), .R(1'b0), .S(1'b0));

assign adc_cdcs_o = 1'b1 ;
assign dac_pwm_o  = 1'b0;

generate
for (genvar i=2; i<7; i++) begin: for_sys2
  sys_bus_stub sys_bus_stub_2_5 (sys[i]);
end: for_sys2
endgenerate
sys_bus_stub sys_bus_stub_7_scope (sys[7]);

`endif
endmodule: red_pitaya_top
