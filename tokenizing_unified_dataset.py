import os
import json
from regex_lexer import CSharpAndCommentsLexer


TOKENS_PER_DATAPOINT = 100
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

        with open(unified_file) as json_file:
            unified_data_dict = json.load(json_file)

        path_to_file = f"""./submodule_repos_to_analyze/{unified_data_dict["Repo"]}/{unified_data_dict["FilePath"]}"""
        with open(path_to_file, 'r') as file:
            orig_file_string = file.read()
        num_lines = orig_file_string.count('\n')
        orig_file_tokens = the_lexer.get_tokens(orig_file_string)
        
        orig_file_line_tokens = [[]]
        idx = 0
        for (token_type, value) in orig_file_tokens:
            orig_file_line_tokens[idx].append((token_type, value))
            if value == "NEWLINE":
                orig_file_line_tokens.append([])
                idx += 1

        # Because lexer always adds NEWLINE at very end
        del orig_file_line_tokens[-1]
        del orig_file_line_tokens[-1][-1]
        assert num_lines == len(orig_file_line_tokens), "num_lines not equal to len(orig_file_line_tokens)"

        # print("tokens first line: ", orig_file_line_tokens[0])
        print("tokens last line: ", orig_file_line_tokens[-1])

        # Diff indices start at 1
        start_required_index = unified_data_dict["RequiredLinesStart"] - 1
        end_required_index = unified_data_dict["RequiredLinesEnd"] - 1
        orig_required_line_tokens = orig_file_line_tokens[start_required_index:end_required_index + 1]
        
        # print("tokens first line: ", orig_required_line_tokens[0])
        # print("tokens last line: ", orig_required_line_tokens[-1])

        orig_required_tokens = []
        for line_tokens in orig_required_line_tokens:
            for token in line_tokens:
                orig_required_tokens.append(token)
        
        if len(orig_required_tokens) > TOKENS_PER_DATAPOINT:
            print("Too many required tokens: ", len(orig_required_tokens))


        # TODO:
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
        

        remove_redundant_fields(unified_data_dict)

        break

        new_filepath = f"{tokenized_dataset_dir}/{unified_file.name}"
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(unified_data_dict, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
