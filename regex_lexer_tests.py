import unittest
import requests
import json
from regex_lexer import CSharpAndCommentsLexer
from tokenizing_unified_dataset import split_tokens_by_line


def compare(s, t):
    t = list(t)   # make a mutable copy
    try:
        for elem in s:
            t.remove(elem)
    except ValueError:
        return False
    return not t


# Used, so that formatting can be compressed (e.g. ["WHITESPACE"]*4)
def flatten(foo):
    for x in foo:
        if hasattr(x, '__iter__') and not isinstance(x, str):
            for y in flatten(x):
                yield y
        else:
            yield x


# -------------

class TestRegexLexer(unittest.TestCase):

    standard_lexer = CSharpAndCommentsLexer()
    camelcase_lexer = CSharpAndCommentsLexer()

    def run_single_test(self, test_string, true_token_list, camelcase=False, index_vars=False):
        true_token_list = flatten(true_token_list)
        true_token_list = [token for token in true_token_list]

        if camelcase:
            calculated_token_list = self.camelcase_lexer.get_tokens(test_string)
        else:
            calculated_token_list = self.standard_lexer.get_tokens(test_string)

        if index_vars:
            if camelcase:
                self.assertTrue(False, "Cannot split for camelcase and index variables at the same time!")
            else:
                index_dict = {}
                index_func = CSharpAndCommentsLexer.index_identifier_token
                calculated_token_list = [index_func(token[0], token[1], index_dict)[1] for token in calculated_token_list]
        else:
            calculated_token_list = [token[1] for token in calculated_token_list]

        self.assertTrue(compare(true_token_list,
                                calculated_token_list), f"""Tokenization failed!
Camelcase: {camelcase}
Index Vars: {index_vars}
True tokens:
{true_token_list}
-----
Calculated tokens:
{calculated_token_list}""")

    ######################
    ######################
    ######################

    CODE_IF_BLOCK = """if (niceGuy ==5){
    y=7;
}"""

    def test_if_block(self):
        true_token_list = ["if", "WHITESPACE", "(", "niceGuy", "WHITESPACE", "==", "5", ")", "{", "NEWLINE",
                           ["WHITESPACE"]*4, "y", "=", "7", ";", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(self.CODE_IF_BLOCK, true_token_list)

    def test_if_block_camelcase(self):
        true_token_list = ["if", "WHITESPACE", "(", "nice", "Guy", "WHITESPACE", "==", "5", ")", "{", "NEWLINE",
                           ["WHITESPACE"]*4, "y", "=", "7", ";", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(self.CODE_IF_BLOCK, true_token_list, camelcase=True)

    CODE_CLASS_DEFINITION = "public static Image imgCOPY;"

    def test_class_definition(self):
        true_token_list = ["public", "WHITESPACE", "static",
                           "WHITESPACE", "Image", "WHITESPACE", "imgCOPY", ";", "NEWLINE"]
        self.run_single_test(self.CODE_CLASS_DEFINITION, true_token_list)

    def test_class_definition_camelcase(self):
        true_token_list = ["public", "WHITESPACE", "static",
                           "WHITESPACE", "Image", "WHITESPACE", "img", "COPY",";", "NEWLINE"]
        self.run_single_test(self.CODE_CLASS_DEFINITION, true_token_list, camelcase=True)

    CODE_CHAR_STRING = """var eclipseRCPExt = 'x'  // Char"""

    def test_char_string(self):
        true_token_list = ["var", "WHITESPACE", "eclipseRCPExt", "WHITESPACE", "=", "WHITESPACE", "'x'", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "Char", "NEWLINE"]
        self.run_single_test(self.CODE_CHAR_STRING, true_token_list)

    def test_char_string_camelcase(self):
        true_token_list = ["var", "WHITESPACE", "eclipse", "RCP", "Ext", "WHITESPACE", "=", "WHITESPACE", "'x'", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "Char", "NEWLINE"]
        self.run_single_test(self.CODE_CHAR_STRING, true_token_list, camelcase=True)

    CODE_BASIC_STRING = """x = "xyz";  // String"""

    def test_basic_string(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(self.CODE_BASIC_STRING, true_token_list)

    def test_basic_string_camelcase(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(self.CODE_BASIC_STRING, true_token_list, camelcase=True)

    CODE_VERBATIM_STRING = """x = @"xyz";  // String"""

    def test_basic_verbatim_string(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(self.CODE_VERBATIM_STRING, true_token_list)

    def test_basic_verbatim_string(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(self.CODE_VERBATIM_STRING, true_token_list, camelcase=True)

    CODE_MULTILINE_STRING = """x = @"xyz
klll mmklll
";  // Some comment"""

    def test_multiline_string(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", "NEWLINE", "klll", "WHITESPACE", "mmklll", "NEWLINE",
                           "\"", ";", "WHITESPACE", "WHITESPACE", "//", "WHITESPACE", "Some", "WHITESPACE", "comment", "NEWLINE"]
        self.run_single_test(self.CODE_MULTILINE_STRING, true_token_list)

    def test_multiline_string_camelcase(self):
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", "NEWLINE", "klll", "WHITESPACE", "mmklll", "NEWLINE",
                           "\"", ";", "WHITESPACE", "WHITESPACE", "//", "WHITESPACE", "Some", "WHITESPACE", "comment", "NEWLINE"]
        self.run_single_test(self.CODE_MULTILINE_STRING, true_token_list, camelcase=True)

    CODE_BLOCK_IN_LINE_COMMENT = """if (x=5){ // /* Weird... */ Why?"""

    def test_block_in_line_comment(self):
        true_token_list = ["if", "WHITESPACE", "(", "x", "=", "5", ")",
                           "{", "WHITESPACE", "//", "WHITESPACE", "/", "*",
                           "WHITESPACE", "Weird", ".", ".", ".", "WHITESPACE",
                           "*", "/", "WHITESPACE", "Why", "?", "NEWLINE"]
        self.run_single_test(self.CODE_BLOCK_IN_LINE_COMMENT, true_token_list)

    def test_block_in_line_comment_camelcase(self):
        true_token_list = ["if", "WHITESPACE", "(", "x", "=", "5", ")",
                           "{", "WHITESPACE", "//", "WHITESPACE", "/", "*",
                           "WHITESPACE", "Weird", ".", ".", ".", "WHITESPACE",
                           "*", "/", "WHITESPACE", "Why", "?", "NEWLINE"]
        self.run_single_test(self.CODE_BLOCK_IN_LINE_COMMENT, true_token_list, camelcase=True)

    CODE_INLINE_BLOCK_COMMENT = """if (nkj && /* njnk */ njs){"""

    def test_inline_block_comment(self):
        true_token_list = ["if", "WHITESPACE", "(", "nkj", "WHITESPACE", "&&", "WHITESPACE",
                           "/*", "WHITESPACE", "njnk", "WHITESPACE", "*/", "WHITESPACE", "njs", ")", "{", "NEWLINE"]
        self.run_single_test(self.CODE_INLINE_BLOCK_COMMENT, true_token_list)

    def test_inline_block_comment_camelcase(self):
        true_token_list = ["if", "WHITESPACE", "(", "nkj", "WHITESPACE", "&&", "WHITESPACE",
                           "/*", "WHITESPACE", "njnk", "WHITESPACE", "*/", "WHITESPACE", "njs", ")", "{", "NEWLINE"]
        self.run_single_test(self.CODE_INLINE_BLOCK_COMMENT, true_token_list, camelcase=True)

    CODE_MULTILINE_BLOCK_COMMENT = """{
/*
    Change 'eclipseRCPExt' to xyz.
    It's hard!
    What is 'this'?
*/
}"""

    def test_multiline_block_comment(self):
        true_token_list = ["{", "NEWLINE", "/*", "NEWLINE", ["WHITESPACE"]*4, "Change", "WHITESPACE", "'", "eclipseRCPExt", "'",
                           "WHITESPACE", "to", "WHITESPACE", "xyz", ".", "NEWLINE", [
                               "WHITESPACE"]*4, "It's", "WHITESPACE", "hard", "!", "NEWLINE",
                           ["WHITESPACE"]*4, "What", "WHITESPACE", "is", "WHITESPACE", "'", "this", "'", "?", "NEWLINE", "*/", "NEWLINE", "}", "NEWLINE"
                           ]
        self.run_single_test(self.CODE_MULTILINE_BLOCK_COMMENT, true_token_list)

    def test_multiline_block_comment_camelcase(self):
        true_token_list = ["{", "NEWLINE", "/*", "NEWLINE", ["WHITESPACE"]*4, "Change", "WHITESPACE", "'", "eclipse", "RCP", "Ext", "'",
                           "WHITESPACE", "to", "WHITESPACE", "xyz", ".", "NEWLINE", [
                               "WHITESPACE"]*4, "It's", "WHITESPACE", "hard", "!", "NEWLINE",
                           ["WHITESPACE"]*4, "What", "WHITESPACE", "is", "WHITESPACE", "'", "this", "'", "?", "NEWLINE", "*/", "NEWLINE", "}", "NEWLINE"
                           ]
        self.run_single_test(self.CODE_MULTILINE_BLOCK_COMMENT, true_token_list, camelcase=True)

    CODE_WHITESPACE = """try{
    eclipseRCPExt = 5  // Comment
}"""

    def test_code_whitespace(self):
        true_token_list = ["try", "{", "NEWLINE", ["WHITESPACE"]*4, "eclipseRCPExt", "WHITESPACE", "=", "WHITESPACE", "5",
                           ["WHITESPACE"]*2, "//", "WHITESPACE", "Comment", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(self.CODE_WHITESPACE, true_token_list)

    def test_code_whitespace_camelcase(self):
        true_token_list = ["try", "{", "NEWLINE", ["WHITESPACE"]*4, "eclipse", "RCP", "Ext", "WHITESPACE", "=", "WHITESPACE", "5",
                           ["WHITESPACE"]*2, "//", "WHITESPACE", "Comment", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(self.CODE_WHITESPACE, true_token_list, camelcase=True)

    CODE_ENUMS = """Found = 302,
Redirect = 302,"""

    def test_enums(self):
        true_token_list = ["Found", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE",
                           "Redirect", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE"]
        self.run_single_test(self.CODE_ENUMS, true_token_list)

    def test_enums_camelcase(self):
        true_token_list = ["Found", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE",
                           "Redirect", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE"]
        self.run_single_test(self.CODE_ENUMS, true_token_list, camelcase=True)

    def test_enums_indexed(self):
        true_token_list = ["VAR-0", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE",
                           "VAR-1", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE"]
        self.run_single_test(self.CODE_ENUMS, true_token_list, True)

    CODE_PRAGMA = """#pragma warning disable 436 // SuppressUnmanagedCodeSecurityAttribute defined in source and mscorlib"""

    def test_pragma(self):
        true_token_list = ["#pragma", "WHITESPACE", "warning", "WHITESPACE", "disable", "WHITESPACE", "4", "3", "6", "WHITESPACE", "//", "WHITESPACE", "SuppressUnmanagedCodeSecurityAttribute", "WHITESPACE",
                           "defined", "WHITESPACE", "in", "WHITESPACE", "source", "WHITESPACE", "and", "WHITESPACE", "mscorlib", "NEWLINE"]
        self.run_single_test(self.CODE_PRAGMA, true_token_list)

    def test_pragma_camelcase(self):
        true_token_list = ["#pragma", "WHITESPACE", "warning", "WHITESPACE", "disable", "WHITESPACE", "4", "3", "6", "WHITESPACE", "//", "WHITESPACE", "Suppress", "Unmanaged", "CodeSecurity", "Attribute", "WHITESPACE",
                           "defined", "WHITESPACE", "in", "WHITESPACE", "source", "WHITESPACE", "and", "WHITESPACE", "mscorlib", "NEWLINE"]
        self.run_single_test(self.CODE_PRAGMA, true_token_list, camelcase=True)

    CODE_ATTRIBUTE_SIMPLE = """}

    [Flags]
    internal"""

    def test_attribute_simple(self):
        true_token_list = ["}", "NEWLINE", "NEWLINE", [
            "WHITESPACE"]*4, "[", "Flags", "]", "NEWLINE", ["WHITESPACE"]*4, "internal", "NEWLINE"]
        self.run_single_test(self.CODE_ATTRIBUTE_SIMPLE, true_token_list)

    def test_attribute_simple_camelcase(self):
        true_token_list = ["}", "NEWLINE", "NEWLINE", [
            "WHITESPACE"]*4, "[", "Flags", "]", "NEWLINE", ["WHITESPACE"]*4, "internal", "NEWLINE"]
        self.run_single_test(self.CODE_ATTRIBUTE_SIMPLE, true_token_list, camelcase=True)

    # Actually, it's Guid("D682FD12-43dE-411C-811B-BE8404CEA126")
    CODE_ATTRIBUTE_COMPLEX = """{
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("bla"), SuppressUnmanagedCodeSecurity]
    internal interface ISymNGenWriter"""

    def test_attribute_complex(self):
        true_token_list = ["{", "NEWLINE", ["WHITESPACE"]*4, "[", "ComImport", ",", "WHITESPACE", "InterfaceType", "(",
                           "ComInterfaceType", ".", "InterfaceIsIUnknown", ")", ",", "WHITESPACE",
                           "Guid", "(", "\"", "bla", "\"", ")", ",", "WHITESPACE", "SuppressUnmanagedCodeSecurity", "]",
                           "NEWLINE", ["WHITESPACE"]*4, "internal", "WHITESPACE", "interface", "WHITESPACE", "ISymNGenWriter", "NEWLINE"]
        self.run_single_test(self.CODE_ATTRIBUTE_COMPLEX, true_token_list)

    def test_attribute_complex_camelcase(self):
        true_token_list = ["{", "NEWLINE", ["WHITESPACE"]*4, "[", "Com","Import", ",", "WHITESPACE", "Interface", "Type", "(",
                           "Com","Interface", "Type", ".", "Interface", "Is", "I", "Unknown" ")", ",", "WHITESPACE",
                           "Guid", "(", "\"", "bla", "\"", ")", ",", "WHITESPACE", "Suppress", "Unmanaged", "Code", "Security", "]",
                           "NEWLINE", ["WHITESPACE"]*4, "internal", "WHITESPACE", "interface", "WHITESPACE", "I", "Sym", "N", "Gen", "Writer", "NEWLINE"]
        self.run_single_test(self.CODE_ATTRIBUTE_COMPLEX, true_token_list, camelcase=True)

    CODE_BASIC_CLASS = """class ConnectAWSToDB {
    }"""

    def test_basic_class(self):
        true_token_list = ["class", "WHITESPACE", "ConnectAWSToDB", "WHITESPACE", "{", "NEWLINE", ["WHITESPACE"]*4, "}", "NEWLINE"]
        self.run_single_test(self.CODE_BASIC_CLASS, true_token_list)

    def test_basic_class_camelcase(self):
        true_token_list = ["class", "WHITESPACE", "Connect", "AWS", "To", "DB", "WHITESPACE", "{", "NEWLINE", ["WHITESPACE"]*4, "}", "NEWLINE"]
        self.run_single_test(self.CODE_BASIC_CLASS, true_token_list, camelcase=True)

    CODE_WHERE_KEYWORD = """public partial struct Nullable<T> where T : struct
    {
        c T value;"""

    def test_where_keyword(self):
        true_token_list = ["public", "WHITESPACE", "partial", "WHITESPACE", "struct", "WHITESPACE", "Nullable",
                           "<", "T", ">", "WHITESPACE", "where", "WHITESPACE", "T", "WHITESPACE", ":", "WHITESPACE",
                           "struct", "NEWLINE", [
                               "WHITESPACE"]*4, "{", "NEWLINE", ["WHITESPACE"]*8, "c",
                           "WHITESPACE", "T", "WHITESPACE", "value", ";", "NEWLINE"]
        self.run_single_test(self.CODE_WHERE_KEYWORD, true_token_list)

    def test_where_keyword_camelcase(self):
        true_token_list = ["public", "WHITESPACE", "partial", "WHITESPACE", "struct", "WHITESPACE", "Nullable",
                           "<", "T", ">", "WHITESPACE", "where", "WHITESPACE", "T", "WHITESPACE", ":", "WHITESPACE",
                           "struct", "NEWLINE", [
                               "WHITESPACE"]*4, "{", "NEWLINE", ["WHITESPACE"]*8, "c",
                           "WHITESPACE", "T", "WHITESPACE", "value", ";", "NEWLINE"]
        self.run_single_test(self.CODE_WHERE_KEYWORD, true_token_list, camelcase=True)

    CODE_METHODS = """public void CopyTo
        ("""

    def test_methods(self):
        true_token_list = ["public", "WHITESPACE", "void", "WHITESPACE", "CopyTo", "NEWLINE", ["WHITESPACE"]*8, "(", "NEWLINE"]
        self.run_single_test(self.CODE_METHODS, true_token_list)

    def test_methods_camelcase(self):
        true_token_list = ["public", "WHITESPACE", "void", "WHITESPACE", "Copy", "To", "NEWLINE", ["WHITESPACE"]*8, "(", "NEWLINE"]
        self.run_single_test(self.CODE_METHODS, true_token_list, camelcase=True)

    def test_count_newlines(self):
        """
        Testing on large files; simply checking whether all NEWLINEs are counted correctly
        """
        # file_to_test = "https://raw.githubusercontent.com/dotnet/runtime/e98d043d7d293c88a346b632d8fc12564a8ef0ce/src/coreclr/tools/aot/ILCompiler.Diagnostics/ISymNGenWriter.cs"
        # file_to_test = "https://raw.githubusercontent.com/dotnet/runtime/e98d043d7d293c88a346b632d8fc12564a8ef0ce/src/coreclr/tools/aot/ILCompiler.Diagnostics/MethodInfo.cs"
        file_to_test = "https://raw.githubusercontent.com/dotnet/runtime/e98d043d7d293c88a346b632d8fc12564a8ef0ce/src/libraries/System.Runtime/ref/System.Runtime.cs"
        f = requests.get(file_to_test)
        file_string = f.text.rstrip('\n')  # file.text returns non-existent newline at the end...
        num_total_lines = file_string.count('\n') + 1  # +1 because logic of newlines

        line_deltas = 40
        line_start = 0
        while line_start < num_total_lines:

            end_of_file = (line_start + line_deltas) > num_total_lines

            if end_of_file:
                split_file = file_string.split(
                    "\n")[line_start:]
            else:
                split_file = file_string.split(
                    "\n")[line_start:line_start+line_deltas]

            file_string_section = "\n".join(split_file)

            orig_file_tokens = [
                result for result in self.standard_lexer.get_tokens(file_string_section)]

            # Because lexer always adds NEWLINE at very end
            del orig_file_tokens[-1]

            line_tokens = split_tokens_by_line(orig_file_tokens)

            if len(split_file) != len(line_tokens):
                for count, line in enumerate(line_tokens):
                    for token in line:
                        if token[1] != "WHITESPACE":
                            first_useful_token = token
                            break
                    print(
                        f"[0]:{first_useful_token} [-1]:{line[-1][1]} content: {split_file[count]}")

                self.assertEqual(line_deltas, len(line_tokens), f"""
                Between line {line_start} and line {line_start + line_deltas},
                line_deltas: {line_deltas}; len(line_tokens): {len(line_tokens)}; Not equal!""")

            line_start += line_deltas

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
