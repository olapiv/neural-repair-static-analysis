# SourceCodeTokenizer

**Disclaimer**: Due to the overhead of using Roslyn as a tokenizer when formatting tokens were required as well, the code in this repository is essentially unused. It is replaced by [regex_lexer.py](/regex_lexer.py), as that is faster, easier to understand, easier modifiable and written in Python. This folder is not removed as it still provides some useful code snippets which are helpful to understand how Roslyn works.

This C# solution/project is to tokenize the unified dataset, so that it can be fed into the NN.

The source code is practically forked from [Source Code 'Learning to Represent Edits'](https://github.com/microsoft/msrc-dpu-learning-to-represent-edits) and adjusted to this use-case.
