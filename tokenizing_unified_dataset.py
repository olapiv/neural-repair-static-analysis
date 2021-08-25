import os
import json
from multiprocessing import Pool
from itertools import product
from regex_lexer import CSharpAndCommentsLexer, LanguageLexer
from regex_lexer_camelcase import CSharpAndCommentsCamelcaseLexer, LanguageCamelcaseLexer
from enum import Enum
from pathlib import Path


class TokenizationType(Enum):
    standard = "standard"
    camelcase = "camelcase"
    zero_index_vars = "zero_index_vars"


class Pipeline:

    def __init__(self, input_dir, output_dir, num_file_context_tokens, tokenization_type=TokenizationType.standard):
        self.input_dir = input_dir
        self.num_file_context_tokens = num_file_context_tokens
        self.tokenization_type = tokenization_type

        self.output_dir = output_dir

        if self.tokenization_type == TokenizationType.camelcase:
            self.the_lexer = CSharpAndCommentsCamelcaseLexer()
            self.diag_message_lexer = LanguageCamelcaseLexer()
        else:
            self.the_lexer = CSharpAndCommentsLexer()
            self.diag_message_lexer = LanguageLexer()

    def remove_redundant_fields(self, data_dict):

        # for diagOccurance in data_dict["DiagnosticOccurances"]:
        #     diagOccurance.pop("Message", None)

        # if data_dict["ParsedDiff"]["ActionType"] != "REMOVE":
        #     data_dict["ParsedDiff"]["Action"].pop("TargetLines", None)

        #     if data_dict["ParsedDiff"]["ActionType"] != "ADD":
        #         data_dict["ParsedDiff"]["Action"].pop("TargetStartLocation", None)

        data_dict.pop("RepoURL", None)
        data_dict.pop("SolutionFile", None)
        data_dict.pop("FilePath", None)
        data_dict.pop("Commit", None)
        # data_dict.pop("Repo", None)
        # data_dict.pop("AnalyzerNuGet", None)
        # data_dict.pop("FileContextStart", None)
        # data_dict.pop("RequiredLinesStart", None)
        # data_dict.pop("RequiredLinesEnd", None)
        # data_dict.pop("FileContext", None)

        return

    @staticmethod
    def split_tokens_by_line(orig_file_tokens):
        orig_file_line_tokens = [[]]
        idx = 0
        for (token_type, value) in orig_file_tokens:
            orig_file_line_tokens[idx].append((token_type, value))
            if value == "NEWLINE":
                orig_file_line_tokens.append([])
                idx += 1

        return orig_file_line_tokens

    def get_required_tokens(self, all_tokens, start_line, end_line):

        line_tokens = Pipeline.split_tokens_by_line(all_tokens)
        required_line_tokens = line_tokens[start_line:end_line + 1]

        # Flatten tokens again:
        required_tokens = []
        for line_tokens in required_line_tokens:
            for token in line_tokens:
                required_tokens.append(token)

        return required_tokens

    def count_tokens_in_lines(self, all_tokens, start_line, num_lines):
        line_tokens = Pipeline.split_tokens_by_line(
            all_tokens)[start_line:start_line+num_lines]
        num_tokens = 0
        for line in line_tokens:
            num_tokens += len(line)
        return num_tokens

    def add_context_to_tokens(self, all_tokens, core_token_list, core_idx_start, num_total_tokens):

        context_token_list = core_token_list.copy()
        max_idx = len(all_tokens) - 1
        core_idx_end = core_idx_start + len(context_token_list) - 1
        num_tokens_to_add = num_total_tokens - len(context_token_list)

        while num_tokens_to_add > 0:

            if core_idx_start == 0 and core_idx_end == max_idx:
                break

            if not core_idx_end == max_idx and (core_idx_start == 0 or num_tokens_to_add % 2 == 1):
                core_idx_end += 1
                context_token_list.append(all_tokens[core_idx_end])

            # elif core_idx_end == max_idx or num_tokens_to_add % 2 == 0:
            else:
                core_idx_start -= 1
                context_token_list.insert(0, all_tokens[core_idx_start])

            num_tokens_to_add -= 1

        return context_token_list, core_idx_start

    def get_line_number_by_token_idx(self, all_tokens, token_idx):
        line_number = 0
        for idx, token in enumerate(all_tokens):
            if idx == token_idx:
                # token is still part of old line
                break
            if token[1] == "NEWLINE":
                line_number += 1

        return line_number

    def apply_diff_to_file(self, unified_data_dict, orig_file):

        diffed_file_list = orig_file.split("\n")
        diff_action_type = unified_data_dict["ParsedDiff"]["ActionType"]
        diff_action = unified_data_dict["ParsedDiff"]["Action"]

        if diff_action_type == "ADD":

            target_lines = [line.rstrip('\n')
                            for line in diff_action["TargetLines"]]

            # Diff starts at line 1
            prev_idx = diff_action["PreviousSourceLocation"] - 1
            diffed_file_list[prev_idx + 1:prev_idx +
                             1] = target_lines

        elif diff_action_type == "REMOVE":

            start_idx = diff_action["SourceLocationStart"] - 1
            end_idx = diff_action["SourceLocationEnd"] - 1
            idx_to_del = list(range(start_idx, end_idx + 1))
            diffed_file_list = [i for j, i in enumerate(
                diffed_file_list) if j not in idx_to_del]

        else:  # "REPLACE"

            # Remove
            # Diff starts at line 1
            idx_to_del = [i-1 for i in diff_action["SourceLocations"]]
            diffed_file_list = [i for j, i in enumerate(
                diffed_file_list) if j not in idx_to_del]

            # Add
            first_idx = idx_to_del[0]
            target_lines = [line.rstrip('\n')
                            for line in diff_action["TargetLines"]]
            diffed_file_list[first_idx:first_idx] = target_lines

        return "\n".join(diffed_file_list)

    def get_required_target_indices(self, unified_data_dict):

        target_start_idx = -1
        target_end_idx = -1
        diff_action_type = unified_data_dict["ParsedDiff"]["ActionType"]
        diff_action = unified_data_dict["ParsedDiff"]["Action"]
        if diff_action_type == "ADD":

            # Diff line start at 1; target starts 1 after PreviousSourceLocation
            target_start_idx = diff_action["PreviousSourceLocation"] - 1 + 1
            target_end_idx = target_start_idx + \
                len(diff_action["TargetLines"]) - 1

        elif diff_action_type == "REPLACE":

            # Diff line start at 1;
            target_start_idx = diff_action["SourceLocations"][0] - 1
            target_end_idx = target_start_idx + \
                len(diff_action["TargetLines"]) - 1

        else:  # "REMOVE"
            # No target information
            pass

        return target_start_idx, target_end_idx

    def subtract_line_offset(self, unified_data_dict, line_offset):

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

    def run_single_datapoint(self, unified_file_path):

        unified_file_basename = os.path.basename(os.path.normpath(unified_file_path))
        print(f"File to tokenize: {unified_file_basename}")

        with open(unified_file_path, 'r') as file:
            orig_file_string = file.read()
            if not orig_file_string.isascii():
                print("File is not ASCII!")
                return
            unified_data_dict = json.loads(orig_file_string)

        path_to_file = f"""./submodule_repos_to_analyze/{unified_data_dict["Repo"]}/{unified_data_dict["FilePath"]}"""
        with open(path_to_file, 'r') as file:
            orig_file_string = file.read()  # Adds newline at very end
        num_lines = orig_file_string.count('\n')
        orig_file_tokens = [
            result for result in self.the_lexer.get_tokens(orig_file_string)]

        if any(["\n" in token[1] for token in orig_file_tokens]):
            print(
                "Newline tokenized incorrectly! unified_file: {unified_file_basename}")
            exit(0)
            # return

        # Because lexer always adds NEWLINE at very end
        del orig_file_tokens[-1]

        # Sanity check
        # line_tokens = Pipeline.split_tokens_by_line(orig_file_tokens)
        # assert num_lines == len(
        #     line_tokens), f"""num_lines not equal to len(line_tokens); num_lines: {num_lines}; len(
        #     line_tokens): {len(line_tokens)}; file: {unified_data_dict["FileURL"]}"""

        ### Get required original tokens ###

        # Diff indices start at 1
        start_required_idx = unified_data_dict["RequiredLinesStart"] - 1
        end_required_idx = unified_data_dict["RequiredLinesEnd"] - 1

        orig_required_tokens = self.get_required_tokens(
            orig_file_tokens, start_required_idx, end_required_idx)

        if len(orig_required_tokens) > self.num_file_context_tokens:
            print("Too many required tokens: ", len(orig_required_tokens))
            return

        ### Add context to original tokens ###

        start_required_token_idx = self.count_tokens_in_lines(
            orig_file_tokens, 0, start_required_idx)

        orig_padded_tokens, start_padded_token_idx = self.add_context_to_tokens(
            orig_file_tokens, orig_required_tokens, start_required_token_idx, self.num_file_context_tokens)

        assert len(
            orig_padded_tokens) <= self.num_file_context_tokens, f"Too many context tokens: {len(orig_padded_tokens)}"
        assert len(orig_padded_tokens) >= len(
            orig_required_tokens), f"Too few context tokens: {len(orig_padded_tokens)}"

        # Optionally zero-index identifiers
        var_index_dict = {}
        if self.tokenization_type == TokenizationType.zero_index_vars:
            index_func = CSharpAndCommentsLexer.index_identifier_token
            orig_padded_tokens = [index_func(
                token[0], token[1], var_index_dict) for token in orig_padded_tokens]

        unified_data_dict["TokenizedFileContext"] = [token[1]
                                                     for token in orig_padded_tokens]

        ### Apply diff to original file and tokenize all ###

        if unified_data_dict["ParsedDiff"]["ActionType"] != "REMOVE":

            diffed_file_str = self.apply_diff_to_file(
                unified_data_dict, orig_file_string)

            diffed_file_tokens = [
                result for result in self.the_lexer.get_tokens(diffed_file_str)]

            # Because lexer always adds NEWLINE at very end
            del diffed_file_tokens[-1]

            start_target_idx, end_target_idx = self.get_required_target_indices(
                unified_data_dict)
            diffed_required_tokens = self.get_required_tokens(
                diffed_file_tokens, start_target_idx, end_target_idx)

            if any(["\n" in token[1] for token in diffed_required_tokens]):
                print(
                    "Newline tokenized incorrectly! unified_file: {unified_file_basename}")
                exit(0)
                # return

            # Optionally zero-index identifiers
            if self.tokenization_type == TokenizationType.zero_index_vars:
                index_func = CSharpAndCommentsLexer.index_identifier_token
                diffed_required_tokens = [index_func(
                    token[0], token[1], var_index_dict) for token in diffed_required_tokens]

            unified_data_dict["ParsedDiff"]["Action"]["TokenizedTargetLines"] = [
                token[1] for token in diffed_required_tokens]

        ### Tokenize diagnostic message ###

        for diag in unified_data_dict["DiagnosticOccurances"]:
            message_lower = [word.lower() if not word.startswith(
                "'") else word for word in diag["Message"].split(" ")]
            diag_message_tokens = [
                result for result in self.diag_message_lexer.get_tokens(' '.join(message_lower))]

            # Because lexer always adds NEWLINE at very end
            del diag_message_tokens[-1]

            # Optionally zero-index identifiers
            if self.tokenization_type == TokenizationType.zero_index_vars:
                index_func = CSharpAndCommentsLexer.index_identifier_token
                diag_message_tokens = [index_func(
                    token[0], token[1], var_index_dict) for token in diag_message_tokens]

            diag["TokenizedMessage"] = [
                result[1] for result in diag_message_tokens]

        ### Subtract line number of file context (offset) from diff src code locations ###
        start_padded_line_number = self.get_line_number_by_token_idx(
            orig_file_tokens, start_padded_token_idx)
        start_padded_line_number += 1  # In diffs, start counting at line 1
        self.subtract_line_offset(unified_data_dict, start_padded_line_number)
        unified_data_dict["TokenizedFileContextStart"] = start_padded_line_number

        self.remove_redundant_fields(unified_data_dict)

        new_filepath = f"{self.output_dir}/{unified_file_basename}"
        with open(new_filepath, 'w', encoding='utf-8') as f:
            json.dump(unified_data_dict, f, ensure_ascii=False, indent=2)

    @staticmethod
    def start_and_run(unified_file_path, input_dir, output_dir, num_file_context_tokens, tokenization_type):

        pipeline = Pipeline(input_dir, output_dir, num_file_context_tokens, tokenization_type)
        pipeline.run_single_datapoint(unified_file_path)


def main(input_dir, num_file_context_tokens, tokenization_type):

    dataset_version = input_dir.split("_")[-1]
    output_dir = f"tokenized_datasets/{num_file_context_tokens}_tokens__{tokenization_type.value}__{dataset_version}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    unified_files = [f for f in os.scandir(
        input_dir) if f.is_file() and f.name.endswith(".json")]
    already_tokenized_files = [f.name for f in os.scandir(
        output_dir) if f.is_file()]
    unified_files_to_do = [f.path for f in unified_files if f.name not in already_tokenized_files]

    print(f"Num unified files: {len(unified_files)}")
    print(f"Num unified files left to do: {len(unified_files_to_do)}")

    args = product(unified_files_to_do, [input_dir], [output_dir], [num_file_context_tokens], [tokenization_type])

    with Pool(6) as p:
        p.starmap(Pipeline.start_and_run, args)


if __name__ == '__main__':

    num_file_context_tokens = 115
    tokenization_type = TokenizationType.camelcase
    input_dir = "unified_dataset_3"

    main(input_dir, num_file_context_tokens, tokenization_type)
