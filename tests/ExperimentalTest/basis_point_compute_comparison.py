def old_max_px_by_bbbo_basis_point_compute(aggressive_quote_px: float,
                                           max_basis_points: int) -> float:
    return aggressive_quote_px + ((aggressive_quote_px / 100) * (max_basis_points / 100))


def new_max_px_by_bbbo_basis_point_compute(aggressive_quote_px: float,
                                           max_basis_points: int) -> float:
    return aggressive_quote_px + (.01 * (aggressive_quote_px + max_basis_points))


def compare_old_vs_new(aggressive_quote_px: float, max_basis_points: int):
    print("-"*100)
    print(f"{aggressive_quote_px=}, {max_basis_points=}")
    print(f"OLD COMPUTE: {old_max_px_by_bbbo_basis_point_compute(aggressive_quote_px, max_basis_points)}")
    print(f"NEW COMPUTE: {new_max_px_by_bbbo_basis_point_compute(aggressive_quote_px, max_basis_points)}")
    print("-"*100)


# if we are placing buy side order then if:
aggressive_quote_px_ = 90

# then if basis_point is 10, then
compare_old_vs_new(aggressive_quote_px_, max_basis_points=10)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=30)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=50)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=100)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=150)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=200)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=300)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=500)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=1000)

# if we are placing sell side order then if:
aggressive_quote_px_ = 100
compare_old_vs_new(aggressive_quote_px_, max_basis_points=10)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=30)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=50)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=100)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=150)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=200)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=300)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=500)
compare_old_vs_new(aggressive_quote_px_, max_basis_points=1000)