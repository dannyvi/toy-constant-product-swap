
"""
Test Data: x: 100000, y:200, amp: 8000,
"""

N_COINS = 2
A_PRECISION = 100


def get_D(_xp: list, _amp) -> int:
    """
    D invariant calculation in non-overflowing integer operations
    iteratively

    A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

    Converging solution:
    D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
    """
    S = 0
    Dprev = 0

    for _x in _xp:
        S += _x
    if S == 0:
        return 0

    D = S
    Ann = _amp * N_COINS
    for _i in range(255):
        D_P = D
        for _x in _xp:
            D_P = D_P * D // (_x * N_COINS)  # If division by 0, this will be borked: only withdrawal will work. And that is good
        Dprev = D
        D = (Ann * S // A_PRECISION + D_P * N_COINS) * D // ((Ann - A_PRECISION) * D // A_PRECISION + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                return D
        else:
            if Dprev - D <= 1:
                return D
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    raise


def recur_D_origin(d, x, y, s, ann, iter, end):
    d_prev = d
    result = 0
    d_p = d
    d_p = d_p * d // (x * 2)
    d_p = d_p * d // (y * 2)
    new_d = (ann * s // A_PRECISION + d_p * 2) * d // ((ann - A_PRECISION) * d // A_PRECISION + 3 * d_p)
    if d_prev < new_d <= d_prev + 1:
        result = new_d
    if new_d <= d_prev <= new_d + 1:
        result = new_d
    if result == 0:
        return recur_D_origin(new_d, x, y, s, ann, iter + 1, end)
    else:
        return result


def recur_D_improve(d, x, y, s, ann, iter, end):
    d_prev = d
    d = d * d * d // x // y // 4
    new_d = (ann * s // A_PRECISION + d * 2) * d_prev // ((ann - A_PRECISION) * d_prev // A_PRECISION + 3 * d)
    if d_prev < new_d <= d_prev + 1:
        return new_d
    if new_d <= d_prev <= new_d + 1:
        return new_d
    return recur_D_improve(new_d, x, y, s, ann, iter + 1, end)


def get_D_origin(x, y, amp):
    s = x + y
    d, ann, iter, end = s, amp*2, 0, 255
    return recur_D_origin(d, x, y, s, ann, iter, end)


def get_D_improve(x, y, amp):
    s = x + y
    d, ann, iter, end = s, amp*2, 0, 255
    return recur_D_improve(d, x, y, s, ann, iter, end)


def test_get_D():
    r = get_D([101010, 200], 50)
    assert r == 20149, f'error: {r}'
    result = get_D_origin(101010, 200, 50)
    assert result == 20149, f'error: {result}'
    result2 = get_D_improve(101010, 200, 50)
    assert result2 == 20147, f'error: {result2}'
