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

    tokens = {
        'root': [
            
            (r"\d", Number),

            # Doing this for indexing in diagnostics
            (r'(?<=[\s\n]\')[^\']+(?=\'[\W])', Name),  # Separates the "'"

            # Words:
            (r'\w+', Text),

            # Formatting
            (r'[\n\s\t\r\v]', Text),
            
            # Punctuation
            (r'[~!%^&*()+=|\'\]\[:;,.<>/?-]', Punctuation),

        ]
    }


class CSharpAndCommentsLexer(UnprocessedTokensMixin, CSharpLexer):
    """
    Since it's difficult to inherit "tokens" from CSharpLexer the way
    it's shown in the documentation (https://pygments.org/docs/lexerdevelopment/#modifying-token-streams),
    this is simply a copy of all the logic in CSharpLexer. Changed are marked
    as OLD/NEW.
    """

    tokens = {}
    token_variants = True

    for levelname, cs_ident in CSharpLexer.levels.items():
        tokens[levelname] = {
            'root': [

                ####### OLD: #######
                # (r'^([ \t]*(?:' + cs_ident + r'(?:\[\])?\s+)+?)'  # return type
                #  r'(' + cs_ident + ')'                            # method name
                #  r'(\s*)(\()',                                    # signature start
                #  bygroups(using(this), Name.Function, Text, Punctuation)),
                ####### NEW: #######
                # return type
                (r'^([ \t]*(?:' + cs_ident + r'(?:\[\])?\s+)+?)'
                 # method name
                 r'(' + cs_ident + ')'
                 # signature start
                 r'(\s*\()',
                 bygroups(using(this), Name.Function, using(this))),
                ####################

                # Avoid bundling too much..
                ####### OLD: #######
                # (r'^\s*\[.*?\]', Name.Attribute),
                ####### NEW: #######
                (r'(?<=\[)\w+(?=\])', Name.Attribute),
                ####################

                # Stop binding formatting:
                ####### OLD: #######
                # (r'[^\S\n]+', Text),
                ####### NEW: #######
                (r'[^\S\n]', Text),  # Inside [], ^ is a negation
                # (r'[\s\t\r\v]', Text),  # Being explicit in what to match
                ####################

                (r'\\\n', Text),  # line continuation

                # Parse comments as natural language (with other lexer)
                ####### OLD: #######
                # (r'//.*?\n', Comment.Single),
                # (r'/[*].*?[*]/', Comment.Multiline),
                ####### NEW: #######
                (r'//', Comment.Single, ('line-comments')),
                (r'/\*', Comment.Multiline, ('block-comments')),
                ####################

                (r'\n', Text),

                # Binding punctuation
                ####### OLD: #######
                # (r'[~!%^&*()+=|\[\]:;,.<>/?-]', Punctuation),
                ####### NEW: #######
                # 3 symbols
                (r'(->\*|>>=|<<=|\.\.\.)', Operator),
                # 2 symbols
                (r'(\+\+|\+=|--|-=|->|&&|&=|\|\||\|=|!=|%=|\*=|==|::|\^=|>=|>>|<=|<<|/=|&&|&=|\^=)', Operator),
                # 1 symbol
                (r'[~!%^&*()+=|\[\]:;,.<>/?-]', Operator),
                ####################

                (r'[{}]', Punctuation),

                # Parse string as natural language (with other lexer)
                ####### OLD: #######
                # (r'@"(""|[^"])*"', String),
                # (r'"(\\\\|\\[^\\]|[^"\\\n])*["\n]', String),
                ####### NEW: #######
                (r'@"', String, ('verbatim-strings')),
                (r'"', String, ('other-strings')),
                ####################

                # No need to change, only one character anyways:
                (r"'\\.'|'[^\\]'", String.Char),

                (r"[0-9](\.[0-9]*)?([eE][+-][0-9]+)?"
                 r"[flFLdD]?|0[xX][0-9a-fA-F]+[Ll]?", Number),

                # Too risky with numbers in pragma or line comments after pragma; simplified
                ####### OLD: #######
                # (r'#[ \t]*(if|endif|else|elif|define|undef|'
                #  r'line|error|warning|region|endregion|pragma)\b.*?\n',
                #  Comment.Preproc),
                ####### NEW: #######
                (r'#[ \t]*(if|endif|else|elif|define|undef|'
                 r'line|error|warning|region|endregion|pragma)', Comment.Preproc),
                ####################

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

                ####### OLD: #######
                # (r'(class|struct)(\s+)', bygroups(Keyword, Text), 'class'),  # \s+ is bundled..
                # (r'(namespace|using)(\s+)', bygroups(Keyword, Text), 'namespace'),
                ####### NEW: #######
                (r'\b(class|struct|namespace|using)\b', Keyword),

                # Avoid bundling whitespace
                (r'(?:(?<=class\W)|(?<=struct\W))\w+', Name.Class),
                (r'(?:(?<=namespace\W)|(?<=using\W))\w+',
                 Name.Class),
                ####################

                (cs_ident, Name),
            ],

            # Not used anymore
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
            ],
            'verbatim-strings': [
                # This represents 3 groups; the last char before \" will be matched a second time,
                # so we use None to ignore it.
                # TODO: Figure out why it is matched a second time
                (r'((""|[^"])*)(")',
                 bygroups(using(LanguageLexer), None, String), '#pop'),

                # (r'(""|[^"])*', using(LanguageLexer)),
                # (r'"', String, '#pop'),
            ],
            'other-strings': [
                # This represents 3 groups; the last char before \" will be matched a second time,
                # so we use None to ignore it.
                # TODO: Figure out why it is matched a second time
                (r'((\\\\|\\[^\\]|[^"\\\n])*)(["\n])',
                 bygroups(using(LanguageLexer), None, String), '#pop'),
            ]
            ####################
        }

    @staticmethod
    def index_identifier_token(token_type, value, index_dict):

        all_name_types = [Name] + [getattr(Name, attribute) for attribute in dir(
            Name) if not attribute.startswith("_") and not attribute.islower()]
        if token_type not in all_name_types:
            return token_type, value

        if value in index_dict:
            return token_type, index_dict[value]

        new_index_name = f"VAR-{len(index_dict.keys())}"
        index_dict[value] = new_index_name
        return token_type, new_index_name


def run_only_language_lexer(original_file_string):
    textlex = LanguageLexer()
    result = textlex.get_tokens(original_file_string)
    for (token_type, value) in result:
        print(f"token_type: {token_type}, value: {value}")


def run_pygments_lexer(original_file_string):
    my_lexer = CSharpAndCommentsLexer()
    result = my_lexer.get_tokens(original_file_string)
    for (token_type, value) in result:
        print(f"token_type: {token_type}, value: {value}")


def run_pygments_lexer_indexed_identifiers(original_file_string):
    index_dict = {}
    my_lexer = CSharpAndCommentsLexer()
    result = my_lexer.get_tokens(original_file_string)
    for (token_type, value) in result:
        (token_type, value) = CSharpAndCommentsLexer.index_identifier_token(
            token_type, value, index_dict)
        print(f"token_type: {token_type}, value: {value}")


if __name__ == "__main__":

    # c_sharp_filepath = "<path/to/file>"
    # with open(c_sharp_filepath, 'r') as file:
    #     original_file = file.read()

    code_string = """class Xyz {
    }"""

    # run_pygments_lexer(code_string)
    
    language_string = """CHANGE class 'eclipseRCPExt' to xyz because EclipseRCPExt is too long."""
    run_only_language_lexer(language_string)
