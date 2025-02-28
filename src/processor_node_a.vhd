------------------------------
------------------------------
--- Cholesky factorization ---
---        using           ---
--- systolic architecture  ---
------------------------------
------------------------------
--- Marco Riggirello, 2025 ---
------------------------------
------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.fixed_pkg.all;


entity processor_node_a is
  generic (
    -- Input sizes
    NW_INTEGER_WIDTH : natural := 4;
    NW_DECIMAL_WIDTH : natural := 4;
    NE_INTEGER_WIDTH : natural := 4;
    NE_DECIMAL_WIDTH : natural := 4;
    S_INTEGER_WIDTH  : natural := 4;
    S_DECIMAL_WIDTH  : natural := 4;
    -- Output sizes
    SE_INTEGER_WIDTH : natural := 8;
    SE_DECIMAL_WIDTH : natural := 8;
    SW_INTEGER_WIDTH : natural := 8;
    SW_DECIMAL_WIDTH : natural := 8;
    N_INTEGER_WIDTH  : natural := 8;
    N_DECIMAL_WIDTH  : natural := 8
  );
  port (
    clk         : in  std_logic;
    rst         : in  std_logic;
    data_in_nw  : in  sfixed (NW_INTEGER_WIDTH - 1 downto -NW_DECIMAL_WIDTH);
    data_in_ne  : in  sfixed (NE_INTEGER_WIDTH - 1 downto -NE_DECIMAL_WIDTH);
    data_in_s   : in  sfixed ( S_INTEGER_WIDTH - 1 downto  -S_DECIMAL_WIDTH);
    data_out_se : out sfixed (SE_INTEGER_WIDTH - 1 downto -SE_DECIMAL_WIDTH);
    data_out_sw : out sfixed (SW_INTEGER_WIDTH - 1 downto -SW_DECIMAL_WIDTH);
    data_out_n  : out sfixed ( N_INTEGER_WIDTH - 1 downto  -N_DECIMAL_WIDTH)
  );
end processor_node_a;

architecture rtl of processor_node_a is

  signal a : sfixed (data_in_nw'range) := (others => '0');
  signal b : sfixed (data_in_ne'range) := (others => '0');
  signal c : sfixed ( data_in_s'range) := (others => '0');

  constant m_left  : integer := sfixed_high (a'left, a'right, '*', b'left, b'right);
  constant m_right : integer := sfixed_low  (a'left, a'right, '*', b'left, b'right);

  signal m : sfixed (m_left downto m_right) := (others => '0');

  constant s_left  : integer := sfixed_high (c'left, c'right, '+', m'left, m'right);
  constant s_right : integer := sfixed_low  (c'left, c'right, '+', m'left, m'right);

  signal s : sfixed (s_left downto s_right) := (others => '0');


begin

  in_proc: process (clk, rst, data_in_nw, data_in_ne, data_in_s)
  begin
    if rst = '1' then
      a <= (others => '0');
      b <= (others => '0');
      c <= (others => '0');
    elsif rising_edge (clk) then
      a <= data_in_nw;
      b <= data_in_ne;
      c <=  data_in_s;
    end if;
  end process;

  -- This is the one relevant part of the processing
  -- node: computing the north output port value.
  m <= a * b;
  s <= c + m;

  out_proc: process (clk, rst, a, b, c, m)
  begin
    if rst = '1' then
      data_out_sw <= (others => '0');
      data_out_se <= (others => '0');
      data_out_n  <= (others => '0');
    elsif rising_edge (clk) then
      data_out_se <= resize(a, data_out_se'left, data_out_se'right);
      data_out_sw <= resize(b, data_out_sw'left, data_out_sw'right);
      data_out_n  <= resize(s,  data_out_n'left,  data_out_n'right);
    end if;
  end process;

end rtl;
