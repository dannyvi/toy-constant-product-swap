import unittest
from pool import LpToken, LpTokenType, SwapToken, SwapTokenType, ConstantProductPool


class TestConstantProductPool(unittest.TestCase):

    def setUp(self) -> None:
        initial_btc = SwapToken(SwapTokenType.BTC, 10.0)
        initial_usdc = SwapToken(SwapTokenType.USDC, 40.0)
        self.pool = ConstantProductPool(initial_btc, initial_usdc)

    def assert_pool_state(self, btc_amt, usdc_amt, product, lp_amt):
        self.assertAlmostEqual(self.pool._btc_amt, btc_amt)
        self.assertAlmostEqual(self.pool._usdc_amt, usdc_amt)
        self.assertAlmostEqual(self.pool._product, product)
        self.assertAlmostEqual(self.pool._lp_amt, lp_amt)

    def test_pool_initial_state(self):
        self.assert_pool_state(10.0, 40.0, 400.0, 50.0)

    def test_deposit_liquidity_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            btc_token = SwapToken(SwapTokenType.BTC, 2.0)
            usdc_token = SwapToken(SwapTokenType.USDC, 6.0)
            self.pool.deposit_liquidity(btc_token, usdc_token)

    def test_deposit_liquidity_balanced(self):
        btc_token = SwapToken(SwapTokenType.BTC, 2.0)
        usdc_token = self.pool.get_balanced_contrary_liquidity(btc_token)
        self.assertAlmostEqual(usdc_token.amt, 8.0)
        lp_token = self.pool.deposit_balanced_liquidity(btc_token, usdc_token)
        self.assertAlmostEqual(lp_token.amt, 10.0)
        self.assert_pool_state(12.0, 48.0, 12.0 * 48.0, 60.0)

    def test_withdraw_liquidity(self):
        lp_token = LpToken(LpTokenType.LP, 5.0)
        btc_token, usdc_token = self.pool.withdraw_liquidity(lp_token)
        self.assertAlmostEqual(btc_token.amt, 1.0)
        self.assertAlmostEqual(usdc_token.amt, 4.0)
        self.assert_pool_state(9.0, 36.0, 9.0 * 36.0, 45.0)

    def test_swap(self):
        usdc_token = SwapToken(SwapTokenType.USDC, 10.0)
        self.assertAlmostEqual(self.pool._product, 400.0)
        btc_token = self.pool.swap(usdc_token)
        self.assertAlmostEqual(btc_token.amt, 2 - 0.006)
        self.assert_pool_state(8.0, 50.0, 400.0, 50.0)
        # continuous trading
        lp_token = LpToken(LpTokenType.LP, 5.0)
        btc_token, usdc_token = self.pool.withdraw_liquidity(lp_token)
        self.assertAlmostEqual(btc_token.amt, 0.8)
        self.assertAlmostEqual(usdc_token.amt, 5.0)
        self.assert_pool_state(7.2, 45.0, 7.2 * 45.0, 45.0)    # product changed to 324.00, decremented by LP withdraw

    def test_price_and_impact(self):
        btc_token = SwapToken(SwapTokenType.USDC, 10)
        price = self.pool.get_price(btc_token)
        self.assertAlmostEqual(price, 5.0)
        impact = self.pool.get_price_impact(btc_token)
        self.assertAlmostEqual(impact, 0.5625)                 # The price raised 56.25%
