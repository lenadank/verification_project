
from tcs.rewrite_systems.of_trees import TreeRewriteRule
from logic.fol.syntax.scheme import FolPatternSubstitution



class FolFormulaRewriteRule(TreeRewriteRule):
    
    TreePatternSubstitution = FolPatternSubstitution
    
    def __init__(self, premise, replacement):
        """
        @param premise: a FolScheme instance
        @param replacement: a FolFormula instance (with placeholders where 
          matched values should go), or a FolPatternSubstitution.Substitution 
          instance for advanced processing capabilities.
        """
        super(FolFormulaRewriteRule, self)\
            .__init__(premise.pattern, replacement)


