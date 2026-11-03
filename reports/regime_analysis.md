# Filtered Markov-switching regime analysis

Zero-mean Gaussian observations; states reordered by ascending variance on every training-window refit. Forecast probabilities equal filtered probabilities multiplied by the estimated row-stochastic transition matrix. No full-sample smoothed states enter the forecasting path. EM initialization may smooth within the permissible training window only.

State shares and transitions below describe the fitted filter. They are not latent-state classification accuracy. Near-boundary transitions, weak occupancy and insufficient variance separation remain visible as fit warnings.

| asset | model | period | origins | high state share | classification changes | mean variance ratio |
|---|---|---|---|---|---|---|
| NIFTY50_TRI | markov_switching_2 | development | 1,477 | 0.1496 | 61 | 8.2179 |
| NIFTY50_TRI | markov_switching_2 | validation | 743 | 0.0700 | 22 | 12.0431 |
| SPY | markov_switching_2 | development | 2,016 | 0.3393 | 166 | 8.1135 |
| SPY | markov_switching_2 | validation | 753 | 0.2895 | 49 | 7.9923 |
| VT | markov_switching_2 | development | 2,016 | 0.3433 | 158 | 7.3844 |
| VT | markov_switching_2 | validation | 753 | 0.1846 | 56 | 8.1330 |

Refits may change classifications and state variances discontinuously. Inspect `fits.parquet` for transition estimates, expected durations, convergence attempts and boundary flags; `regime_probabilities.csv` records saved origin-time states.

[statsmodels MarkovRegression documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html)
