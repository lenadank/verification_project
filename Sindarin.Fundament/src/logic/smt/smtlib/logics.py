
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.semantics.extensions.po import FolNaturalPartialOrder
from logic.fol.semantics.extensions.arith import FolIntegerArithmetic



class AUFLIA:
    """
    Arrays, Uninterpreted Functions, Linear Integer Arithmetic
    
    Closed formulas over the theory of linear integer arithmetic and arrays 
    extended with free sort and function symbols but restricted to arrays with
    integer indices and values. 
    """
    
    class Signature(FolWithEquality.Signature, FolNaturalPartialOrder, FolIntegerArithmetic):
        pass

    _ = Signature
    SMTLIB_BUILTINS = {_.add: "+", _.mul: "*", _.sub: "-", _.div: "/", _.neg: "-",
                       _.gt: ">", _.le: "<=", _.lt: "<", _.ge: ">=", 'ite': 'ite'}

