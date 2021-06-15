"""
This file unifies the fixes and the analysis made by Roslynator into single datapoints.

"""

import xml.etree.ElementTree as ET
import json
import os
import urllib.request
from unidiff import PatchSet, PatchedFile
import pandas as pd
import hashlib
import copy
from parsing_diffs import parse_hunk


diff_dir = "raw_dataset/diffs"
analysis_dir = "raw_dataset/analysis_files"
unified_dataset_dir = "unified_dataset"
repositories_dir = "submodule_repos_to_analyze"


df_repos = pd.read_csv("github_repos.csv")
analysis_files = [f.name for f in os.scandir(
    analysis_dir) if f.is_file() and not f.name == ".DS_Store"]
unified_data_files = [f.name.split("-")[0] for f in os.scandir(
    unified_dataset_dir) if f.is_file()]

# Instantiate this multiple times later:
unified_data_sample = {
    "Repo": "",
    "RepoURL": "",
    "SolutionFile": "",
    "FilePath": "",
    "NumberFileLines": "",
    "Commit": "",
    "FileURL": "",
    "DiagnosticID": "",
    "AnalyzerNuGet": "",
    "Severity": "",
    "RequiredLinesStart": None,
    "RequiredLinesEnd": None,
    "DiagnosticOccurances": [
        # {
        #     "Message": "",
        #     "Line": 0,
        #     "Character": 0
        # },
    ],
    "ParsedDiff": {
        "ReplacedLines": [
            # {
            #     "SourceLocations": [4, 5],
            #     "TargetLines": ["static int i = 0;"]
            # }
        ],
        "RemovedLines": [],
        "AddedLines": [
            # {
            #     "TargetStartLocation": 34,
            #     "TargetLines": ["static int i = 0;"]
            # }
        ]
    },
    "FileContextStart": None,
    "FileContext": [],
}


def hash_filename(filename):
    """Using hash function to avoid OS Errors, too  long filename"""
    return f"{str(int(hashlib.sha256(filename.encode('utf-8')).hexdigest(), 16) % 10**8)}"


def filter_analysis_files(repo_name, solution_filename, nuget_full_name):

    def filter_func(analysis_filename):
        """
        $ANALYSIS_FILEPATH = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}.xml"

        Sample ANALYSIS_FILEPATH:
        raw_dataset\analysis_files\runtime__Common.Tests.sln__dcf816579c616e1d172d587301a0a769aa1c0771__AkzenteIT.Analyzers.1.0.6304.37642.xml

        Disregarding LAST_COMMIT for now.
        """
        REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME = analysis_filename[:-len(
            '.xml')].split("__")
        if repo_name == REPO_NAME and solution_filename == SOLUTION_FILENAME and nuget_full_name == NUGET_FULL_NAME:
            return True
        else:
            return False

    return filter_func


def filter_diagnostic_occurance(new_occurance_dict):
    def filter_func(existing_occurance_dict):
        if (
            existing_occurance_dict["Message"] == new_occurance_dict["Message"] and
            existing_occurance_dict["Line"] == new_occurance_dict["Line"] and
            existing_occurance_dict["Character"] == new_occurance_dict["Character"]
        ):
            return True
        return False
    return filter_func


