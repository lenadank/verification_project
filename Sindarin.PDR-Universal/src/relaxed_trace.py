from z3 import *

from z3support.vocabulary import Z3Alphabet, Z3Renaming, Z3TwoVocabulary

RELAX_TRACE_AND_BAD = 1
RELAX_TRACE_NOT_BAD = 2
NO_RELAX_TRACE = 3

VAR_VERSION_SEP = "_"
DEBUG=False

class Relaxed_Trace_Analyzer():
    def __init__(self, init, rho, bad, background, globals, locals, relations, constants, N):
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
        self.n_star_is_global = False
        self.spare_variables = []
        self.rebased_delta = None
        self.rebased_bad = bad
        self.rebased_background = background
        self.constants = constants
        self.preprocess()

    def preprocess(self):
        for item in self.globals + self.relations:
            if is_func_decl(item) and str(item) == "n*":
                self.n_star = item
                self.n_star_is_global = True

        for item in self.locals:
            if is_func_decl(item[1]) and str(item[1]) == "n*":
                self.n_star = item[1]
                self.n_star_is_global = False

        assert not self.n_star is None, "n* is not defined as a function"
        max_arity = 1
        indices = [str(i) for i in xrange(2 * self.N + 1)]
        all_variables = list()
        all_variables.extend(self.globals)
        var_sort = None
        for item in self.locals:
            var = str(item[1])
            const_str = var + VAR_VERSION_SEP + (" " + var + VAR_VERSION_SEP).join(indices)
            if is_const(item[1]):
                if DEBUG:
                    print ("Const: %s (%s)" % (str(item[1]), item[1].sort()))
                self.var_dict[var] = Consts(const_str, item[1].sort())
                all_variables.append(item[1])
            elif is_func_decl(item[1]):
                sorts = [item[1].domain(i) for i in range(item[1].arity())] + [item[1].range()]
                if DEBUG:
                    print ("Relation: %s (%s)" % (str(item[1]), str(sorts)))
                if var_sort is None:
                    var_sort = sorts[0]
                self.var_dict[var] = self.Functions(const_str, sorts)
                max_arity = max(max_arity, item[1].arity())

        #add all global predicates/constant to globals:
        for item in self.relations:
            if not str(item) in self.var_dict:
                if not item in self.globals:
                    self.globals.append(item)

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
        if DEBUG:
            print "-- spare_variables --"
            for z in self.spare_variables:
                print("%s (%s)" % (str(z), z.sort()))
        self.rebased_init = self.init
        self.rebased_rho = self.rho
        for (v0, v) in self.locals:
            # replace v0 with v_0, replace v with v_1
            # rebase init to the _0 set of variables
            self.rebased_init = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.get_rebased_name(v, 0)]))(self.rebased_init)
            self.rebased_rho = Z3Renaming(Z3Alphabet([v0]), Z3Alphabet([self.get_rebased_name(v, 0)]))(self.rebased_rho)
            self.rebased_rho = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.get_rebased_name(v, 1)]))(self.rebased_rho)
            #rebase bad to the last set of variables
            self.rebased_bad = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.get_rebased_name(v, 2 * self.N - 1)]))(self.rebased_bad)
            #rebase background, replace v0 with v_0, replace v with v_1
            self.rebased_background = Z3Renaming(Z3Alphabet([v0]), Z3Alphabet([self.get_rebased_name(v, 0)]))(self.rebased_background)
            self.rebased_background = Z3Renaming(Z3Alphabet([v]), Z3Alphabet([self.get_rebased_name(v, 1)]))(self.rebased_background)

        self.rebased_delta = self.delta(2)
        if DEBUG:
            print "DEBUG: rebased_init, variables copy number:", 0
            print "DEBUG: rebased_rho, variables copy number:", 1
            print "rebased_background, variables copy number:", 0

    def get_rebased_name(self, var, phase_num):
        # some times n_star is a global mathod, so it doesn't need to rebase, but we do it in the active function so this case need to be taked care of
        if var is self.n_star:
            return var if var not in self.var_dict else self.var_dict[str(var)][phase_num]
        else:
            return self.var_dict[str(var)][phase_num]

    def active(self, n_func, e, all_variables):
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
        curr_n_star = self.get_rebased_name(self.n_star, phase_num)
        for var in self.locals:
            past_var = self.get_rebased_name(var[1], phase_num - 1)
            present_var = self.get_rebased_name(var[1], phase_num)
            past_present_tuples.append((past_var, present_var))
        for var in self.globals:
            if is_func_decl(var):
                past_present_tuples.append((var, var))
            if is_const(var):
                all_variables.append(var)
        for past, present in past_present_tuples:
            if is_const(past) and past.sort().kind() != Z3_BOOL_SORT:
                all_variables.append(present)
                sub_forms_var.append(self.bid_implies(past == z1, present == z1))
            elif is_func_decl(past):
                arity = past.arity()
                sub_vars = self.spare_variables[:arity]
                bi_dir_equality = self.bid_implies(past(*sub_vars), present(*sub_vars))
                # skip the first variable in the ForAll clause because its aleady bounded
                active_and_equal = Implies(self.all_active(curr_n_star, sub_vars, all_variables), bi_dir_equality)
                if arity == 1: #no need to add additional bounded variables
                    sub_forms_rel.append(active_and_equal)
                else:
                    sub_forms_rel.append(ForAll(sub_vars[1:], active_and_equal))
        if DEBUG:
            print "all constants: " + str(all_variables)
        # take care of the globals
        all_constants_formula = And(sub_forms_var)
        all_relations_formula = And(sub_forms_rel)
        # all_relations_formula = True
        formula = ForAll([z1], Implies(self.active(curr_n_star, z1, all_variables), And(all_constants_formula, all_relations_formula)))
        return formula

    def Functions(self, names, sort_List):
        if isinstance(names, str):
            names = names.split(" ")
        return [Function(name, *sort_List) for name in names]

    #considers even gaps
    def change_names(self, next_n, formula):
        if (next_n <= 2):
            return formula
        for (v0, v) in self.locals:
            past_1 = self.get_rebased_name(v, next_n - 2)
            past_2 = self.get_rebased_name(v, next_n - 3)
            present_1 = self.get_rebased_name(v, next_n)
            present_2 = self.get_rebased_name(v, next_n - 1)
            formula = Z3Renaming(Z3Alphabet([past_1, past_2]), Z3Alphabet([present_1, present_2]))(formula)
        return formula


    def promote_names(self, next_n, formula):
        if (next_n < 2):
            return formula
        for (v0, v) in self.locals:
            past_1 = self.get_rebased_name(v, next_n - 1)
            past_2 = self.get_rebased_name(v, next_n - 2)
            present_1 = self.get_rebased_name(v, next_n)
            present_2 = self.get_rebased_name(v, next_n - 1)
            formula = Z3Renaming(Z3Alphabet([past_1, past_2]), Z3Alphabet([present_1, present_2]))(formula)
        return formula


    def run(self):
        phi_solver = Solver()
        elements_for_phi = list()
        elements_for_phi.append(self.rebased_background)
        elements_for_phi.append(self.rebased_init)
        elements_for_phi.append(self.rebased_rho)
        for i in xrange(self.N -1):
            #rebased_delta = self.delta(2*(i+1))
            self.rebased_delta = self.change_names(2*(1+i), self.rebased_delta)
            self.rebased_rho = self.change_names(2*(1+i) + 1, self.rebased_rho)
            if DEBUG:
                print "DEBUG: rebased_delta, variables copy number:", 2*(1+i)
                print "DEBUG: rebased_rho, variables copy number:", 2*(1+i)+1

            elements_for_phi.append(self.rebased_delta)
            elements_for_phi.append(self.rebased_rho)
        if DEBUG:
            print "rebased_bad, variables copy number:", 2*self.N-1

        #last step would be to promote to 2N-1, same as base
        for i in xrange(2, 2*self.N):
            if DEBUG:
                print "rebased_background, variables copy number:", i
            elements_for_phi.append(self.promote_names(i, self.rebased_background))
            phi_solver.add(*elements_for_phi)
        phi_sat = phi_solver.check()
        if sat == phi_sat:
            #print(phi_solver.model())
            print("*" * 60)
            phi_and_bad_solver = Solver()
            phi_and_bad_solver.add(*elements_for_phi)
            phi_and_bad_solver.add(self.rebased_bad)
            phi_and_bad_sat = phi_and_bad_solver.check()
            if sat == phi_and_bad_sat:
                print("***  found relaxed trace for depth=%d, bad is safisfied ----" % self.N)
                self.print_model(phi_solver.model())
                ret_val = RELAX_TRACE_AND_BAD
            else:
                print("***  found relaxed trace for depth=%d, bad is unsafisfied " % self.N)
                """
                model = phi_solver.model()
                for d in model:
                    print("%s %s" % (d.name(), model[d]))
                """
                ret_val = RELAX_TRACE_NOT_BAD

        else:
            print("***  unable to find relaxed trace for depth=%d" % self.N)
            ret_val = NO_RELAX_TRACE
        print("*" * 60)
        return ret_val

    def print_model(self, model):
        keys_to_string_map = dict()
        for d in model:
            keys_to_string_map[d.name()] = d
        print("globals:")
        for g in self.globals:
            val = keys_to_string_map.get(str(g), None)
            if not val is None:
                print("\t%s %s" % (str(g), str(model[val])))
        print("locals:")
        #starting with 0 (init) and then go over the odd indices
        indices = [0]+ range(1, 2*self.N, 2)
        for i in indices:
            if i == 0:
                print("initial state:")
            else:
                print("iteration %d" % ((i+1)/2))
            for g in self.var_dict:
                iteration_version = self.get_rebased_name(g, i)
                val = keys_to_string_map.get(str(iteration_version), None)
                if not val is None:
                    print("\t%s %s" % (str(iteration_version), str(model[val])))

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

    r_t_analyzer = Relaxed_Trace_Analyzer(init, rho, bad, background, globals, locals, [n], 3)
    r_t_analyzer.run()
