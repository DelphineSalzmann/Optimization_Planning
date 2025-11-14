from pyomo.environ import *
import gurobipy
import numpy as np
from extraction import load_instance 
from pyomo.environ import Reals

# --- Constante pour le sens des objectifs
OBJECTIVE_SENSE = {
    'profit': maximize,
    'retard': minimize,
    'nb_projets_max': minimize,
    'duree': minimize
}

def build_model(nom_instance):
    Hmax, Smax, Pmax, Qmax, n_values, v_values, g_values, c_values, d_values, r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    
    model = ConcreteModel()

    # --- Ensembles
    model.H = RangeSet(1, Hmax)
    model.S = RangeSet(1, Smax)
    model.Q = RangeSet(1, Qmax)
    model.P = RangeSet(1, Pmax)

    # --- Paramètres
    model.n = Param(model.P, model.Q, initialize=n_values)
    model.v = Param(model.S, model.H, initialize=v_values)
    model.g = Param(model.P, initialize=g_values)
    model.c = Param(model.S, model.Q, initialize=c_values)
    model.d = Param(model.P, initialize=d_values)
    model.r = Param(model.P, initialize=r_values)

    # --- Variables

    model.a = Var(model.H, model.S, model.Q, model.P, domain=Binary)
    model.f = Var(model.P, domain=Binary)
    model.fin = Var(model.P, domain=NonNegativeIntegers)
    model.R = Var(model.P, domain=NonNegativeIntegers)
    model.debut = Var(model.P, domain=NonNegativeIntegers)
    model.p_retard = Var(model.P, domain=Binary)
    model.k = Var(model.S, model.P, domain=Binary)
    model.z = Var(model.P, model.H, domain=Binary)
    #model.z = Var(model.P, model.H, domain=Reals, bounds=(0, 1))
    model.N_projets = Var(domain=NonNegativeIntegers)

    # --- Contraintes
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
    
    def z_activation_rule(model, p, h, s, q):
        return model.z[p,h] >= model.a[h,s,q,p]
    model.z_activation_strong = Constraint(model.P, model.H, model.S, model.Q, rule=z_activation_rule)

    def z_monotonic_rule(model, p, h):
        if h < Hmax:
            return model.z[p, h+1] >= model.z[p, h]
        return Constraint.Skip
    model.z_monotonic = Constraint(model.P, model.H, rule=z_monotonic_rule)

    def debut_rule(model, p):
        return model.debut[p] <= sum(h *(model.z[p,h]-model.z[p,h-1]) for h in RangeSet(2, Hmax)) 
    model.debut_def = Constraint(model.P, rule=debut_rule)

    def duree_rule(model,p):
        return model.fin[p]>=model.debut[p]
    model.duree=Constraint(model.P, rule=duree_rule, doc="def duree positive")

    def k_rule(model,s,p,q,h):
        return model.k[s,p]>=model.a[h,s,q,p] 
    model.k_def=Constraint(model.S, model.P,model.Q, model.H, rule=k_rule, doc="def de k")

    def retard_rule(model,p):
        return model.p_retard[p] >= model.R[p]/Hmax
    model.retard=Constraint(model.P, rule=retard_rule, doc="Projet p en retard")

    def max_projets_rule(model, s):
        return model.N_projets >= sum(model.k[s, p] for p in model.P)
    model.max_projets_constraints = Constraint(model.S, rule=max_projets_rule)

    # --- Stocker les dimensions pour les règles de contrainte
    model.Hmax = Hmax
    model.Smax = Smax
    model.Qmax = Qmax
    model.Pmax = Pmax
    
    return model

# --- Expession des fonctions objectif ---

def obj_profit(model):
    return sum(model.f[p]*model.g[p] - model.R[p]*model.r[p] for p in model.P)

def obj_retard(model):
    return sum(model.p_retard[p] for p in model.P)

def obj_nb_projets_max(model):
    return model.N_projets

def obj_duree(model):
    return sum(model.fin[p] - model.debut[p] for p in model.P)


# --Ajout de l'objectif dans le modèle
def get_objective_expression(model, objective_name):

    if objective_name == 'profit':
        return obj_profit(model)
    elif objective_name == 'retard':
        return obj_retard(model)
    elif objective_name == 'nb_projets_max':
        return obj_nb_projets_max(model)
    elif objective_name == 'duree':
        return obj_duree(model)
    else:
        raise ValueError(f"Objectif inconnu : {objective_name}")