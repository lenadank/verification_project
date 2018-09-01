

class LineParser(object):

    WS = r"\s+"

    def __init__(self, rules=[], whitespace=WS):
        self.WS = whitespace
        self.syntax = list(self._syntax(rules))
        
    def parse_line(self, line):
        line = line.strip()
        for regexp, symbol_name in self.syntax:
            mo = regexp.match(line)
            if mo is not None:
                return symbol_name, mo.groupdict()
        else:
            raise SyntaxError, "parse error in expression '%s'" % (line,)

    def __call__(self, line):
        return self.parse_line(line)

    def _rule2re(self, rule):
        import re
        if isinstance(rule, str):
            return rule
        elif isinstance(rule, tuple):
            tok, tag = rule
            return "(?P<%s>%s)" % (tag, self._rule2re(tok))
        elif isinstance(rule, list):
            join = self.WS.join(self._rule2re(x) for x in rule)
            try:
                return re.compile(join + "$")
            except:
                raise SyntaxError, "error in regexp '%s' for rule %r" % (join, rule)
        
    def _syntax(self, named_rules):
        for symbol_name, rule in named_rules:
            yield self._rule2re(rule), symbol_name
            


class Z3OutputFormat(object):
    
    ID = r"[a-zA-Z_?][a-zA-Z0-9_!'?]*"
    IDS = ID + r"(\s" + ID + r")*"
    FREETEXT = r".*"
    
    RULES = [('else-value', ["else", "->", (ID,'rhs')]),
             ('single-value', [(ID,'lhs'), "->", (ID,'rhs')]),
             ('multiple-value', [(IDS,'lhs'), "->", (ID,'rhs')]),
             ('compound-value-{', [(ID,'lhs'), "->", "{"]),
             ('compound-value-}', ["}"]),
             ('warning', ["WARNING:", (FREETEXT,'msg')]),
             ('timeout', ["timeout"]),
             ('unknown', ["unknown"]),
             ('sat', ["sat"]),
             ('unsat', ["unsat"])]

    RESERVED = {'true': True, 'false': False}

    def __init__(self):
        self.parser = LineParser(self.RULES)

    def structure(self, lines):
        sm = {}
        stack = [sm]
        for line in lines:
            symbol_name, elements = self.parser.parse_line(line)
            if symbol_name == 'single-value':
                lhs, rhs = elements['lhs'], elements['rhs']
                rhs = self.RESERVED.get(rhs, rhs)
                stack[-1][lhs] = rhs
            elif symbol_name == 'multiple-value':
                lhs, rhs = elements['lhs'], elements['rhs']
                lhs = tuple(lhs.split(" "))
                rhs = self.RESERVED.get(rhs, rhs)
                stack[-1][lhs] = rhs
            elif symbol_name == 'compound-value-{':
                lhs = elements['lhs']
                stack[-1][lhs] = cv = {}
                stack.append(cv)
            elif symbol_name == 'compound-value-}':
                if len(stack) <= 1:
                    raise ValueError, "unbalanced '{ }' brackets"
                stack.pop()
            elif symbol_name == 'timeout':
                raise RuntimeError, "Z3 SMT solver timed out"
            elif symbol_name == 'unsat':
                raise Unsatisfiable, "no model for Z3 input formula" 
        if len(stack) != 1:
            raise ValueError, "unterminated '{' bracket (at end of file)"
        return sm
    
    
class Unsatisfiable(RuntimeError):
    pass


if __name__ == "__main__":
    f = Z3OutputFormat()
    print f.structure(["a -> true", "?q!0 -> val!0", "ar -> {", "val!0 val!1 -> true", "}"])
