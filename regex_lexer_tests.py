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

    def test_nqjk(self):
        test_string = """if (x ==5){
    y=7;
}"""
        true_token_list = ["if", "WHITESPACE", "(", "x", "WHITESPACE", "=", "=", "5", ")", "{", "NEWLINE",
                           ["WHITESPACE"]*4, "y", "=", "7", ";", "NEWLINE", "}", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_fnjk(self):
        test_string = """x = @"xyz
klll mmklll
";  // Some comment"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '@"', "xyz", "NEWLINE", "klll", "WHITESPACE", "mmklll", "NEWLINE",
                           "\n", ";", "WHITESPACE", "WHITESPACE", "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_snw2jk(self):
        test_string = "public static Image img;"
        true_token_list = ["public", "WHITESPACE", "static",
                           "WHITESPACE", "Image", "WHITESPACE", "img", ";", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)

    def test_1mw2k1l(self):
        test_string = """x = "xyz";  // String"""
        true_token_list = ["x", "WHITESPACE", "=", "WHITESPACE", '"xyz"', ";", [
            "WHITESPACE"]*2, "//", "WHITESPACE", "String", "NEWLINE"]
        self.run_single_test(test_string, true_token_list)




"""
/ x = "x";  // String
x = @"xyz
klll mmklll
";  // Some comment
x = @"abc";
z = 'x'  // Char
try{
    z = 'xyz'  // Error ('), Name (xyz), Error (')
}
Found = 302,

"""

if __name__ == '__main__':
    unittest.main()
