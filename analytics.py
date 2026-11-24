
"""
CarePlus - Probability and Statistics Module

Calculates descriptive statistics and Pearson correlation
from real user research and usability testing data.
"""

from statistics import mean, median, multimode, stdev
from math import sqrt


def descriptive_statistics(values):
    """Calculate descriptive statistics for numerical data."""

    if not values:
        raise ValueError("At least one numerical value is required.")

    numbers = [float(value) for value in values]

    result = {
        "count": len(numbers),
        "mean": mean(numbers),
        "median": median(numbers),
        "mode": multimode(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers),
        "range": max(numbers) - min(numbers),
        "standard_deviation": (
            stdev(numbers) if len(numbers) >= 2 else None
        )
    }

    return result


def pearson_correlation(x_values, y_values):
    """Calculate Pearson correlation coefficient."""

    if len(x_values) != len(y_values):
        raise ValueError("Both lists must have equal length.")

    if len(x_values) < 2:
        raise ValueError("At least two paired observations are required.")

    x = [float(value) for value in x_values]
    y = [float(value) for value in y_values]

    x_mean = mean(x)
    y_mean = mean(y)

    numerator = sum(
        (a - x_mean) * (b - y_mean)
        for a, b in zip(x, y)
    )

    denominator = sqrt(
        sum((a - x_mean) ** 2 for a in x)
        *
        sum((b - y_mean) ** 2 for b in y)
    )

    if denominator == 0:
        raise ValueError("Correlation cannot be calculated for constant data.")

    return numerator / denominator
