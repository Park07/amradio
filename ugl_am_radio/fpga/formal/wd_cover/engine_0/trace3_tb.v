`ifndef VERILATOR
module testbench;
  reg [4095:0] vcdfile;
  reg clock;
`else
module testbench(input clock, output reg genclock);
  initial genclock = 1;
`endif
  reg genclock = 1;
  reg [31:0] cycle = 0;
  wire [0:0] PI_clk = clock;
  reg [0:0] PI_force_reset;
  reg [0:0] PI_rstn;
  reg [0:0] PI_heartbeat;
  reg [0:0] PI_enable;
  watchdog_timer UUT (
    .clk(PI_clk),
    .force_reset(PI_force_reset),
    .rstn(PI_rstn),
    .heartbeat(PI_heartbeat),
    .enable(PI_enable)
  );
`ifndef VERILATOR
  initial begin
    if ($value$plusargs("vcd=%s", vcdfile)) begin
      $dumpfile(vcdfile);
      $dumpvars(0, testbench);
    end
    #5 clock = 0;
    while (genclock) begin
      #5 clock = 0;
      #5 clock = 1;
    end
  end
`endif
  initial begin
`ifndef VERILATOR
    #1;
`endif
    // UUT.$auto$async2sync.\cc:116:execute$483  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$489  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$495  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$501  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$507  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$513  = 1'b1;
    UUT._witness_.anyinit_procdff_298 = 1'b0;
    UUT._witness_.anyinit_procdff_299 = 1'b0;
    UUT._witness_.anyinit_procdff_300 = 1'b0;
    UUT._witness_.anyinit_procdff_326 = 1'b0;
    UUT.counter = 32'b00000000000000000000000000000000;
    UUT.f_past_valid = 1'b0;
    UUT.triggered = 1'b0;
    UUT.warning = 1'b0;

    // state 0
    PI_force_reset = 1'b0;
    PI_rstn = 1'b0;
    PI_heartbeat = 1'b0;
    PI_enable = 1'b1;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 2
    if (cycle == 1) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 3
    if (cycle == 2) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 4
    if (cycle == 3) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 5
    if (cycle == 4) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 6
    if (cycle == 5) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    // state 7
    if (cycle == 6) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b0;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b0;
    end

    // state 8
    if (cycle == 7) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b0;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b0;
    end

    // state 9
    if (cycle == 8) begin
      PI_force_reset <= 1'b0;
      PI_rstn <= 1'b1;
      PI_heartbeat <= 1'b0;
      PI_enable <= 1'b1;
    end

    genclock <= cycle < 9;
    cycle <= cycle + 1;
  end
endmodule
