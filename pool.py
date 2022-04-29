from enum import Enum
import math


class TokenError(Exception):
    """"""


class LiquidityError(Exception):
    """"""


class TransactionError(Exception):
    """"""


class TokenType(str, Enum):
    """"""


class SwapTokenType(TokenType):
    BTC = 'BTC'
    USDC = 'USDC'


class LpTokenType(TokenType):
    LP = 'LP'


class Token:
    def __init__(self, token_type: TokenType, amount: float):
        """The data type which takes along the transfer infomation."""
        if amount <= 0:
            raise TokenError('Should be larger than 0.')
        self.type = token_type
        self.amt = amount

    def __repr__(self):
        return f'Token({self.type}): {self.amt}'


class LpToken(Token):
    def __init__(self, token_type: LpTokenType, amount: float):
        super().__init__(token_type, amount)


class SwapToken(Token):
    def __init__(self, token_type: SwapTokenType, amount: float):
        super().__init__(token_type, amount)

    def is_btc(self):
        return True if self.type == SwapTokenType.BTC else False

    def assert_btc(self):
        if self.type != SwapTokenType.BTC:
            raise TransactionError('Must be BTC')

    def assert_usdc(self):
        if self.type != SwapTokenType.USDC:
            raise TransactionError('Must be USDC')

    def counter_type(self):
        return TokenType.BTC if self.type == TokenType.USDC else TokenType.USDC


