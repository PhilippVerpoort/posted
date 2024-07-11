test_that("normalization works", {
  setwd("../")
  expect_no_error(DataSet$new('Tech|Electrolysis')$normalise())
})
