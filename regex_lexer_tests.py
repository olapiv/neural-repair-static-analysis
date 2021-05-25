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


def flatten(foo):
    for x in foo:
        if hasattr(x, '__iter__') and not isinstance(x, str):
            for y in flatten(x):
                yield y
        else:
            yield x


# -------------

class TestRegexLexer(unittest.TestCase):

    def run_single_test(self, test_string, true_token_list):
        true_token_list = flatten(true_token_list)
        true_token_list = [token for token in true_token_list]
        calculated_token_list = the_lexer.get_tokens(test_string)
        calculated_token_list = [token[1] for token in calculated_token_list]
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
        true_token_list = ["if", "WHITESPACE", "(", "x", "WHITESPACE", "=", "=", "5", ")", "{", "NEWLINE",
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
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '"xyz"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_multiline_string(self):
        test_string = """x = @"xyz
klll mmklll
";  // Some comment"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", "NEWLINE", "klll", "WHITESPACE", "mmklll", "NEWLINE",
                           "\n", ";", "WHITESPACE", "WHITESPACE", "//", "WHITESPACE", "Some", "WHITESPACE", "comment", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_block_in_line_comment(self):
        test_string = """if (x=5){ // /* Weird... */ Why?"""
        true_token_list = ["if", "WHITESPACE", "(", "x", "=", "5", ")",
                           "{", "WHITESPACE", "//", "WHITESPACE", "/*",
                           "WHITESPACE", "Weird", "...", "WHITESPACE",
                           "*/", "WHITESPACE", "Why", "?", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_inline_block_comment(self):
        test_string = """if (nkj && /* njnk */ njs){"""
        true_token_list = ["if", "WHITESPACE", "(", "nkj", "WHITESPACE", "&", "&", "WHITESPACE",
                           "/*", "WHITESPACE", "njnk", "WHITESPACE", "*/", "WHITESPACE", "njs", ")", "{", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)


"""
try{
    z = 'xyz'  // Error ('), Name (xyz), Error (')
}
Found = 302,

"""

if __name__ == '__main__':
    unittest.main()