class ConstantProductPool:
    """A trading venue for BTC & USDC tokens."""
    LIQUIDITY_PRECISION = 1e-7
    FEE_RATE = 0.003

    def __init__(self, liquidity_btc: SwapToken, liquidity_usdc: SwapToken):
        """Declare an initial state of liquidity swap.

        We take btc and usdc in the params as convension,
        and fixed LP token numbers.
        """
        liquidity_btc.assert_btc()
        liquidity_usdc.assert_usdc()
        self._btc_amt = liquidity_btc.amt
        self._usdc_amt = liquidity_usdc.amt
        self._refresh_product()
        self._lp_amt = self._btc_amt + self._usdc_amt

    def _refresh_product(self):
        self._product = self._btc_amt * self._usdc_amt

    def _ident_type(self, token: SwapToken):
        return SwapTokenType.BTC if token.is_btc() else SwapTokenType.USDC

    def _ident_total(self, token: SwapToken):
        return self._btc_amt if token.is_btc() else self._usdc_amt

    def _contrary_type(self, token: SwapToken):
        return SwapTokenType.USDC if token.is_btc() else SwapTokenType.BTC

    def _contrary_total(self, token: SwapToken):
        return self._usdc_amt if token.is_btc() else self._btc_amt

    def _validate_current_product(self):
        if not math.isclose(self._btc_amt * self._usdc_amt, self._product, rel_tol=self.LIQUIDITY_PRECISION):
            raise LiquidityError('Product value was wrong')

    def _balance_liquidity(self, liq_btc: SwapToken, liq_usdc: SwapToken) -> LpToken:
        """"""
        raise NotImplementedError

    def deposit_liquidity(self, liq_btc: SwapToken, liq_usdc: SwapToken) -> LpToken:
        """
        Deposit liquidityA and liquidityB into the pool, and return the corresponding LP token

        """
        liq_btc.assert_btc()
        liq_usdc.assert_usdc()
        blanced_btc_token, balanced_usdc_token = self._balance_liquidity(liq_btc, liq_usdc)
        return self.deposit_balanced_liquidity(blanced_btc_token, balanced_usdc_token)

    def get_balanced_contrary_liquidity(self, liq_btc: SwapToken) -> SwapToken:
        """Give the balanced contrary token of the swap helps the LP to deposit liquidity."""
        balanced_amt = liq_btc.amt * self._usdc_amt / self._btc_amt
        return SwapToken(SwapTokenType.USDC, balanced_amt)

    def deposit_balanced_liquidity(self, balanced_btc: SwapToken, balanced_usdc: SwapToken) -> LpToken:
        """"""
        incremented_btc_prop = balanced_btc.amt / self._btc_amt
        incremented_usdc_prop = balanced_usdc.amt / self._usdc_amt
        assert math.isclose(incremented_btc_prop, incremented_usdc_prop, rel_tol=self.LIQUIDITY_PRECISION),\
            "Deposit liquidity not balanced"
        incremental_prop = incremented_btc_prop
        incremental_lp_amt = incremental_prop * self._lp_amt
        # Transactional
        # Increase liquidity, refresh Product, mint LpToken
        self._btc_amt += balanced_btc.amt
        self._usdc_amt += balanced_usdc.amt
        self._refresh_product()
        self._lp_amt += incremental_lp_amt
        token = LpToken(LpTokenType.LP, incremental_lp_amt)
        return token

    def withdraw_liquidity(self, lp_token: LpToken) -> (SwapToken, SwapToken):
        """
        Burn the lp token, and return the corresponding amount of liquidityA and liquidityB
        - i.e. return (Token, Token)
        """
        if lp_token.amt >= self._lp_amt:
            raise TransactionError('Token amount beyond the total liquidity')
        prop = lp_token.amt / self._lp_amt                                # get the shares of token
        btc_amt, usdc_amt = self._btc_amt * prop, self._usdc_amt * prop   # get withdraw amt of currencies
        # transactional
        # mint btc, usdc, burn lp, update pool state, _btc_amt, _usdc_amt, _K
        btc_token, usdc_token = SwapToken(SwapTokenType.BTC, btc_amt), SwapToken(SwapTokenType.USDC, usdc_amt)
        self._lp_amt -= lp_token.amt
        self._btc_amt -= btc_amt
        self._usdc_amt -= usdc_amt
        self._refresh_product()
        return btc_token, usdc_token

    def swap(self, paid_token: SwapToken):
        """
        Should alter state of the pool, and return the other token. E.g.
        - if paidToken is typeA, return a Token object of typeB
        - if paidToken is typeB, return a Token object of typeA
        """
        id_type, id_total, new_id_total, cont_type, cont_total, new_cont_total, cash_amt = self._forecast_swap(paid_token)
        # Transactional，
        # Update new pool token amt, validate product, and mint cash Token.
        if paid_token.is_btc():
            btc_amt, usdc_amt = new_id_total, new_cont_total
        else:
            btc_amt, usdc_amt = new_cont_total, new_id_total
        self._btc_amt, self._usdc_amt = btc_amt, usdc_amt
        self._validate_current_product()
        # withhold 0.3% in the pool
        mint_amt = cash_amt * (1 - self.FEE_RATE)
        token = SwapToken(cont_type, mint_amt)          # mint
        return token

    def get_price(self, paid_token: SwapToken):
        """"""
        _, _, _, _, _, _, amt_to_be_cashed = self._forecast_swap(paid_token)
        return paid_token.amt / amt_to_be_cashed

    def _forecast_swap(self, paid_token: SwapToken):
        """Helper function that calculates the states transfered within the swap proc."""
        self._validate_current_product()
        ident_type, ident_total = self._ident_type(paid_token), self._ident_total(paid_token)
        contrary_type, contrary_total = self._contrary_type(paid_token), self._contrary_total(paid_token)
        if paid_token.amt >= ident_total:
            raise TransactionError('Token amount of currency was too large.')
        ident_total_after_paid = ident_total + paid_token.amt
        contrary_total_after_paid = self._product / ident_total_after_paid
        cashed_token_amt = contrary_total - contrary_total_after_paid
        return (
            ident_type, ident_total, ident_total_after_paid,
            contrary_type, contrary_total, contrary_total_after_paid,
            cashed_token_amt
        )

    def get_price_impact(self, paid_token: SwapToken):
        """"""
        _, id_total, new_id_total, _, cont_total, new_cont_total, _ = self._forecast_swap(paid_token)
        pre_trade_price = id_total / cont_total
        post_trade_price = new_id_total / new_cont_total
        impact = abs(post_trade_price - pre_trade_price) / pre_trade_price
        return impact
