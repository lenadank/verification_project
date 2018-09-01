

class LaTeX(object):
    def to_latex(self):
        return r"\latex" 


class VerbatimText(LaTeX):
    def __init__(self, text=""):
        self.text = text
    def to_latex(self):
        return r"\begin{verbatim}%s\end{verbatim}" % self.text


def latex(obj):
    if isinstance(obj, LaTeX):
        return obj.to_latex()
    else:
        return VerbatimText(str(obj)).to_latex()