# run_plumber.R
pr <- plumber::plumb('app.R')
pr$run(host = '0.0.0.0', port = 8000)