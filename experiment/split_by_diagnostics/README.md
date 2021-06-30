# Final Dataset & Corresponding Results

## Dataset

* Dataset & metadata files generated with [finalize_tokenized_dataset.py](/finalize_tokenized_dataset.py)
* Measuring **Extrapolation Behaviour**: Training-, validation- and test-set have unique sets of diagnostics
  * train_perc = 70% of diagnostics
  * val_perc = 20% of diagnostics
  * test_perc = 10% of diagnostics
* Variable names / identifiers are *not* indexed
* Train, val & test dataset are *randomly* chosen from aggregate dataset
* See metadata files for further information on data
* Max number of FILE_CONTENT tokens in input (required lines + context): 100
