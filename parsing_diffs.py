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
    print("########")
    for hunk in patch:
        print("hunk: ", hunk)

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
