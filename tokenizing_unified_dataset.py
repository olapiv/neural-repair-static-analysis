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


def split_tokens_by_line(orig_file_tokens):
    orig_file_line_tokens = [[]]
    idx = 0
    for (token_type, value) in orig_file_tokens:
        orig_file_line_tokens[idx].append((token_type, value))
        if value == "NEWLINE":
            orig_file_line_tokens.append([])
            idx += 1

    return orig_file_line_tokens


def get_required_tokens(all_tokens, start_line, end_line):
    line_tokens = split_tokens_by_line(all_tokens)
    required_line_tokens = line_tokens[start_line:end_line + 1]

    # Flatten tokens again:
    required_tokens = []
    for line_tokens in required_line_tokens:
        for token in line_tokens:
            required_tokens.append(token)

    return required_tokens


def count_tokens_in_lines(all_tokens, start_line, num_lines):
    line_tokens = split_tokens_by_line(
        all_tokens)[start_line:start_line+num_lines]
    num_tokens = 0
    for line in line_tokens:
        num_tokens += len(line)
    return num_tokens


def add_context_to_tokens(all_tokens, core_token_list, core_idx_start, num_total_tokens=TOKENS_PER_DATAPOINT):

    context_token_list = core_token_list.copy()
    max_idx = len(all_tokens) - 1
    core_idx_end = core_idx_start + len(context_token_list)
    num_tokens_to_add = num_total_tokens - len(context_token_list)

    while num_tokens_to_add > 0:

        if core_idx_start == 0 and core_idx_end == max_idx:
            break

        if core_idx_start == 0 or num_tokens_to_add % 2 == 1:
            core_idx_end += 1
            context_token_list.append(all_tokens[core_idx_end])

        # elif core_idx_end == max_idx or num_tokens_to_add % 2 == 0:
        else:
            core_idx_start -= 1
            context_token_list.insert(0, all_tokens[core_idx_start])

        num_tokens_to_add -= 1

    return context_token_list, core_idx_start


def get_line_number_by_token_idx(all_tokens, token_idx):
    line_number = 0
    for idx, token in enumerate(all_tokens):
        if idx == token_idx:
            # token is still part of old line
            break
        if token[1] == "NEWLINE":
            line_number += 1

    return line_number


def subtract_line_offset(unified_data_dict, line_offset):

    for diag_occurance in unified_data_dict["DiagnosticOccurances"]:
        diag_occurance["Line"] -= line_offset

    diff_action_type = unified_data_dict["ParsedDiff"]["ActionType"]
    diff_action = unified_data_dict["ParsedDiff"]["Action"]

    if diff_action_type == "ADD":
        diff_action["PreviousSourceLocation"] -= line_offset
    elif diff_action_type == "REPLACE":
        diff_action["SourceLocations"] = [
            loc - line_offset for loc in diff_action["SourceLocations"]]
    else:  # "REMOVE"
        diff_action["SourceLocationStart"] -= line_offset
        diff_action["SourceLocationEnd"] -= line_offset


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
        orig_file_tokens = [
            result for result in the_lexer.get_tokens(orig_file_string)]

        # Because lexer always adds NEWLINE at very end
        del orig_file_tokens[-1]

        # Sanity check
        line_tokens = split_tokens_by_line(orig_file_tokens)
        assert num_lines == len(
            line_tokens), "num_lines not equal to len(line_tokens)"

        ### Get required original tokens ###

        # Diff indices start at 1
        start_required_idx = unified_data_dict["RequiredLinesStart"] - 1
        end_required_idx = unified_data_dict["RequiredLinesEnd"] - 1

        orig_required_tokens = get_required_tokens(
            orig_file_tokens, start_required_idx, end_required_idx)

        if len(orig_required_tokens) > TOKENS_PER_DATAPOINT:
            print("Too many required tokens: ", len(orig_required_tokens))
            continue

        ### Add context to original tokens ###

        start_required_token_idx = count_tokens_in_lines(
            orig_file_tokens, 0, start_required_idx)
        orig_padded_tokens, start_padded_token_idx = add_context_to_tokens(
            orig_file_tokens, orig_required_tokens, start_required_token_idx)
        assert len(
            orig_padded_tokens) <= TOKENS_PER_DATAPOINT, f"Too many context tokens: {len(orig_padded_tokens)}"
        assert len(orig_padded_tokens) >= len(
            orig_required_tokens), f"Too few context tokens: {len(orig_padded_tokens)}"
        unified_data_dict["TokenizedFileContext"] = [token[1] for token in orig_padded_tokens]

        ### Subtract line number of file context (offset) from diff src code locations ###
        start_padded_line_number = get_line_number_by_token_idx(
            orig_file_tokens, start_padded_token_idx)
        subtract_line_offset(unified_data_dict, start_padded_line_number)

        # TODO:
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

        print(json.dumps(unified_data_dict, indent=2))

        break

        new_filepath = f"{tokenized_dataset_dir}/{unified_file.name}"
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(unified_data_dict, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
