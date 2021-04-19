import urllib.request
from unidiff import PatchSet, PatchedFile


diff = urllib.request.urlopen(
    'https://github.com/matiasb/python-unidiff/pull/3.diff')
encoding = diff.headers.get_charsets()[0]
patches = PatchSet(diff, encoding=encoding)

# Each file has one patch
for patch in patches:
    print("patch.path: ", patch.path)
    print("patch.added: ", patch.added)
    print("patch.removed: ", patch.removed)
    print("patch.is_added_file: ", patch.is_added_file)
    print("patch.is_removed_file: ", patch.is_removed_file)
    print("patch.is_modified_file: ", patch.is_modified_file)

    # Lines next to "@@ -98,7 +99,7 @@" are not counted
    ad_line_no = [line.target_line_no 
            for hunk in patch for line in hunk 
            if line.is_added]
    del_line_no = [line.source_line_no for hunk in patch 
        for line in hunk if line.is_removed]
    print("ad_line_no:", ad_line_no)
    print("del_line_no:", del_line_no)

    added_lines = [{"TargetLocation": line.target_line_no, "Line": line.value}
            for hunk in patch for line in hunk 
            if line.is_added]
    print("added_lines:", added_lines)

    print("########")
    for hunk in patch:
        print("hunk: \n", hunk)

        print("hunk.source_start:", hunk.source_start)
        print("hunk.source_length:", hunk.source_length)
        print("hunk.target_start:", hunk.target_start)
        print("hunk.target_length:", hunk.target_length)
        print("hunk.section_header:", hunk.section_header)

        # print("hunk.added:", hunk.added)
        # print("hunk.removed:", hunk.removed)
        # print("hunk.source:", hunk.source)
        # print("hunk.target:", hunk.target)
        print("----")
    print("--------")
