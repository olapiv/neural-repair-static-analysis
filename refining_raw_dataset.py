import xml.etree.ElementTree as ET
import json
import os
import urllib.request
from unidiff import PatchSet, PatchedFile
import pandas as pd

diff_dir = "raw_dataset/diffs"
analysis_dir = "raw_dataset/analysis_files"
refined_dataset_dir = "refined_dataset"
repositories_dir = "submodule_repos_to_analyze"

# $OUTPUT_FILENAME = "${Using:REPO_NAME}__${SOLUTION_FILENAME}__${Using:LAST_COMMIT}__${NUGET_FULL_NAME}"
# $DIFF_FILENAME = "${OUTPUT_FILENAME}__${DIAGNOSTIC_ID}.diff"
# $ANALYSIS_FILEPATH = "${OUTPUT_FILENAME}.xml"

# Sample diff-filepath:
# raw_dataset\diffs\runtime__parse-hb-log.sln__e98d043d7d293c88a346b632d8fc12564a8ef0ce__APIDocCodeAnalyzer.1.0.6253.30470__DA3010.diff

# Sample analysis-filepath:
# raw_dataset\analysis_files\runtime__Common.Tests.sln__dcf816579c616e1d172d587301a0a769aa1c0771__AkzenteIT.Analyzers.1.0.6304.37642.xml


df_repos = pd.read_csv("github_repos.csv")
analysis_files = [f.name for f in os.scandir(analysis_dir) if f.is_file()]
refined_data_sample = {
    "Repo": ""
    "RepoURL": ""
    "SolutionFile": ""
    "File": ""
    "Commit": ""
    "DiagnosticID": ""
    "Severity": ""
    "DiagnosticOccurances": [
        # {
        #     "Message": "",
        #     "Line": 0,
        #     "Character": 0
        # },
    ]
    "FileContent": []
    "ParsedDiffHunks": {
        RemovedLines: []
        AddedLines: [
            # {
            #     "TargetLocation": 34,
            #     "Line": ""
            # }
        ]
    }
}


def filter_analysis_files(repo_name, solution_filename, nuget_full_name):

    def filter_func(analysis_filename):
        REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME = analysis_filename.removesuffix(
            '.xml').split("__")
        if repo_name == REPO_NAME and solution_filename == SOLUTION_FILENAME and nuget_full_name == NUGET_FULL_NAME:
            return True
        else:
            return False

    return filter_func


for diff_file in diff_dir:
    REPO_NAME, SOLUTION_FILENAME, LAST_COMMIT, NUGET_FULL_NAME, DIAGNOSTIC_ID = diff_file.removesuffix(
        '.diff').split("__")

    # Prepare XML analysis file
    filtered_analysis_file = filter(filter_analysis_files(
        REPO_NAME, SOLUTION_FILENAME, NUGET_FULL_NAME), analysis_files)[0]
    tree = ET.parse(filtered_analysis_file)
    root = tree.getroot()
    projects_analysed = root.Roslynator.CodeAnalysis.Projects

    diff = urllib.request.urlopen(
        'https://github.com/matiasb/python-unidiff/pull/3.diff')
    encoding = diff.headers.get_charsets()[0]
    patch_set = PatchSet(diff, encoding=encoding)

    repo_dir = f"{repositories_dir}/{REPO_NAME}"

    # Each file has one patch
    for patched_file in patch_set:
        if patch.is_added_file or patched_file.is_removed_file:
            continue

        print("patched_file.added: ", patched_file.added)
        print("patched_file.removed: ", patched_file.removed)
        print("patched_file.is_modified_file: ", patched_file.is_modified_file)

        refined_data_base = refined_data_sample.copy()

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
                
        refined_data["ParsedDiffHunks"]["RemovedLines"] = removed_line_indices
        refined_data["ParsedDiffHunks"]["AddedLines"] = added_lines

        count = 0
        for xml_project in projects_analysed:
            for xml_diagnostic in xml_project.Diagnostics:
                if xml_diagnostic.Id != DIAGNOSTIC_ID or xml_diagnostic.FilePath != patched_file.path:
                    continue
                
                # Just do this once
                if count == 0:
                    refined_data["Severity"] = xml_diagnostic.Severity
                    count++

                refined_data["DiagnosticOccurances"].append(
                    {
                        "Message": xml_diagnostic.Message,
                        "Line": xml_diagnostic.Location.Line,
                        "Character": xml_diagnostic.Location.Character
                    }
                )

        # TODO: Parse patched_file.path
        refined_data_filepath = f"{refined_dataset_dir}/{diff_file.removesuffix('.diff')}__{patched_file.path}.json"
        with open(refined_data_filepath, 'w') as f:
            json.dump(refined_data, f)


    # <Projects>
    #   <Project Name="AppCommon" FilePath="C:\Users\vlohse\source\repos\acat\src\Applications\AppCommon\AppCommon.csproj">
    #     <Diagnostics>
    #       <Diagnostic Id="CA1827">
    #         <Severity>Info</Severity>
    #         <Message>Count() is used where Any() could be used instead to improve performance</Message>
    #         <FilePath>C:\Users\vlohse\source\repos\acat\src\Applications\AppCommon\AppCommon.cs</FilePath>
    #         <Location Line="254" Character="17" />
    #       </Diagnostic>

