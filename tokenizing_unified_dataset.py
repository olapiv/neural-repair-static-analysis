import os
import json
from regex_lexer import CSharpAndCommentsLexer


unified_dataset_dir = "unified_dataset"
tokenized_dataset_dir = "tokenized_dataset"


def remove_redundant_fields(data_dict):

    for diagOccurance in data_dict["DiagnosticOccurances"]:
        diagOccurance.pop("Message", None)

    if data_dict["ParsedDiff"]["ActionType"] != "REMOVE":
        data_dict["ParsedDiff"]["Action"].pop("TargetLines", None)

        if data_dict["ParsedDiff"]["ActionType"] != "ADD":
            data_dict["ParsedDiff"]["Action"].pop("TargetStartLocation", None)

    data_dict.pop("Repo", None)
    data_dict.pop("RepoURL", None)
    data_dict.pop("SolutionFile", None)
    data_dict.pop("FilePath", None)
    data_dict.pop("Commit", None)
    data_dict.pop("AnalyzerNuGet", None)
    data_dict.pop("FileContextStart", None)
    data_dict.pop("RequiredLinesStart", None)
    data_dict.pop("RequiredLinesEnd", None)
    # data_dict.pop("FileContext", None)

    return

def main():
    the_lexer = CSharpAndCommentsLexer()

    unified_files = [f for f in os.scandir(
        unified_dataset_dir) if f.is_file()]
    for unified_file in unified_files:
        unified_file.name
        print("unified_file.path: ", unified_file.path)
        with open(unified_file) as json_file:
            unified_file_dict = json.load(json_file)

        print("unified_file_dict: ", unified_file_dict)
        break

        # TODO:
        # 1. Read original file and tokenize all
        # 1. Split between NEWLINE; Get tokens between required lines
        # 1. Exit if too many tokens (>100?)
        # 1. Add additional tokens until 100(?) are reached
        # 1. Subtract line number of file context (offset) from diff src code locations
        # 1. Optional: Index vars
        # ------
        # 1. Apply diff to original file and tokenize all
        # 1. Extract tokens from diff
        # 1. Optional: Index vars
        # ------
        # 1. Tokenize diagnostic message with LanguageLexer
        # 1. Optional: Index vars
        # ------
        # 1. Add Error token...?

        #### Tokenization: ####
        # result = the_lexer.get_tokens(original_file_string)
        # for (token_type, value) in result:
        #     pass

        remove_redundant_fields(unified_file_dict)

        new_filepath = f"{tokenized_dataset_dir}/{unified_file.name}"
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(unified_file_dict, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
