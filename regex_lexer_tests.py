import unittest
from regex_lexer import CSharpAndCommentsLexer


the_lexer = CSharpAndCommentsLexer()


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

    def run_single_test(self, test_string, true_token_list, index_vars=False):
        true_token_list = flatten(true_token_list)
        true_token_list = [token for token in true_token_list]
        calculated_token_list = the_lexer.get_tokens(test_string)
        if index_vars:
            index_dict = {}
            index_func = CSharpAndCommentsLexer.index_identifier_token
            calculated_token_list = [index_func(token[0], token[1], index_dict)[
                1] for token in calculated_token_list]
        else:
            calculated_token_list = [token[1]
                                     for token in calculated_token_list]

        self.assertTrue(compare(true_token_list,
                                calculated_token_list), f"""Tokenization failed!
True tokens:
{true_token_list}
-----
Calculated tokens:
{calculated_token_list}""")

    def test_if_block(self):
        test_string = """if (x ==5){
    y=7;
}"""
        true_token_list = ["if", "WHITESPACE", "(", "x", "WHITESPACE", "==", "5", ")", "{", "NEWLINE",
                           ["WHITESPACE"]*4, "y", "=", "7", ";", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_class_definition(self):
        test_string = "public static Image img;"
        true_token_list = ["public", "WHITESPACE", "static",
                           "WHITESPACE", "Image", "WHITESPACE", "img", ";", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_char_string(self):
        test_string = """var z = 'x'  // Char"""
        true_token_list = ["var", "WHITESPACE", "z", "WHITESPACE", "=", "WHITESPACE", "'x'", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "Char", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_basic_string(self):
        test_string = """x = "xyz";  // String"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_basic_verbatim_string(self):
        test_string = """x = @"xyz";  // String"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", '"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_multiline_string(self):
        test_string = """x = @"xyz
klll mmklll
";  // Some comment"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", "NEWLINE", "klll", "WHITESPACE", "mmklll", "NEWLINE",
                           "\"", ";", "WHITESPACE", "WHITESPACE", "//", "WHITESPACE", "Some", "WHITESPACE", "comment", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_block_in_line_comment(self):
        test_string = """if (x=5){ // /* Weird... */ Why?"""
        true_token_list = ["if", "WHITESPACE", "(", "x", "=", "5", ")",
                           "{", "WHITESPACE", "//", "WHITESPACE", "/", "*",
                           "WHITESPACE", "Weird", ".", ".", ".", "WHITESPACE",
                           "*", "/", "WHITESPACE", "Why", "?", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_inline_block_comment(self):
        test_string = """if (nkj && /* njnk */ njs){"""
        true_token_list = ["if", "WHITESPACE", "(", "nkj", "WHITESPACE", "&&", "WHITESPACE",
                           "/*", "WHITESPACE", "njnk", "WHITESPACE", "*/", "WHITESPACE", "njs", ")", "{", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_multiline_block_comment(self):
        test_string = """{
/*
    Change 'Unused' to xyz.
    It's hard!
    What is 'this'?
*/
}"""
        true_token_list = ["{", "NEWLINE", "/*", "NEWLINE", ["WHITESPACE"]*4, "Change", "WHITESPACE", "'", "Unused", "'",
                           "WHITESPACE", "to", "WHITESPACE", "xyz", ".", "NEWLINE", [
                               "WHITESPACE"]*4, "It's", "WHITESPACE", "hard", "!", "NEWLINE",
                           ["WHITESPACE"]*4, "What", "WHITESPACE", "is", "WHITESPACE", "'", "this", "'", "?", "NEWLINE", "*/", "NEWLINE", "}", "NEWLINE"
                           ]
        self.run_single_test(test_string, true_token_list)

    def test_code_whitespace(self):
        test_string = """try{
    z = 5  // Comment
}"""
        true_token_list = ["try", "{", "NEWLINE", ["WHITESPACE"]*4, "z", "WHITESPACE", "=", "WHITESPACE", "5",
                           ["WHITESPACE"]*2, "//", "WHITESPACE", "Comment", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_enums(self):
        test_string = """Found = 302,
Redirect = 302,"""
        true_token_list = ["Found", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE",
                           "Redirect", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_enums_indexed(self):
        test_string = """Found = 302,
Redirect = 302,"""
        true_token_list = ["VAR-0", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE",
                           "VAR-1", "WHITESPACE", "=", "WHITESPACE", "3", "0", "2", ",", "NEWLINE"]
        self.run_single_test(test_string, true_token_list, True)

    def test_pragma(self):

        test_string = """#pragma warning disable 436 // SuppressUnmanagedCodeSecurityAttribute defined in source and mscorlib"""
        true_token_list = ["#pragma", "WHITESPACE", "warning", "WHITESPACE", "disable", "WHITESPACE", "4", "3", "6", "WHITESPACE", "//", "WHITESPACE", "SuppressUnmanagedCodeSecurityAttribute", "WHITESPACE", 
                            "defined", "WHITESPACE", "in", "WHITESPACE", "source", "WHITESPACE", "and", "WHITESPACE", "mscorlib", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_attribute_simple(self):

        test_string = """}

    [Flags]
    internal"""
        true_token_list = ["}", "NEWLINE", "NEWLINE", ["WHITESPACE"]*4, "[", "Flags", "]", "NEWLINE", ["WHITESPACE"]*4, "internal", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_attribute_complex(self):

        # Actually, it's Guid("D682FD12-43dE-411C-811B-BE8404CEA126")
        test_string = """{
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("bla"), SuppressUnmanagedCodeSecurity]
    internal interface ISymNGenWriter"""
        true_token_list = ["{", "NEWLINE", ["WHITESPACE"]*4, "[", "ComImport", ",", "WHITESPACE", "InterfaceType", "(", 
        "ComInterfaceType", ".", "InterfaceIsIUnknown", ")", ",", "WHITESPACE",
        "Guid", "(", "\"", "bla", "\"", ")", ",", "WHITESPACE", "SuppressUnmanagedCodeSecurity", "]",
        "NEWLINE", ["WHITESPACE"]*4, "internal", "WHITESPACE", "interface", "WHITESPACE", "ISymNGenWriter", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    # TODO: UUID ?

if __name__ == '__main__':
    unittest.main()
