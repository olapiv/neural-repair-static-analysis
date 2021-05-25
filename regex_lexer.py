import re
from pygments.lexers.dotnet import CSharpLexer
from pygments.lexers import TextLexer
from pygments.token import Name, Comment, Text, Punctuation
from pygments.lexer import RegexLexer, DelegatingLexer, inherit, bygroups, using, this, default, words
from pygments.token import Punctuation, \
    Text, Comment, Operator, Keyword, Name, String, Number, Literal, Other
from pygments.util import get_choice_opt
from pygments import unistring as uni
from pygments.lexers.web import HtmlLexer, PhpLexer


c_sharp_filepath = "/Users/vincent/Desktop/test-state-machine.cs"
with open(c_sharp_filepath, 'r') as file:
    original_file = file.read()


class UnprocessedTokensMixin(object):

    def get_tokens_unprocessed(self, text):
        for index, token, value in CSharpLexer.get_tokens_unprocessed(self, text):

            if token is Text:
                if value == " ":
                    yield index, Text, "WHITESPACE"
                elif value == "\n":
                    yield index, Text, "NEWLINE"
                elif value == "\t":
                    yield index, Text, "TAB"
                else:
                    yield index, token, value
            elif token is Name:
                # TODO: Implement indexing dictionary
                yield index, token, value
            else:
                yield index, token, value


class LanguageLexer(UnprocessedTokensMixin, RegexLexer):

    tokens = {
        'root': [

            # Variable names in string:
            (r'(?<=[\s\n])\'[^\']+\'(?=[\W])', Name),  # Includes the "'"

            # Words, including ones with apostrophes:
            (r'\w+(\'\w+)?', Text),

            # Formatting
            (r'[\n\s\t\r]', Text),
            (r'[~!%^&*()+=|\[\]:;,.<>/?-]+', Punctuation),

        ]
    }


# textlex = LanguageLexer()
# result = textlex.get_tokens(original_file)
# for (token_type, value) in result:
#     # type, value
#     print(f"token_type: {token_type}, value: {value}")
    
# exit(0)


