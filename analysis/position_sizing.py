"""Position sizing — how much to allocate per trade based on portfolio, risk, conviction."""


def calculate_position_size(
    budget: float,
    conviction_score: float,
    current_price: float,
    max_position_pct: float = 0.20,
    min_position_thb: float = 5000,
) -> float:
    """Calculate position size (THB) for a trade.

    Uses conviction-based sizing: higher score = larger allocation,
    capped at max_position_pct of budget.

    Args:
        budget: Available cash (THB)
        conviction_score: Composite score (0 to 100, higher = stronger conviction)
        current_price: Current stock price (for round lot calculation)
        max_position_pct: Maximum % of budget per position (default 20%)
        min_position_thb: Minimum trade size in THB (default 5,000)

    Returns:
        Recommended position size in THB.
    """
    if budget <= 0 or conviction_score <= 0 or current_price <= 0:
        return 0.0

    max_position = budget * max_position_pct

    # Scale position by conviction (30-100 score maps to 30%-100% of max position)
    conviction_factor = max(0.3, min(1.0, conviction_score / 100))
    raw_amount = max_position * conviction_factor

    # Round to nearest lot (SET uses 100-share lots)
    shares = int(raw_amount / current_price / 100) * 100
    amount = shares * current_price

    # Apply minimum
    if amount < min_position_thb:
        return 0.0

    return round(amount, 2)


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Calculate Kelly Criterion for optimal bet sizing.

    f* = (p * b - q) / b
    where p = win rate, q = 1 - p, b = avg_win / avg_loss

    Args:
        win_rate: Historical win rate (0 to 1)
        avg_win: Average winning trade size
        avg_loss: Average losing trade size (positive number)

    Returns:
        Optimal fraction of capital to risk (0 to 1).
    """
    if avg_loss <= 0 or win_rate <= 0:
        return 0.0

    b = avg_win / avg_loss
    q = 1 - win_rate
    kelly = (win_rate * b - q) / b

    # Use half-Kelly for safety
    return max(0.0, min(0.5, kelly / 2))
