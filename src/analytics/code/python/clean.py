from sklearn.base import BaseEstimator, TransformerMixin
import io, tokenize
import numpy as np
import re

class CleanPythonPreprocessor(BaseEstimator, TransformerMixin):

    def __init__(self, remove_comments_and_docstrings=True, normalize_whitespace=True):
        self.remove_comments_and_docstrings = remove_comments_and_docstrings
        self.normalize_whitespace = normalize_whitespace

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        return np.array([
            clean_source_code(x, self.remove_comments_and_docstrings, self.normalize_whitespace)
            for x in X
        ])

def __remove_via_regex(source: str) -> str:
    pattern = r'''^[ \t]*(#.*\n|"""[\s\S]*?"""\n?|\'\'\'[\s\S]*?\'\'\'\n?)'''

    source = re.sub(pattern, "", source, flags=re.MULTILINE)
    return source

def __strip_double_newlines(source: str) -> str:
    pattern = r'\n(\s*\n)+'
    source = re.sub(pattern, "\n", source)
    return source

def __remove_via_parsing(source: str) -> str:
    io_obj = io.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        # ltext = tok[4]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype != tokenize.INDENT:
                if prev_toktype != tokenize.NEWLINE:
                    if start_col > 0:
                        out += token_string
        else:
            out += token_string
        prev_toktype = token_type
        last_col = end_col
        last_lineno = end_line
    out = '\n'.join(l for l in out.splitlines() if l.strip())
    return out

def clean_source_code(source: str,
          remove_comments_and_docstrings: bool = True,
          normalize_whitespace: bool = True
          ) -> str:
    """

    """
    # TODO: The parsing stripper also does something weird with
    # spacing that I don't like, so I'm not using it for now
    # try:
    #     stripped = PythonPreprocessor.__remove_via_parsing(source)
    # except:
    if remove_comments_and_docstrings:
        stripped = __remove_via_regex(source)
    if normalize_whitespace:
        stripped = __strip_double_newlines(stripped)
        stripped = stripped.replace("\t", "    ")
    return stripped

def _test_clean_source_code():
    for i, test in enumerate(__tests):
        print(f"# Test {i}")
        print(test)
        stripped = CleanPythonPreprocessor.remove_comments_and_docstring(test)
        print(stripped)
        re_stripped = CleanPythonPreprocessor.__remove_via_regex(test)
        if stripped.strip() != re_stripped.strip():
            print("Regex and parsing don't match!")
            print("Regex:")
            print(re_stripped)
        print("\n\n")


__tests = [
'''
def example_function():
    string_with_comment = "This is a string with a # comment character inside."
    print(string_with_comment)
''',
'''
def example_function():
    string_with_comment = "This is a string with a # comment character inside."  # This is a comment
    print(string_with_comment)
''',
'''
def example_function():
    string_with_docstring = "This is a string with a triple-quoted docstring inside. ''\' Docstring \'''"
    print(string_with_docstring)
''',
'''
def example_function():
    complex_string = \'''
        This is a triple-quoted string with escaped quotes: \\"quote\\".
        And here's a comment inside: # Comment
    \'''
    print(complex_string)
''',
'''
def example_function():
    multiline_string = ''\'
        This is a multiline string.
        Line 2 with a comment: # Comment
        Line 3.
    \'''
    print(multiline_string)
''',
'''
def example_function():
    single_quoted_docstring = \'\'\'Single-quoted docstring\'\'\'
    double_quoted_docstring = \"\"\"Double-quoted docstring\"\"\"
    mixed_quoted_docstring = \'\'\'Mixed-quoted docstring with "quotes"\'\'\'
    print(single_quoted_docstring, double_quoted_docstring, mixed_quoted_docstring)
''',
'''
def valid(s, alphabet):
    """ (str, str) -> bool

    Return True iff s is composed only of characters in alphabet.

    >>> valid('adc', 'abcd')
    True
    >>> valid('ABC', 'abcd')
    False
    >>> valid('abc', 'abz')
    False
    """
    for x in s:
        if x.lower() not in alphabet.lower():
            return False
    return True
'''
]