from pyomo.environ import *
import gurobipy
import numpy as np
from extraction import load_instance


def LP_multi(nom_instance, Dmax, Pmax, Rmax):

    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    # Creation of a Concrete Model
    model = ConcreteModel()

    #Sets
    model.H= RangeSet(1,Hmax)
    model.S = RangeSet(1,Smax)
    model.Q = RangeSet(1,Qmax)
    model.P = RangeSet(1, Pmax) 


    #Parameters
    
    model.n = Param(model.P, model.Q, initialize=n_values, doc='nb jours par compétence')
    model.v = Param(model.S, model.H, initialize=v_values, doc='vacances')
    model.g = Param(model.P, initialize=g_values, doc='gain par projet')
    model.c = Param(model.S, model.Q, initialize=c_values, doc='compétences')
    model.d = Param(model.P, initialize=d_values, doc='deadline')
    model.r = Param(model.P, initialize=r_values,doc='pénalités retard')

    #Variables 
    def init_a(model, h, s, q, p):
        return 0  
    model.a=Var(model.H, model.S, model.Q, model.P, initialize=init_a, domain=Binary, doc="matrice d'affectation")
    def init_f(model,p):
        return 0
    model.f = Var(model.P, initialize=init_f, domain = Binary, doc='indice de fin de projet')
    model.fin=Var(model.P, initialize=init_f, domain=Integers)
    model.R=Var(model.P, initialize=init_f, domain=Integers)
    model.debut=Var(model.P, initialize=init_f, domain=Integers)
    model.p_retard=Var(model.P, initialize=init_f, domain=Binary)

    def init_k(model,s,p):
        return 0
    model.k=Var(model.S,model.P, initialize=init_k, domain=Binary)

    #Constraints

    def competences_rule(model,h,s,q,p):
        return model.a[h,s,q,p]<=model.c[s,q]
    model.competences = Constraint(model.H, model.S,model.Q,model.P, rule=competences_rule, doc='personne affectée a compétence')

    # def vacances_rule(model,h,s,q,p):
    #     return model.a[h,s,q,p]<=1-model.v[s,h]
    # model.vacances = Constraint(model.H, model.S,model.Q,model.P, rule=vacances_rule, doc='vacances')

    def allocation_rule(model,h,s):
        return sum(model.a[h,s,q,p] for q in model.Q for p in model.P )<=1-model.v[s,h]
    model.allocation = Constraint(model.H, model.S, rule=allocation_rule, doc='unicité allocation')

    def unicite_rule(model,p,q):
        return sum(model.a[h,s,q,p] for h in model.H for s in model.S )<=model.n[p,q]
    model.unicite = Constraint(model.P, model.Q, rule=unicite_rule, doc='travail max par projet et unicite sur H')

    def fini_rule(model,p,q):
        return (sum(model.a[h,s,q,p] for s in model.S for h in model.H)) >=model.f[p]*model.n[p,q]
    model.fini = Constraint(model.P, model.Q, rule=fini_rule, doc='projet fini')

    def duration_rule(model,p,h,q,s):
        return model.fin[p]>= h*model.a[h,s,q,p]
    model.duration= Constraint(model.P, model.H, model.Q, model.S, rule=duration_rule, doc="definir delai pour finir projet")

    def delay_rule(model,p):
        return model.R[p]>= model.fin[p]-model.d[p]
    model.delay= Constraint(model.P, rule=delay_rule, doc="def delai 1/2")

    def delay2_rule(model,p):
        return model.R[p]>= 0
    model.delay2= Constraint(model.P, rule=delay2_rule, doc="def delai 2/2")
                             
    def debut_rule(model,p,h,s,q):
        return model.debut[p]<=h+Hmax*(1-model.a[h,s,q,p])
    model.debutp= Constraint(model.P, model.H,model.S, model.Q, rule=debut_rule, doc="def debut projet")

    def duree_rule(model,p):
        return model.fin[p]>=model.debut[p]
    model.duree=Constraint(model.P, rule=duree_rule, doc="def duree positive")

    def k_rule(model,s,p):
        return model.k[s,p]>=1/(Hmax*Qmax) * sum(model.a[h,s,q,p] for h in model.H for q in model.Q)
    model.k_def=Constraint(model.S, model.P, rule=k_rule, doc="def de k")

    def retard_rule(model,p):
        return model.p_retard[p] >= model.R[p]/Hmax
    model.retard=Constraint(model.P, rule=retard_rule, doc="Projet p en retard")

    def dureeMax_rule(model):
        return sum(model.fin[p] - model.debut[p] for p in model.P) <= Dmax
    model.duree=Constraint(rule=dureeMax_rule, doc="duree de projet max")

    def Nb_projet_rule(model):
        return sum(model.k[s,p] for s in model.S for p in model.P)/Smax<= Pmax
    model.Nb_projet=Constraint(rule=Nb_projet_rule, doc="nombre de projets max")
    
    def retardMax_rule(model):
        return sum(model.p_retard[p] for p in model.P)<= Rmax
    model.Nb_projet=Constraint(rule=retardMax_rule, doc="retard max")

    #Objective
    model.obj=Objective(expr=sum(model.f[p]*model.g[p] - model.R[p]*model.r[p] for p in model.P), sense=maximize)

    #Solve Optimization problem
    solver=SolverFactory('gurobi')
    result=solver.solve(model, tee=True)    

    return model, result

Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance('toy')
print(LP_multi('toy', 0, 0, 0))