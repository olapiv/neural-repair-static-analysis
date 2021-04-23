import urllib.request
from unidiff import PatchSet, PatchedFile
import json


def parse_hunk(hunk):

    all_replaced_lines = []
    all_added_lines = []
    all_removed_lines = []

    replaced_line_pair = {
        "SourceLocations": [],
        "TargetLines": []
    }
    added_line_set = {
        "PreviousSourceLocation": None,
        "TargetStartLocation": None,
        "TargetLines": []
    }
    removed_line_set = {
        "SourceLocationStart": None,
        "SourceLocationEnd": None,
    }

    prev_line = None
    for line in hunk:
        if line.is_context:
            if added_line_set["TargetStartLocation"]:
                all_added_lines.append(added_line_set)
                added_line_set = {
                    "PreviousSourceLocation": None,
                    "TargetStartLocation": None,
                    "TargetLines": []
                }
            elif replaced_line_pair["SourceLocations"] != []:

                # Looked liked replacing, but just ended up deleting:
                if replaced_line_pair["TargetLines"] == []:
                    all_removed_lines.append({
                        "SourceLocationStart": replaced_line_pair["SourceLocations"][0],
                        "SourceLocationEnd": replaced_line_pair["SourceLocations"][-1],
                    })
                else:
                    all_replaced_lines.append(replaced_line_pair)

                replaced_line_pair = {
                    "SourceLocations": [],
                    "TargetLines": []
                }

        elif line.is_added:
            # Nothing deleted previously:
            if replaced_line_pair["SourceLocations"] == []:

                # Nothing added previously:
                if not added_line_set["TargetStartLocation"]:
                    added_line_set["PreviousSourceLocation"] = prev_line.source_line_no if prev_line else hunk.source_start
                    added_line_set["TargetStartLocation"] = line.target_line_no
                added_line_set["TargetLines"].append(line.value)

            # Add is related to previous deletion:
            else:
                replaced_line_pair["TargetLines"].append(line.value)

        elif line.is_removed:
            replaced_line_pair["SourceLocations"].append(line.source_line_no)

        prev_line = line

    if replaced_line_pair["SourceLocations"] != []:
        # Deleted lines without adding
        if replaced_line_pair["TargetLines"] == []:
            all_removed_lines.append({
                "SourceLocationStart": replaced_line_pair["SourceLocations"][0],
                "SourceLocationEnd": replaced_line_pair["SourceLocations"][-1],
            })
        else:
            all_replaced_lines.append(replaced_line_pair)
    elif added_line_set["TargetStartLocation"]:
        all_added_lines.append(added_line_set)

    return all_replaced_lines, all_added_lines, all_removed_lines


def run_through_patches(patches):
    # Each file has one patch
    for patch in patches:
        # print("patch.path: ", patch.path)
        # print("patch.added: ", patch.added)
        # print("patch.removed: ", patch.removed)
        # print("patch.is_added_file: ", patch.is_added_file)
        # print("patch.is_removed_file: ", patch.is_removed_file)
        # print("patch.is_modified_file: ", patch.is_modified_file)

        # Lines next to "@@ -98,7 +99,7 @@" are not counted
        # ad_line_no = [line.target_line_no
        #               for hunk in patch for line in hunk
        #               if line.is_added]
        # del_line_no = [line.source_line_no for hunk in patch
        #                for line in hunk if line.is_removed]
        # # print("ad_line_no:", ad_line_no)
        # # print("del_line_no:", del_line_no)

        # added_lines = [{"TargetLocation": line.target_line_no, "Line": line.value}
        #                for hunk in patch for line in hunk
        #                if line.is_added]
        # print("added_lines:", added_lines)

        print("########")
        for hunk in patch:
            replaced_lines = []
            print("hunk: \n", hunk)

            all_replaced_lines, all_added_lines, all_removed_lines = parse_hunk(
                hunk)
            print("all_replaced_lines: ", all_replaced_lines)
            print("all_added_lines: ", all_added_lines)
            print("all_removed_lines: ", all_removed_lines)

            # print("hunk.source_start:", hunk.source_start)
            # print("hunk.source_length:", hunk.source_length)
            # print("hunk.target_start:", hunk.target_start)
            # print("hunk.target_length:", hunk.target_length)
            # print("hunk.section_header:", hunk.section_header)

            # print("hunk.added:", hunk.added)
            # print("hunk.removed:", hunk.removed)
            # print("hunk.source:", hunk.source)
            # print("hunk.target:", hunk.target)

            # print ("replaced_lines", json.dumps(replaced_lines, indent=2))
            # print("----")
        print("--------")


if __name__ == "__main__":
    diff = urllib.request.urlopen(
        'https://github.com/matiasb/python-unidiff/pull/3.diff')
    encoding = diff.headers.get_charsets()[0]
    patches = PatchSet(diff, encoding=encoding)
    run_through_patches(patches)
