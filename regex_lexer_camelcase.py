import re
from pygments.lexers.dotnet import CSharpLexer
from pygments.token import Name, Comment, Text, Punctuation
from pygments.lexer import RegexLexer, DelegatingLexer, inherit, bygroups, using, this, default, words
from pygments.token import Punctuation, \
    Text, Comment, Operator, Keyword, Name, String, Number, Literal, Other
from pygments.util import get_choice_opt
from pygments import unistring as uni


class UnprocessedTokensMixin(object):

    def get_tokens_unprocessed(self, text):
        for index, token, value in CSharpLexer.get_tokens_unprocessed(self, text):

            if token is Text:
                if value == " ":
                    yield index, Text, "WHITESPACE"
                # if " " in value:
                #     yield index, Text, f"WHITESPACE-{value.count(' ')}"
                elif value == "\n":
                    yield index, Text, "NEWLINE"
                elif value == "\t":
                    yield index, Text, "TAB"
                else:
                    yield index, token, value
            else:
                yield index, token, value


class LanguageLexer(UnprocessedTokensMixin, RegexLexer):
    """
    Occasionally (quite rarely), multiple lines are put into quotation marks. Since
    we only assume that these are used for variable names, this leads to none of the
    formatting being tokenized. This is therefore an incorrect datapoint.
    """

    camelCase = '(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])'

    tokens = {
        'root': [

            # Words separated by camelcase:
            ('[A-Z]+(?=[A-Z][a-z])', Name),
            ('[A-Z][a-z]+', Name),
            ('([a-z]+)', Name),
            ('([A-Z]+)', Name),
            # ('[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]+|[a-z]+|[A-Z]+', Name),

            # Formatting
            (r'[\n\s\t\r\v]', Text),
            
            # Punctuation
            (r'[~!%^&*()+=|\'\]\[:;,.<>/?-]', Punctuation),

            (r"\d", Number),

        ]
    }


class CSharpAndCommentsCamelcaseLexer(UnprocessedTokensMixin, CSharpLexer):
    """
    Since it's difficult to inherit "tokens" from CSharpLexer the way
    it's shown in the documentation (https://pygments.org/docs/lexerdevelopment/#modifying-token-streams),
    this is simply a copy of most of the logic in CSharpLexer.
    """

    tokens = {}
    token_variants = True

    for levelname, cs_ident in CSharpLexer.levels.items():
        tokens[levelname] = {
            'root': [

                # Formatting
                (r'[^\S\n]', Text),  # Inside [], ^ is a negation
                # (r'[\s\t\r\v]', Text),  # Being explicit in what to match

                # Line continuation
                (r'\\\n', Text),

                # Comments as natural language
                (r'//', Comment.Single, ('line-comments')),
                (r'/\*', Comment.Multiline, ('block-comments')),

                ####################

                (r'\n', Text),

                # Punctuation
                # 3 symbols
                (r'(->\*|>>=|<<=|\.\.\.)', Operator),
                # 2 symbols
                (r'(\+\+|\+=|--|-=|->|&&|&=|\|\||\|=|!=|%=|\*=|==|::|\^=|>=|>>|<=|<<|/=|&&|&=|\^=)', Operator),
                # 1 symbol
                (r'[~!%^&*()+=|\[\]:;,.<>/?-]', Operator),

                (r'[{}]', Punctuation),

                # String as natural language
                (r'@"', String, ('verbatim-strings')),
                (r'"', String, ('other-strings')),

                (r"'\\.'|'[^\\]'", String.Char),

                # Numbers
                (r"[0-9](\.[0-9]*)?([eE][+-][0-9]+)?"
                 r"[flFLdD]?|0[xX][0-9a-fA-F]+[Ll]?", Number),

                (r'#[ \t]*(if|endif|else|elif|define|undef|'
                 r'line|error|warning|region|endregion|pragma)', Comment.Preproc),

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

                (r'\b(class|struct|namespace|using)\b', Keyword),

                (r'(?:(?<=class\W)|(?<=struct\W))', using(this), ('identifier')),
                (r'(?:(?<=namespace\W)|(?<=using\W))', using(this), ('identifier')),

                # Words separated by camelcase:
                ('[A-Z]+(?=[A-Z][a-z])', Name),
                ('[A-Z][a-z]+', Name),
                ('([a-z]+)', Name),
                ('([A-Z]+)', Name),
                # ('[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]+|[a-z]+|[A-Z]+', Name),

                (cs_ident, Name),

            ],

            'identifier': [
                (r'[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]+|[a-z]+|[A-Z]+', Name),
                default('#pop'),
            ],

            'block-comments': [
                # First group parsed by LanguageLexer, second group parsed by root again
                (r'(.+?)(\*/)', bygroups(using(LanguageLexer), Comment.Multiline), '#pop'),
            ],
            'line-comments': [
                # First group parsed by LanguageLexer, second group parsed by root again
                (r'(.+?)(\n)', bygroups(using(LanguageLexer), Text), '#pop'),
            ],
            'verbatim-strings': [
                # This represents 3 groups; the last char before \" will be matched a second time,
                # so we use None to ignore it.
                # TODO: Figure out why it is matched a second time
                (r'((""|[^"])*)(")',
                 bygroups(using(LanguageLexer), None, String), '#pop'),
            ],
            'other-strings': [
                # This represents 3 groups; the last char before \" will be matched a second time,
                # so we use None to ignore it.
                # TODO: Figure out why it is matched a second time
                (r'((\\\\|\\[^\\]|[^"\\\n])*)(["\n])',
                 bygroups(using(LanguageLexer), None, String), '#pop'),
            ]
        }


def run_only_language_lexer(original_file_string):
    textlex = LanguageLexer()
    result = textlex.get_tokens(original_file_string)
    for (token_type, value) in result:
        print(f"token_type: {token_type}, value: {value}")


def run_pygments_lexer(original_file_string):
    my_lexer = CSharpAndCommentsCamelcaseLexer()
    result = my_lexer.get_tokens(original_file_string)
    for (token_type, value) in result:
        print(f"token_type: {token_type}, value: {value}")


if __name__ == "__main__":

    # c_sharp_filepath = "<path/to/file>"
    # with open(c_sharp_filepath, 'r') as file:
    #     original_file = file.read()

    code_string = """class eclipseRCPExt {
    }"""
    run_pygments_lexer(code_string)

    language_string = """CHANGE class 'eclipseRCPExt' to xyz because EclipseRCPExt is too long."""
    run_only_language_lexer(language_string)