class CSharpAndCommentsLexer(UnprocessedTokensMixin, CSharpLexer):

    levels = {
        'none': r'@?[_a-zA-Z]\w*',
        'basic': ('@?[_' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl') + ']' +
                  '[' + uni.combine('Lu', 'Ll', 'Lt', 'Lm', 'Nl', 'Nd', 'Pc',
                                    'Cf', 'Mn', 'Mc') + ']*'),
        'full': ('@?(?:_|[^' +
                 uni.allexcept('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl') + '])'
                 + '[^' + uni.allexcept('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl',
                                        'Nd', 'Pc', 'Cf', 'Mn', 'Mc') + ']*'),
    }

    tokens = {}
    token_variants = True

    for levelname, cs_ident in levels.items():
        tokens[levelname] = {
            'root': [
                # method names
                (r'^([ \t]*(?:' + cs_ident + r'(?:\[\])?\s+)+?)'  # return type
                 r'(' + cs_ident + ')'                            # method name
                 r'(\s*)(\()',                               # signature start
                 bygroups(using(this), Name.Function, Text, Punctuation)),
                (r'^\s*\[.*?\]', Name.Attribute),
                (r'[^\S\n]+', Text),
                (r'\\\n', Text),  # line continuation

                ####### OLD: #######
                # (r'//.*?\n', Comment.Single),
                # (r'/[*].*?[*]/', Comment.Multiline),
                ####################

                ####### NEW: #######
                (r'//', Comment.Single, ('line-comments')),
                (r'/\*', Comment.Multiline, ('block-comments')),
                ####################

                (r'\n', Text),
                (r'[~!%^&*()+=|\[\]:;,.<>/?-]', Punctuation),
                (r'[{}]', Punctuation),
                (r'@"(""|[^"])*"', String),
                (r'"(\\\\|\\[^\\]|[^"\\\n])*["\n]', String),
                (r"'\\.'|'[^\\]'", String.Char),
                (r"[0-9](\.[0-9]*)?([eE][+-][0-9]+)?"
                 r"[flFLdD]?|0[xX][0-9a-fA-F]+[Ll]?", Number),
                (r'#[ \t]*(if|endif|else|elif|define|undef|'
                 r'line|error|warning|region|endregion|pragma)\b.*?\n',
                 Comment.Preproc),
                (r'\b(extern)(\s+)(alias)\b', bygroups(Keyword, Text,
                 Keyword)),
                (r'(abstract|as|async|await|base|break|by|case|catch|'
                 r'checked|const|continue|default|delegate|'
                 r'do|else|enum|event|explicit|extern|false|finally|'
                 r'fixed|for|foreach|goto|if|implicit|in|interface|'
                 r'internal|is|let|lock|new|null|on|operator|'
                 r'out|override|params|private|protected|public|readonly|'
                 r'ref|return|sealed|sizeof|stackalloc|static|'
                 r'switch|this|throw|true|try|typeof|'
                 r'unchecked|unsafe|virtual|void|while|'
                 r'get|set|new|partial|yield|add|remove|value|alias|ascending|'
                 r'descending|from|group|into|orderby|select|thenby|where|'
                 r'join|equals)\b', Keyword),
                (r'(global)(::)', bygroups(Keyword, Punctuation)),
                (r'(bool|byte|char|decimal|double|dynamic|float|int|long|object|'
                 r'sbyte|short|string|uint|ulong|ushort|var)\b\??', Keyword.Type),
                (r'(class|struct)(\s+)', bygroups(Keyword, Text), 'class'),
                (r'(namespace|using)(\s+)', bygroups(Keyword, Text), 'namespace'),
                (cs_ident, Name),
            ],
            'class': [
                (cs_ident, Name.Class, '#pop'),
                default('#pop'),
            ],
            'namespace': [
                (r'(?=\()', Text, '#pop'),  # using (resource)
                ('(' + cs_ident + r'|\.)+', Name.Namespace, '#pop'),
            ],

            ####### NEW: #######
            'block-comments': [
                # First group parsed by LanguageLexer, second group parsed by root again
                (r'(.+?)(\*/)', bygroups(using(LanguageLexer), Comment.Multiline), '#pop'),
            ],
            'line-comments': [
                # First group parsed by LanguageLexer, second group parsed by root again
                (r'(.+?)(\n)', bygroups(using(LanguageLexer), Text), '#pop'),
            ]
            ####################
        }


# Consider:
# Binding punctuation ">", "=" --> ">=" (?)

my_lexer = CSharpAndCommentsLexer()

result = my_lexer.get_tokens(original_file)
for (token_type, value) in result:
    print(f"token_type: {token_type}, value: {value}")
    # print("token_type: ", token_type)
    # if token_type == Comment.Multiline:
    #     print("value: ", value)

exit(0)
# ---------------------
# Experimenting with own Regex here
# ---------------------

c_sharp_keywords_filepath = "./csharp_keywords.txt"
with open(c_sharp_keywords_filepath, 'r') as file:
    c_sharp_kw = [x.rstrip() for x in file]

str_diff_separator = "<<<<<< DIFF STARTING HERE >>>>>>"

str_block_comments = r'/\*.*?\*/'
re_block_comments = re.compile(str_block_comments, re.DOTALL)
result = re.findall(re_block_comments, original_file)
print("re_block_comments result: ", result)

str_newlines = '\n'
re_newlines = re.compile(str_newlines)
result = re.findall(re_newlines, original_file)
print("re_newlines result: ", result)

c_sharp_kw[0] = r'\b' + c_sharp_kw[0]
c_sharp_kw[len(c_sharp_kw) - 1] = c_sharp_kw[len(c_sharp_kw) - 1] + r'\b'
str_keywords = r'\b|\b'.join(c_sharp_kw)

regexes = [str_diff_separator, str_block_comments, str_newlines, str_keywords]
pattern_combined = re.compile('|'.join(regexes), re.DOTALL)
result = re.findall(pattern_combined, original_file)

print("result: ", result)
print("len(result): ", len(result))

