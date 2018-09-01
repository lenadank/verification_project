from z3 import *

from z3support.vocabulary import Z3Alphabet, Z3Renaming, Z3TwoVocabulary

class Relaxed_Trace_Analyzer():
    def __init__(self, init, rho, bad, background, globals, locals, relations, N):
        self.init = init;
        self.rho = rho
        self.bad = bad
        self.background = background;
        self.globals = globals;
        self.locals = locals;
        self.relations = relations;
        self.N = N;
        self.var_dict = dict()
        self.rebased_init = init
        self.rebased_rho = rho
        self.n_star = None
        self.spare_variables = []
        self.rebased_delta = None
        self.rebased_bad = bad
        self.preprocess()

    def preprocess(self):
        for item in self.globals + self.relations:
            if is_func_decl(item) and str(item) == "n*":
                self.n_star = item

        for item in self.locals:
            if is_func_decl(item[1]) and str(item[1]) == "n*":
                self.n_star = item[1]

        assert not self.n_star is None, "n* is not defined as a function"

        max_arity = 1
        indices = [str(i) for i in xrange(2 * self.N + 1)]
        all_variables = list()
        all_variables.extend(self.globals)
        var_sort = None
        for item in self.locals:
            var = str(item[1])
            const_str = var + "_" + (" " + var + "_").join(indices)
            if is_const(item[1]):
                self.var_dict[var] = Consts(const_str, item[1].sort())
                all_variables.append(item[1])
            elif is_func_decl(item[1]):
                sorts = [item[1].domain(i) for i in range(item[1].arity())] + [item[1].range()]
                if var_sort is None:
                    var_sort = sorts[0]
                self.var_dict[var] = self.Functions(const_str, sorts)
                max_arity = max(max_arity, item[1].arity())

        for item in self.globals:
            if is_func_decl(item):
                if var_sort is None:
                    var_sort = item.domain(0)
                max_arity = max(max_arity, item.arity())

        for item in self.relations:
            if is_func_decl(item):
                if var_sort is None:
                    var_sort = item.domain(0)
                max_arity = max(max_arity, item.arity())


        self.spare_variables = Consts(" ".join(["z" + str(i + 1) for i in range(max_arity + 1)]), var_sort)

        self.rebased_init = self.init
        self.rebased_rho = self.rho
        for (v0, v) in self.locals:
            #replace v0 with v_0, replace v with v_1
            self.rebased_init = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.var_dict[str(v)][0]]))(self.rebased_init)
            self.rebased_rho = Z3Renaming(Z3Alphabet([v0]), Z3Alphabet([self.var_dict[str(v)][0]]))(self.rebased_rho)
            self.rebased_rho = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.var_dict[str(v)][1]]))(self.rebased_rho)
            self.rebased_bad = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.var_dict[str(v)][2*self.N]]))(self.rebased_bad)


        self.rebased_delta = self.delta(2)

    def active(self, n_func, e, all_variables):
        # formula = n_func(all_variables[0], e)
        formula = Or([n_func(var, e) for var in all_variables])
        return formula

    def all_active(self, n_func, e_list, all_variables):
        return And([self.active(n_func, e, all_variables) for e in e_list])

    def bid_implies(self, part1, part2):
        return And(Implies(part1, part2), Implies(part2, part1))

    def delta(self, phase_num):
        z1 = self.spare_variables[0]
        all_variables = []
        sub_forms_var = []
        sub_forms_rel = []
        past_present_tuples = []
        for var in self.locals:
            past_var = self.var_dict[str(var[1])][phase_num - 1];
            present_var = self.var_dict[str(var[1])][phase_num]
            past_present_tuples.append((past_var, present_var))
        for var in self.globals:
            if is_func_decl(var):
                past_present_tuples.append((var, var))
        for past, present in past_present_tuples:
            if is_const(past) and past.sort().kind() != Z3_BOOL_SORT:
                all_variables.append(present)
                sub_forms_var.append(self.bid_implies(past == z1, present == z1))
            elif is_func_decl(past):
                arity = past.arity()
                sub_vars = self.spare_variables[:arity]
                bi_dir_equality = self.bid_implies(past(*sub_vars), present(*sub_vars))
                # skip the first variable in the ForAll clause because its aleady bounded
                sub_forms_rel.append(
                    ForAll(sub_vars[1:], Implies(self.all_active(self.n_star, sub_vars, all_variables), bi_dir_equality)))

        # take care of the globals

        all_constants_formula = And(sub_forms_var)
        all_relations_formula = And(sub_forms_rel)
        # all_relations_formula = True
        formula = ForAll([z1], Implies(self.active(self.n_star, z1, all_variables), And(all_constants_formula, all_relations_formula)))
        return formula

    def Functions(self, names, sort_List):
        if isinstance(names, str):
            names = names.split(" ")
        return [Function(name, *sort_List) for name in names]

    def change_names(self, next_n, formula):
        if (next_n <= 2):
            return formula
        for (v0, v) in self.locals:
            past_1 = self.var_dict[str(v)][next_n - 2]
            past_2 = self.var_dict[str(v)][next_n - 3]
            present_1 = self.var_dict[str(v)][next_n]
            present_2 = self.var_dict[str(v)][next_n - 1]
            formula = Z3Renaming(Z3Alphabet([past_1, past_2]), Z3Alphabet([present_1, present_2]))(formula)
        return formula

    def run(self):
        solver = Solver()
        print("backgroud", self.background)
        solver.add(self.background)
        solver.add(self.rebased_init)
        solver.add(self.rebased_rho)
        for i in xrange(self.N -1):
            #rebased_delta = self.delta(2*(i+1))
            self.rebased_delta = self.change_names(2*(1+i), self.rebased_delta)
            self.rebased_rho = self.change_names(2*(1+i) + 1, self.rebased_rho)
            solver.add(self.rebased_delta)
            solver.add(self.rebased_rho)
        solver.add(self.rebased_bad)
        print(solver.check())
        #print(solver.model())
        print("done!")




if __name__ == '__main__':
    A = IntSort()
    B = BoolSort()
    n = Function('n*', A, A, B)


    def nPlus(x, y):
        return And(x != y, n(x, y))


    N = 3
    x, y, l, h, x0, z = Consts('x y l h x0 z', A)
    init    = And(x == h, Implies(n(h, y), nPlus(y, l)))
    rho     = And(nPlus(x0, x), ForAll([z], Implies(nPlus(x,z),n(x0,z))))
    bad     = And(x == y, x == l)
    background = ForAll([z], n(z,z))
    globals = [y, l, h, n]    # @ReservedAssignment
    locals  = [(x0,x)]  # @ReservedAssignment

    r_t_analyzer = Relaxed_Trace_Analyzer(init, rho, bad, background, globals, locals, [n], 2)
    r_t_analyzer.run()
