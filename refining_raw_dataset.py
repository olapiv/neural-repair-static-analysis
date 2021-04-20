import xml.etree.ElementTree as ET
import json
import os
import urllib.request
from unidiff import PatchSet, PatchedFile
import pandas as pd
import hashlib


diff_dir = "raw_dataset/diffs"
analysis_dir = "raw_dataset/analysis_files"
refined_dataset_dir = "refined_dataset"
repositories_dir = "submodule_repos_to_analyze"


df_repos = pd.read_csv("github_repos.csv")
analysis_files = [f.name for f in os.scandir(analysis_dir) if f.is_file()]
refined_data_files = [f.name for f in os.scandir(
    refined_dataset_dir) if f.is_file()]

# Instantiate this multiple times later:
refined_data_sample = {
    "Repo": "",
    "RepoURL": "",
    "SolutionFile": "",
    "File": "",
    "Commit": "",
    "DiagnosticID": "",
    "Severity": "",
    "DiagnosticOccurances": [
        # {
        #     "Message": "",
        #     "Line": 0,
        #     "Character": 0
        # },
    ],
    "FileContent": [],
    "ParsedDiff": {
        "RemovedLines": [],
        "AddedLines": [
            # {
            #     "TargetLocation": 34,
            #     "Line": ""
            # }
        ]
    }
}

def hash_filename(filename):
    """Using hash function to avoid OS Errors, too  long filename"""
    return f"{str(int(hashlib.sha256(filename.encode('utf-8')).hexdigest(), 16) % 10**8)}.json"


def filter_analysis_files(repo_name, solution_filename, nuget_full_name):

    def filter_func(analysis_filename):
        """
        $ANALYSIS_FILEPATH = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}.xml"
        
        Sample ANALYSIS_FILEPATH:
        raw_dataset\analysis_files\runtime__Common.Tests.sln__dcf816579c616e1d172d587301a0a769aa1c0771__AkzenteIT.Analyzers.1.0.6304.37642.xml
        """
        REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME = analysis_filename[:-len(
            '.xml')].split("__")
        if repo_name == REPO_NAME and solution_filename == SOLUTION_FILENAME and nuget_full_name == NUGET_FULL_NAME:
            return True
        else:
            return False

    return filter_func


diff_files = [f.name for f in os.scandir(diff_dir) if f.is_file()]
for diff_file in diff_files:

    print("diff_file: ", diff_file)

    # $ANALYSIS_FILEPATH = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}__${DIAGNOSTIC_ID}.diff"
    REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME, DIAGNOSTIC_ID = diff_file[:-len(
        '.diff')].split("__")

    # Prepare XML analysis file
    filtered_analysis_file = list(filter(filter_analysis_files(
        REPO_NAME, SOLUTION_FILENAME, NUGET_FULL_NAME), analysis_files))[0]

    tree = ET.parse(f"{analysis_dir}/{filtered_analysis_file}")
    root = tree.getroot()  # Roslynator is root
    projects_analysed = root.find('CodeAnalysis').find('Projects')

    patch_set = PatchSet.from_filename(f"{diff_dir}/{diff_file}")

    repo_dir = f"{repositories_dir}/{REPO_NAME}"

    # One patch per file
    for patched_file in patch_set:
        if patched_file.is_added_file or patched_file.is_removed_file:
            continue

        parsed_file_path = patched_file.path.replace(
            "/", "--").replace("\\", "--")
        refined_data_filename = f"{diff_file[:-len('.diff')]}__{parsed_file_path}"
        refined_data_filename_hash = f"{hash_filename(refined_data_filename)}"
        if refined_data_filename_hash in refined_data_files:
            print(
                f"refined_data_filename_hash already exists! file: {refined_data_filename}")
            # Appending refined_data_filename_hash to refined_data_files in the end
            continue

        refined_data = refined_data_sample.copy()

        repo_row = df_repos.loc[df_repos['RepoName'] == REPO_NAME].iloc[0]

        refined_data["Repo"] = REPO_NAME
        refined_data["RepoURL"] = repo_row["RepoURL"]
        refined_data["SolutionFile"] = SOLUTION_FILENAME
        refined_data["File"] = patched_file.path
        refined_data["Commit"] = LAST_COMMIT
        refined_data["DiagnosticID"] = DIAGNOSTIC_ID

        with open(f"{repo_dir}/{patched_file.path}") as f:
            # my_list = [x.rstrip() for x in f] # remove line breaks
            refined_data["FileContent"] = list(f)

        removed_line_indices = [line.source_line_no for hunk in patched_file
                                for line in hunk if line.is_removed]

        added_lines = [{"TargetLocation": line.target_line_no, "Line": line.value}
                       for hunk in patched_file for line in hunk
                       if line.is_added]

        refined_data["ParsedDiff"]["RemovedLines"] = removed_line_indices
        refined_data["ParsedDiff"]["AddedLines"] = added_lines

        count = 0
        for xml_project in projects_analysed:
            for xml_diagnostic in xml_project.find('Diagnostics'):
                if xml_diagnostic.get('Id') != DIAGNOSTIC_ID or xml_diagnostic.find('FilePath').text != patched_file.path:
                    continue

                # Just do this once
                if count == 0:
                    refined_data["Severity"] = xml_diagnostic.find(
                        'Severity').text
                    count += 1

                refined_data["DiagnosticOccurances"].append(
                    {
                        "Message": xml_diagnostic.find('Message').text,
                        "Line": xml_diagnostic.find('Location').get('Line'),
                        "Character": xml_diagnostic.find('Location').get('Character')
                    }
                )

        with open(f"{refined_dataset_dir}/{refined_data_filename_hash}", 'w', encoding='utf-8') as f:
            json.dump(refined_data, f, ensure_ascii=False, indent=2)
        print("Created refined_data_filename: ", refined_data_filename)
        refined_data_files.append(refined_data_filename_hash)