def match_diff_batches_to_diagnostics(diagnostics, all_added_lines, all_removed_lines, all_replaced_lines):
    """
        To which diff-batch does each diagnostic correspond to?
        In some cases, multiple diagnostic occurances may have generated
        one "diff batch". An example would be two occurances in the same line,
        but at different characters. If the line was deleted in the diff, we would
        not know which diagnostic occurance caused this to happen. Therefore,
        these occurances are bundled. 
        One diagnostic occurance can however only have generated a single 
        diff batch. The assumption is that this diff batch will be "at the same
        line" as the diagnostic occurance. This however also has shortcomings
        for multi-line diffs (they will be split up).

        WARNING: Very hacky code. Trying to align diff batches with diagnostics, which is very speculative.

        Diagnostics that result in multiple diff batches are not handled well; the diff batches will be
        split up, since one datapoint can only have one diff batch.

        IRL, it would actually make sense that one diagnostic has multiple 
        diff batches and not the other way around...
    """

    add_batch_is_above_diagnostic_position = {}
    diff_batch_to_diagnostics = {}
    for diagnostic_occurance in unique_diagnostic_occurances:

        diff_key = None
        for count, value in enumerate(all_replaced_lines):
            if diagnostic_occurance["Line"] in value["SourceLocations"]:
                diff_key = f"REPLACE-{count}"
                break

        if not diff_key:
            for count, value in enumerate(all_removed_lines):
                if (diagnostic_occurance["Line"] >= value["SourceLocationStart"] and
                        diagnostic_occurance["Line"] <= value["SourceLocationEnd"]):
                    diff_key = f"REMOVE-{count}"
                    break

        # Do added_lines last, since intuitively, finding deleted lines is easier; diagnostic
        # will probably be inside one of the deleted/replaced lines?
        # Adding lines on the other hand is evenly likely to happen before
        # or after the diagnostic. Here we are prioritising ADD batches that happen above
        # the diagnostics, unless these already have diagnostics above them.

        if not diff_key:
            for count, value in enumerate(all_added_lines):
                # If added lines are above diagnostic
                if (diagnostic_occurance["Line"] - 1) == value["PreviousSourceLocation"]:
                    diff_key = f"ADD-{count}"

                    # If a ADD diff batch already has diagnostics above it, then it more
                    # likely to find the correct diff batch underneath the current diagnostic.
                    if diff_key in add_batch_is_above_diagnostic_position:
                        if not add_batch_is_above_diagnostic_position[diff_key]:
                            diff_key = None
                            continue
                    else:
                        add_batch_is_above_diagnostic_position[diff_key] = True

                    break

        if not diff_key:
            for count, value in enumerate(all_added_lines):
                # If added lines are beneath diagnostic
                if diagnostic_occurance["Line"] == value["PreviousSourceLocation"]:
                    diff_key = f"ADD-{count}"
                    add_batch_is_above_diagnostic_position[diff_key] = False
                    break

        # Diagnostic occurance leads to no obvious diff batch
        if not diff_key:
            continue

        if diff_key not in diff_batch_to_diagnostics:
            diff_batch_to_diagnostics[diff_key] = []
        diff_batch_to_diagnostics[diff_key].append(
            diagnostic_occurance)

    return diff_batch_to_diagnostics


