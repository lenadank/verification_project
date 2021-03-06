from z3 import *
import itertools

from z3support.vocabulary import Z3Alphabet, Z3Renaming, Z3ActiveBoundedVariables

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
        self.local_name_to_var_dict = dict()
        self.active_func = None
        self.rebased_active_for_rho = None
        self.rebased_active_for_delta = None
        self.all_variables = []
        self.preprocess()

    def preprocess(self):
        LAST_PHASE_NUM = 2*self.N
        for item in self.globals + self.relations:
            if is_func_decl(item) and str(item) == "n*":
                self.n_star = item
                self.n_star_is_global = True

        for item in self.locals:
            if is_func_decl(item[1]) and str(item[1]) == "n*":
                self.n_star = item[1]
                self.n_star_is_global = False

        #add active function

        self.active_func = Function("__active__", self.n_star.domain(0), self.n_star.range())
        temp_next_active = Function("__active0__", self.n_star.domain(0), self.n_star.range())
        self.locals.append((temp_next_active, self.active_func))

        assert not self.n_star is None, "n* is not defined as a function"
        max_arity = 1
        indices = [str(i) for i in xrange(2 * self.N + 1)]
        all_variables = list()
        all_variables.extend(self.globals)
        var_sort = None
        for prev, curr in self.locals:
            var = str(curr)
            const_str = var + VAR_VERSION_SEP + (" " + var + VAR_VERSION_SEP).join(indices)
            if is_const(curr):
                if DEBUG:
                    print ("Const: %s (%s)" % (str(curr), curr.sort()))
                self.var_dict[var] = Consts(const_str, curr.sort())
                all_variables.append(curr)
            elif is_func_decl(curr):
                sorts = [curr.domain(i) for i in range(curr.arity())] + [curr.range()]
                if DEBUG:
                    print ("Relation: %s (%s)" % (str(curr), str(sorts)))
                if var_sort is None:
                    var_sort = sorts[0]
                self.var_dict[var] = self.Functions(const_str, sorts)
                max_arity = max(max_arity, curr.arity())
            self.local_name_to_var_dict[str(var)] = var

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
        for (prev, curr) in self.locals:
            # replace v0 with v_0, replace v with v_1
            # rebase init to the _0 set of variables
            self.rebased_init = Z3Renaming(Z3Alphabet([curr]), Z3Alphabet([self.get_rebased_name(curr, 0)]))(self.rebased_init)
            self.rebased_rho = Z3Renaming(Z3Alphabet([prev]), Z3Alphabet([self.get_rebased_name(curr, 0)]))(self.rebased_rho)
            self.rebased_rho = Z3Renaming(Z3Alphabet([curr]), Z3Alphabet([self.get_rebased_name(curr, 1)]))(self.rebased_rho)
            #rebase bad to the last set of variables
            self.rebased_bad = Z3Renaming(Z3Alphabet([curr]), Z3Alphabet([self.get_rebased_name(curr, LAST_PHASE_NUM)]))(self.rebased_bad)
            #rebase background, replace v0 with v_0, replace v with v_1
            self.rebased_background = Z3Renaming(Z3Alphabet([curr]), Z3Alphabet([self.get_rebased_name(curr, 1)]))(self.rebased_background)
            self.rebased_background = Z3Renaming(Z3Alphabet([prev]), Z3Alphabet([self.get_rebased_name(curr, 0)]))(self.rebased_background)

        self.rebased_delta = self.delta(2)
        self.rebased_active_for_rho = self.active_for_rho(1)
        self.rebased_init = And(self.rebased_init, self.active_for_init())
        if DEBUG:
            print "DEBUG: rebased_init, variables copy number:", 0
            print "DEBUG: rebased_rho, variables copy number:", 1
            print "rebased_background, variables copy number:", 0

        #replace all quantifies to include active condition
        curr_active_func = self.get_rebased_name(self.active_func, 1)
        self.rebased_rho = Z3ActiveBoundedVariables(curr_active_func)(self.rebased_rho)
        self.rebased_background = Z3ActiveBoundedVariables(curr_active_func)(self.rebased_background)
        active_func_for_bad = self.get_rebased_name(self.active_func, LAST_PHASE_NUM)
        self.rebased_bad = Z3ActiveBoundedVariables(active_func_for_bad)(self.rebased_bad)

    def active_for_init(self):
        assert(self.all_variables != [])

        phase_num = 0;
        curr_active_func = self.get_rebased_name(self.active_func, phase_num)

        # ForAll(ac1, active(ac1)
        z1 = self.spare_variables[0]
        ac1 = Const("ac1", z1.sort())
        cond = ForAll(ac1, curr_active_func(ac1))
        return cond


    def active_for_rho(self, phase_num):
        #for rho the active don't change
        curr_active_func = self.get_rebased_name(self.active_func, phase_num)
        prev_active_func = self.get_rebased_name(self.active_func, phase_num-1)
        z1 = self.spare_variables[0]
        ac1 = Const("ac1", z1.sort())
        bid_equal =  self.bid_implies(curr_active_func(ac1), prev_active_func(ac1))
        return ForAll(ac1, bid_equal)



    def active_for_delta(self, phase_num):
        assert(self.all_variables != [])
        curr_active_func = self.get_rebased_name(self.active_func, phase_num)
        prev_active_func = self.get_rebased_name(self.active_func, phase_num-1)
        z1 = self.spare_variables[0]
        ac1 = Const("ac1", z1.sort())
        # !prev_active(ac1) -> !curr_active(ac1)
        cond1 = ForAll(ac1, Implies(Not(prev_active_func(ac1)), Not(curr_active_func(ac1))))

        # Exist(c, c == ac1) -> curr_active(ac1)
        some_var_points_to_ac1 = Or(*[x == ac1 for x in self.all_variables])
        cond2 = Implies(some_var_points_to_ac1, curr_active_func(ac1))
        return ForAll(ac1, And(cond1, cond2))



    def get_rebased_name(self, var, phase_num):
        # some times n_star is a global mathod, so it doesn't need to rebase, but we do it in the active function so this case need to be taked care of
        if var is self.n_star:
            return var if str(var) not in self.var_dict else self.var_dict[str(var)][phase_num]
        else:
            return self.var_dict[str(var)][phase_num]

    def bid_implies(self, part1, part2):
        return And(Implies(part1, part2), Implies(part2, part1))

    def delta(self, phase_num):
        z1 = self.spare_variables[0]
        m1 = Const("m1", z1.sort())

        sub_forms_var = []
        sub_forms_rel = []
        past_present_tuples = []
        curr_n_star = self.get_rebased_name(self.n_star, phase_num)
        prev_n_star = self.get_rebased_name(self.n_star, phase_num-1)

        curr_active_func = self.get_rebased_name(self.active_func, phase_num)

        for prev, curr in self.locals:
            #ignore active in the equations
            if str(curr) == str(self.active_func):
                continue
            past_var = self.get_rebased_name(curr, phase_num - 1)
            present_var = self.get_rebased_name(curr, phase_num)
            past_present_tuples.append((past_var, present_var))
        for var in self.globals:
            if is_func_decl(var):
                pass
                #past_present_tuples.append((var, var))
            if is_const(var):
                self.all_variables.append(var)
        functions = []
        for past, present in past_present_tuples:
            if is_const(past):
                if  past.sort().kind() != Z3_BOOL_SORT:
                    self.all_variables.append(present)
                    sub_forms_var.append(past == present)
                else:
                    sub_forms_var.append(self.bid_implies(past, present))
            elif is_func_decl(past):
                functions.append((past, present))
            else:
                raise ValueError(str(past) + " is neither a constant nor a function")


        if DEBUG:
            print "all constants: " + str(self.all_variables)
        all_constants_are_equal_formula = And(sub_forms_var)

        #make sure there are no new edges in the new graph:
        no_new_edges = ForAll([z1, m1], Implies(curr_n_star(z1, m1), prev_n_star(z1, m1)))

        for past, present in functions:
            arity = past.arity()
            sub_vars = self.spare_variables[:arity]
            bi_dir_equality = self.bid_implies(past(*sub_vars), present(*sub_vars))
            # skip the first variable in the ForAll clause because its aleady bounded
            active_and_equal = Implies(And(*[curr_active_func(x) for x in sub_vars]), bi_dir_equality)
            sub_forms_rel.append(ForAll(sub_vars, active_and_equal))

        active_maintain_relations = And(*sub_forms_rel)
        formula = And(all_constants_are_equal_formula, no_new_edges, active_maintain_relations)
        self.rebased_active_for_delta = self.active_for_delta(phase_num)
        return formula

    def Functions(self, names, sort_List):
        if isinstance(names, str):
            names = names.split(" ")
        return [Function(name, *sort_List) for name in names]



    def promote_names(self, index_pairs, formula):
        if len(index_pairs) == 0:
            return formula
        pasts = []
        presents = []
        for (next, curr) in self.locals:
            for index_pair in index_pairs:
                past = self.get_rebased_name(curr, index_pair[0])
                present = self.get_rebased_name(curr, index_pair[1])
                pasts.append(past)
                presents.append(present)
        formula = Z3Renaming(Z3Alphabet(pasts), Z3Alphabet(presents))(formula)
        return formula



    def get_all_vars_recursively(self, formula):
        if is_func_decl(formula):
            """
            term_prime = self.d.get(get_id(term), term)
            #print self.d
            #print term, "--->", term_prime
            return term_prime
            """
            raise Exception()
        if is_quantifier(formula):
            #vars = [formula.var_name(i) for i in xrange(formula.num_vars())]
            return self.get_all_vars_recursively(formula.body())
        else:
            res = []
            children = formula.children()
            if len(children) == 0:
                return [str(formula)]
            for ch in formula.children():
                res.extend(self.get_all_vars_recursively(ch))
            res.append(str(formula.decl()))
            return res


    def get_var_versions(self, formula):
        """
        This is a helper function for debugging only. It gets a formula and returns the variable versions used in
        this formula. For example, if it contains n*_0 or x_1, this method will return the indices 0 and 1.
        """
        res = set()
        all_vars = self.get_all_vars_recursively(formula)
        for var in all_vars:
            var_split = var.split("_")
            if len(var_split) > 1:
                res.add(int(var_split[-1]))
        return tuple(sorted(res))


    def run_phi_delta(self):
        phi_solver = Solver()
        elements_for_phi = list()
        elements_for_phi.append(self.rebased_init)
        elements_for_phi.append(self.rebased_background) # (0,1)
        elements_for_phi.append(self.rebased_active_for_rho) #(0,1)
        elements_for_phi.append(self.rebased_rho) # (0,1)
        elements_for_phi.append(self.rebased_delta) # (1,2)
        elements_for_phi.append(self.rebased_active_for_delta) # (1,2)
        new_active_for_rho = self.rebased_active_for_rho #(0,1)
        new_rho = self.rebased_rho # (0,1)
        new_delta = self.rebased_delta # (1,2)
        new_active_for_delta = self.rebased_active_for_delta # (1,2)
        if DEBUG:
            print("rho", self.get_var_versions(new_rho))
            print("delta", self.get_var_versions(new_delta))
        new_background = self.rebased_background # (0,1)
        for i in xrange(1, self.N):
            real_i = 2*(i-1)+1

            new_rho = self.promote_names([(real_i-1, real_i+1), (real_i, real_i+2)], new_rho)
            new_background = self.promote_names([(real_i-1, real_i+1), (real_i, real_i+2)], new_background)
            new_active_for_rho = self.promote_names([(real_i-1, real_i+1), (real_i, real_i+2)], new_active_for_rho)
            if DEBUG:
                print("rho", self.get_var_versions(new_rho))
            elements_for_phi.append(new_rho)
            elements_for_phi.append(new_active_for_rho)
            elements_for_phi.append(new_background)


            new_delta = self.promote_names([(real_i, real_i+2) ,(real_i+1, real_i+3)], new_delta)
            new_background = self.promote_names([(real_i, real_i+2) ,(real_i+1, real_i+3)], new_background)
            new_active_for_delta = self.promote_names([(real_i, real_i+2) ,(real_i+1, real_i+3)], new_active_for_delta)

            if DEBUG:
                print("delta", self.get_var_versions(new_delta))
            elements_for_phi.append(new_delta)
            elements_for_phi.append(new_active_for_delta)
            elements_for_phi.append(new_background)

        if DEBUG:
            print("bad", self.get_var_versions(self.rebased_bad))
        phi_solver.add(*elements_for_phi)
        phi_solver.add(self.rebased_bad)
        phi_sat = phi_solver.check()
        print("*" * 60)
        if sat == phi_sat:
            print("***  found relaxed trace for depth=%d ***" % self.N)
            self.print_model(phi_solver.model())
            #print(phi_solver.model().sexpr())
            ret_val = RELAX_TRACE_AND_BAD
        else:
            print("***  unable to find relaxed trace for depth=%d" % self.N)
            ret_val = NO_RELAX_TRACE
        print("*" * 60)
        return ret_val

    def run(self):
        return self.run_phi_delta()



    def print_func(selfs, values, func, func_name_no_version, model, prefix = ""):
        print(prefix + func_name_no_version + ":")
        all_val_combination = [values[func.domain(i)] for i in range(func.arity())]
        for element in itertools.product(*all_val_combination):
            print("%s\t%s: %s" % (prefix, element, model.eval(func(*element))))

    def print_model(self, model):
        #print n

        sorts = model.sorts()
        values = dict()
        print("++++++++++++++++++++++++")
        print("+++ model variables: +++")
        print("++++++++++++++++++++++++")

        for sort in sorts:
            values[sort] = model.get_universe(sort)
            print("type %s : %s" % (str(sort), str(values[sort])))

        keys_to_string_map = dict()
        for d in model:
            keys_to_string_map[d.name()] = d

        print("++++++++++++++++++++++++")
        print("+++++++ globals: +++++++")
        print("++++++++++++++++++++++++")

        for g in self.globals:
            val = keys_to_string_map.get(str(g), None)
            if not val is None:
                if is_const(g):
                    print("\t%s: %s" % (str(g), str(model[val])))
                else:
                    self.print_func(values, g, str(g), model, "\t")

        print("++++++++++++++++++++++++")
        print("++++++++ locals: ++++++++")
        print("++++++++++++++++++++++++")
        #starting with 0 (init) and then go over the odd indices
        indices = [0]+ range(1, 2*self.N, 2)
        for i in indices:
            if i == 0:
                print("----------------------")
                print("--  initial state:---")
                print("----------------------")
            else:
                print("----------------------")
                print("-- sigma %d --" % ((i+1)/2))
                print("----------------------")
            local_vars = dict()
            local_rels = dict()
            for g in self.var_dict:
                iteration_version = self.get_rebased_name(g, i)
                val = keys_to_string_map.get(str(iteration_version), None)
                if not val is None:
                    if is_const(iteration_version):
                        local_vars[str(g)] = model[val]
                    else:
                        local_rels[str(g)] = iteration_version
            for var in sorted(local_vars):
                print("\t%s:\t\t\t\t%s" % (var, str(local_vars[var])))

            for var in sorted(local_rels):
                self.print_func(values, local_rels[var], var, model, "\t")


if __name__ == '__main__':
    A = IntSort()
    B = BoolSort()
    n = Function('n*', A, A, B)
    active = Function("active", A, B)

    def nPlus(x, y):
        return And(x != y, n(x, y))


    N = 3
    x, y, l, null, x0, z1, z2, z3 = Consts('x y l null x0 z1, z2, z3', A)
    init    = And(Not(x == null), Exists(z1, n(x,z)))
    bad     = And(x == y, x == l)
    background = ForAll([z1,z2, z3], Implies(And(n(z1, z2), n(z2, z3), n(z1, z3))))

    phi_solver = Solver()
    phi_solver.add(init)
    phi_solver.add(background)
    stat = phi_solver.check()
    if stat == sat:
        print(stat.model())