diff_files = [f.name for f in os.scandir(diff_dir) if f.is_file()]
for diff_file in diff_files:

    print("diff_file: ", diff_file)

    # $ANALYSIS_FILEPATH = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}__${DIAGNOSTIC_ID}.diff"
    REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME, DIAGNOSTIC_ID = diff_file[:-len(
        '.diff')].split("__")

    # Prepare XML analysis file
    analysis_file_for_diff = list(filter(filter_analysis_files(
        REPO_NAME, SOLUTION_FILENAME, NUGET_FULL_NAME), analysis_files))
    print("analysis_file_for_diff: ", analysis_file_for_diff)
    if len(analysis_file_for_diff) != 1:
        print("More than one analysis_file_for_diff!")
        # input("Press Enter to continue...")
    analysis_file_for_diff = analysis_file_for_diff[0]
    # Generated by Roslynator as 'Filepath'
    analyzed_file_prefix = f"C:\\Users\\vlohse\Desktop\\neural-repair-static-analysis\\submodule_repos_to_analyze\\{REPO_NAME}\\"

    tree = ET.parse(f"{analysis_dir}/{analysis_file_for_diff}")
    root = tree.getroot()  # <Roslynator></Roslynator> is root
    projects_analysed = root.find('CodeAnalysis').find('Projects')

    patch_set = PatchSet.from_filename(f"{diff_dir}/{diff_file}")

    repo_dir = f"{repositories_dir}/{REPO_NAME}"

    # One patch per file
    for patched_file in patch_set:
        if patched_file.is_added_file or patched_file.is_removed_file:
            continue

        print("patched_file.path: ", patched_file.path)

        parsed_file_path = patched_file.path.replace(
            "/", "--").replace("\\", "--")
        unified_data_filename = f"{diff_file[:-len('.diff')]}__{parsed_file_path}"
        unified_data_filename_hash = f"{hash_filename(unified_data_filename)}"
        if unified_data_filename_hash in unified_data_files:
            print(
                f"unified_data_filename_hash already exists! file: {unified_data_filename}")
            # Appending unified_data_filename_hash to unified_data_files later on
            continue

        unified_data_file = copy.deepcopy(unified_data_sample)

        repo_row = df_repos.loc[df_repos['RepoName'] == REPO_NAME].iloc[0]

        unified_data_file["Repo"] = REPO_NAME
        unified_data_file["RepoURL"] = repo_row["RepoURL"]
        unified_data_file["SolutionFile"] = SOLUTION_FILENAME
        unified_data_file["FilePath"] = patched_file.path
        unified_data_file["Commit"] = LAST_COMMIT
        unified_data_file["DiagnosticID"] = DIAGNOSTIC_ID
        unified_data_file["AnalyzerNuGet"] = NUGET_FULL_NAME

        repo_url = repo_row["RepoURL"]
        if "https://github.com" in repo_url:
            repo_url = repo_url[:-len('.git')
                                ] if repo_url.endswith('.git') else repo_url
            unified_data_file["FileURL"] = f"{repo_url}/blob/{LAST_COMMIT}/{patched_file.path}"

        try:
            with open(f"{repo_dir}/{patched_file.path}") as f:
                unified_data_file["NumberFileLines"] = len(list(f))
        except UnicodeDecodeError as e:
            print(f"Error reading file: {repo_dir}/{patched_file.path}; Error: {e}")
            continue

        all_replaced_lines = []
        all_added_lines = []
        all_removed_lines = []
        for hunk in patched_file:
            replaced_lines, added_lines, removed_lines = parse_hunk(hunk)
            all_replaced_lines += replaced_lines
            all_added_lines += added_lines
            all_removed_lines += removed_lines

        count = 0
        project_filepaths = []
        unique_diagnostic_occurances = []
        for xml_project in projects_analysed:

            # TODO: Check whether some analysis is based on target framework
            # Occasionally, Roslynator may perform the same analysis multiple times (due to multiple target frameworks in sln file, etc.)
            cs_proj_path = xml_project.get('FilePath')
            if cs_proj_path in project_filepaths:
                print(
                    f"This .csproj has been analysed multiple times! cs_proj_path: {cs_proj_path}")
                continue
            else:
                project_filepaths.append(cs_proj_path)

            for xml_diagnostic in xml_project.find('Diagnostics'):

                if not hasattr(xml_diagnostic.find('FilePath'), 'text'):
                    # Happens rarely. Example:
                    # CA9998; FxCopAnalyzers package has been deprecated in favor of 'Microsoft.CodeAnalysis.NetAnalyzers'

                    # Cannot be sure that this diagnostic led to fix in our file
                    continue

                analyzed_file_filepath = xml_diagnostic.find(
                    'FilePath').text[len(analyzed_file_prefix):].replace("\\", "/")

                if xml_diagnostic.get('Id') != DIAGNOSTIC_ID or analyzed_file_filepath != patched_file.path:
                    continue

                # Just do this once
                if count == 0:
                    unified_data_file["Severity"] = xml_diagnostic.find(
                        'Severity').text
                    count += 1

                new_occurance_dict = {
                    "Message": xml_diagnostic.find('Message').text,
                    "Line": int(xml_diagnostic.find('Location').get('Line')),
                    "Character": int(xml_diagnostic.find('Location').get('Character'))
                }

                # Even though already checking for .csproj duplicates earlier, one file may be referenced
                # in multiple different projects as well.
                # Example: SA1642 for <Location Line="55" Character="16" /> in analysis file
                # Druntime__Microsoft.Bcl.AsyncInterfaces.sln__e98d043d7d293c88a346b632d8fc12564a8ef0ce__Documentation.Analyser.1.1.1.xml
                occurance_duplicates = filter(filter_diagnostic_occurance(
                    new_occurance_dict), unique_diagnostic_occurances)
                if len(list(occurance_duplicates)) != 0:
                    print(
                        f"Duplicate DiagnosticOccurance! new_occurance_dict: {new_occurance_dict}")
                    # input("Press Enter to continue...")
                    continue

                unique_diagnostic_occurances.append(new_occurance_dict)

        num_diff_batches_in_file = len(
            all_replaced_lines) + len(all_removed_lines) + len(all_added_lines)
        num_diagnostics = len(unique_diagnostic_occurances)
        if num_diff_batches_in_file != num_diagnostics:
            print(
                f"Num diff batches ({num_diff_batches_in_file}) != diagnostics ({num_diagnostics})")

        diff_batch_to_diagnostic_occurances_dict = match_diff_batches_to_diagnostics(
            unique_diagnostic_occurances, all_added_lines, all_removed_lines, all_replaced_lines)

        num_diff_datapoint = 0
        # Creating one datapoint per diff action (add/delete/replace)
        for key, value in diff_batch_to_diagnostic_occurances_dict.items():

            # TODO: Comment this out for full dataset
            # For a more heterogenuous dataset
            if num_diff_datapoint > 3:
                continue

            unified_data = copy.deepcopy(unified_data_file)
            unified_data["DiagnosticOccurances"] = value

            diff_action, action_num = key.split("-")
            unified_data["ParsedDiff"] = {}
            unified_data["ParsedDiff"]["ActionType"] = diff_action
            if diff_action == "REPLACE":
                unified_data["ParsedDiff"]["Action"] = all_replaced_lines[int(
                    action_num)]
            elif diff_action == "ADD":
                unified_data["ParsedDiff"]["Action"] = all_added_lines[int(
                    action_num)]
            elif diff_action == "REMOVE":
                unified_data["ParsedDiff"]["Action"] = all_removed_lines[int(
                    action_num)]

            # Find range of lines that are required to be inside FileContext

            diag_occurance_lines = [diag_occurance["Line"]
                                    for diag_occurance in value]
            # Roslynator & diff hunks start at index 1
            first_diag_line = min(diag_occurance_lines)
            # Roslynator & diff hunks start at index 1
            last_diag_line = max(diag_occurance_lines)

            # Take into account that all deleted lines have to be in FileContext as well
            first_diff_line = None
            last_diff_line = None
            actionType = unified_data["ParsedDiff"]["ActionType"]
            if actionType == "REPLACE":
                first_diff_line = unified_data["ParsedDiff"]["Action"]["SourceLocations"][0]
                last_diff_line = unified_data["ParsedDiff"]["Action"]["SourceLocations"][-1]
            elif actionType == "ADD":
                first_diff_line = unified_data["ParsedDiff"]["Action"]["PreviousSourceLocation"]
            else:  # actionType == REMOVE
                first_diff_line = unified_data["ParsedDiff"]["Action"]["SourceLocationStart"]
                last_diff_line = unified_data["ParsedDiff"]["Action"]["SourceLocationEnd"]

            first_required_line = min(first_diag_line, first_diff_line)
            last_required_line = max(
                last_diag_line, last_diff_line) if last_diff_line else last_diag_line

            unified_data["RequiredLinesStart"] = first_required_line
            unified_data["RequiredLinesEnd"] = last_required_line

            # Add context around required lines. This is only for intermediate readability
            # since context is added later as a fixed amount of tokens.

            LINE_DELTA = 3

            if first_diag_line > LINE_DELTA:
                starting_line = first_required_line - LINE_DELTA
            else:
                starting_line = 1

            if last_required_line < unified_data_file["NumberFileLines"] - LINE_DELTA:
                ending_line = last_required_line + LINE_DELTA
            else:
                ending_line = unified_data_file["NumberFileLines"]

            with open(f"{repo_dir}/{patched_file.path}") as f:
                file_list = list(f)
                # Also want to include ending_line
                unified_data["FileContext"] = file_list[starting_line - 1:ending_line]

            unified_data["FileContextStart"] = starting_line

            with open(f"{unified_dataset_dir}/{unified_data_filename_hash}-{num_diff_datapoint}.json", 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, ensure_ascii=False, indent=2)
            print("Created unified_data_filename: ", unified_data_filename)
            unified_data_files.append(unified_data_filename_hash)
            num_diff_datapoint += 1
