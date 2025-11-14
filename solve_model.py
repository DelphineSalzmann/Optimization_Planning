from pyomo.environ import *
import numpy as np
import itertools
from build_model import build_model, get_objective_expression, OBJECTIVE_SENSE
from pyomo.opt import SolverStatus, TerminationCondition

# Récupérer l'expression de l'objectif 
def get_obj_value(model, obj_name_str):
    try:
        expr = get_objective_expression(model, obj_name_str)
        return value(expr)
    except Exception as e:
        # cas où la solution est infaisable ou non trouvée
        # print(f"Avertissement : Impossible d'évaluer {obj_name_str}. Erreur : {e}")
        return float('nan')

#Définir l'objectif principal du modèle
def set_objective(model, obj_name_str):
    if hasattr(model, 'obj'):
        model.del_component(model.obj)
        
    sense = OBJECTIVE_SENSE[obj_name_str]
    expr = get_objective_expression(model, obj_name_str)
    model.obj = Objective(expr=expr, sense=sense)

# Calcule les bornes min et max pour tous les objectifs
def _calculate_bounds(nom_instance, all_objectives, solver, tee=False):

    print("--- Calcul des bornes ---")
    bounds = {}
    payoff_table = {}

    for obj_name in all_objectives:
        print(f"Optimisation pour : {obj_name}")
        model = build_model(nom_instance)
        set_objective(model, obj_name)
        
        
        # Si on minimise (duree, retard, etc.), on veut éviter la solution triviale (0) en forçant le modèle à faire au moins 1 projet.
        # On ne le fait pas pour 'profit' car son sens est 'maximize'.
        if OBJECTIVE_SENSE[obj_name] == minimize:
            print("  (Ajout contrainte : au moins 1 projet)")
            model.at_least_one_project = Constraint(expr=sum(model.f[p] for p in model.P) >= 1)

        solver.solve(model, tee=tee)
        
        # Stocker les résultats pour cet 'anchor point'
        payoff_table[obj_name] = {}
        for other_obj in all_objectives:
            payoff_table[obj_name][other_obj] = get_obj_value(model, other_obj)
        
        # Stocker la meilleure valeur (diagonale de la table)
        bounds[obj_name] = {'best': payoff_table[obj_name][obj_name]}
        
    # Utiliser la table pour trouver les pires valeurs (nadir)
    for obj_name in all_objectives:
        # La pire valeur est le max (si min) ou min (si max) de la colonne
        col_values = [payoff_table[anchor_obj][obj_name] for anchor_obj in all_objectives]
        if OBJECTIVE_SENSE[obj_name] == minimize:
            bounds[obj_name]['worst'] = max(col_values)
        else:
            bounds[obj_name]['worst'] = min(col_values)
            if bounds[obj_name]['worst'] < 0:
                bounds[obj_name]['worst'] = 0
            
    print("Bornes calculées (Best / Worst):")
    for obj, b in bounds.items():
        print(f"  {obj}: {b['best']:.2f} (best) ... {b['worst']:.2f} (worst)")
    print("------------------------------------------")
    return bounds

# --Version 1 : exploration du front avec linspace et un intervalle choisi --> pratique pour obtenir la forme du front de Pareto sans être forcément exhaustif, 
# notamment pour réduire le temps lors de la minimisation de la durée
def solve_multiobjective_epsilon_constraint_v1(nom_instance, primary_objective, secondary_objectives=[], nb_epsilon_steps=5, tee=False, time_limit_sec=60):
    
    solver = SolverFactory('gurobi')
    if time_limit_sec > 0:
        solver.options['TimeLimit'] = time_limit_sec
        print(f"[INFO] Limite de temps Gurobi réglée à {time_limit_sec} secondes.")

    all_objectives = [primary_objective] + secondary_objectives
    
    # --- Cas 1 : Optimisation simple (aucun objectif secondaire) ---
    if not secondary_objectives:
        print("\n--- Optimisation mono-objectif ---")
        print(f"Objectif principal : {primary_objective}")
        model = build_model(nom_instance)
        set_objective(model, primary_objective)
        result = solver.solve(model, tee=tee)
        
        if result.solver.termination_condition == TerminationCondition.optimal:
            point = {'status': 'Optimal'}
            for obj in all_objectives:
                point[obj] = get_obj_value(model, obj)
            print(f"Solution trouvée : {point}")
            return [point]
        else:
            print(f"Échec de la résolution : {result.solver.termination_condition}")
            return []

    # --- Cas 2 : Optimisation Multi-objectif ---
    
    # 1. Calculer les bornes 
    bounds = _calculate_bounds(nom_instance, all_objectives, solver, tee=False) # 'tee' forcé à False ici pour la clarté

    # 2. Générer les grilles d'epsilon
    epsilon_ranges = {}
    for sec_obj in secondary_objectives:
        b = bounds[sec_obj]
        epsilon_ranges[sec_obj] = np.linspace(b['best'], b['worst'], nb_epsilon_steps)
        print(f"Grille Epsilon pour '{sec_obj}' (de {b['best']:.2f} à {b['worst']:.2f})")

    # Utiliser itertools.product pour créer la grille N-dimensionnelle
    epsilon_grids = [epsilon_ranges[sec_obj] for sec_obj in secondary_objectives]
    pareto_points = []

    total_runs = len(list(itertools.product(*epsilon_grids)))
    print(f"\n--- Lancement de {total_runs} optimisations Epsilon-Constraint ---")

    # 3. Itérer sur la grille d'epsilon
    for i, epsilon_tuple in enumerate(itertools.product(*epsilon_grids)):
        
        epsilon_values = dict(zip(secondary_objectives, epsilon_tuple))
        print(f"\n[Run {i+1}/{total_runs}] Résolution pour Epsilon = {epsilon_values}")

        model = build_model(nom_instance)
        
        # Définir l'objectif principal
        set_objective(model, primary_objective)
        
        # Ajouter les contraintes Epsilon
        model.epsilon_constraints = ConstraintList()
        for sec_obj, eps_val in epsilon_values.items():
            expr = get_objective_expression(model, sec_obj)
            
            # La contrainte est <= si on minimise, >= si on maximise
            if OBJECTIVE_SENSE[sec_obj] == minimize:
                model.epsilon_constraints.add(expr <= eps_val)
            else:
                model.epsilon_constraints.add(expr >= eps_val)

        # Résoudre le modèle contraint
        result = solver.solve(model, tee=tee)
        
        status_str = str(result.solver.termination_condition)
        
        # 4. Stocker les résultats
        if status_str in ['optimal', 'maxTimeLimit', 'feasible']:
            if status_str == 'maxTimeLimit':
                print("--- ATTENTION : LIMITE DE TEMPS ATTEINTE ---")
            
            point = {'status': status_str}
            for obj in all_objectives:
                point[obj] = get_obj_value(model, obj)
            
            print(f"-> Résultat : {point}")
            pareto_points.append(point)
            
        elif status_str == 'infeasible':
            print("--- MODÈLE INFESABLE (Epsilon trop strict) ---")
            # Nous n'ajoutons pas ce point au front
        else:
            print(f"--- ÉCHEC DE LA RÉSOLUTION (Status: {status_str}) ---")

    # Nettoyer l'option du solveur
    if time_limit_sec > 0:
        solver.options.pop('TimeLimit', None)

    return pareto_points

# --Version 2 : exploration du front par epsilon constraint
def solve_multiobjective_epsilon_constraint_v2(nom_instance, primary_objective, secondary_objectives=[], tee=False, time_limit_sec=60):
    
    solver = SolverFactory('gurobi')
    if time_limit_sec > 0:
        solver.options['TimeLimit'] = time_limit_sec
        print(f"[INFO] Limite de temps Gurobi réglée à {time_limit_sec} secondes.")

    all_objectives = [primary_objective] + secondary_objectives
    
    # --- Cas 1 : Optimisation simple (aucun objectif secondaire) ---
    if not secondary_objectives:
        print("\n--- Optimisation mono-objectif ---")
        print(f"Objectif principal : {primary_objective}")
        model = build_model(nom_instance)
        set_objective(model, primary_objective)
        result = solver.solve(model, tee=tee)
        
        if result.solver.termination_condition == TerminationCondition.optimal:
            point = {'status': 'Optimal'}
            for obj in all_objectives:
                point[obj] = get_obj_value(model, obj)
            print(f"Solution trouvée : {point}")
            return [point]
        else:
            print(f"Échec de la résolution : {result.solver.termination_condition}")
            return []

    # --- Cas 2 : Optimisation Multi-objectif ---
    
    # 1. Calculer les bornes
    bounds = _calculate_bounds(nom_instance, all_objectives, solver, tee=False)

    pareto_points = []
    
    # --- Définition des fonctions internes ---

    def _solve_single_epsilon_run(epsilon_values):

        model = build_model(nom_instance)
        set_objective(model, primary_objective)
        
        model.epsilon_constraints = ConstraintList()
        for sec_obj, eps_val in epsilon_values.items():
            expr = get_objective_expression(model, sec_obj)
            
            if OBJECTIVE_SENSE[sec_obj] == minimize:
                model.epsilon_constraints.add(expr <= eps_val)
            else:
                model.epsilon_constraints.add(expr >= eps_val)

        # Résoudre le modèle contraint
        result = solver.solve(model, tee=tee)
        status_str = str(result.solver.termination_condition)
        
        # Stocker les résultats
        if status_str in ['optimal', 'maxTimeLimit', 'feasible']:
            if status_str == 'maxTimeLimit':
                print("--- ATTENTION : LIMITE DE TEMPS ATTEINTE ---")
            
            point = {'status': status_str}
            for obj in all_objectives:
                point[obj] = get_obj_value(model, obj)
            
            print(f"-> Résultat : {point}")
            return point
            
        elif status_str == 'infeasible':
            print("--- MODÈLE INFÉISABLE (Epsilon trop strict) ---")
            return None
        else:
            print(f"--- ÉCHEC DE LA RÉSOLUTION (Status: {status_str}) ---")
            return None

    def _recursive_adaptive_search(
        remaining_objectives,  # La liste des objectifs à traiter
        current_constraints    # Le dict des contraintes fixées par les boucles externes
    ):
        
        # 1. Identifier l'objectif de cette boucle
        obj_to_iterate = remaining_objectives[0]
        is_innermost_loop = (len(remaining_objectives) == 1)
        
        # 2. Définir les bornes de la boucle
        current_eps = bounds[obj_to_iterate]['worst']
        end_bound = bounds[obj_to_iterate]['best']
        sense = OBJECTIVE_SENSE[obj_to_iterate]
        
        all_points_found_in_this_loop = []
        
        # 3. C'est la boucle "while" pour cet objectif
        while True:
            
            # 4. Préparer les contraintes pour ce run
            constraints_for_this_run = current_constraints.copy()
            constraints_for_this_run[obj_to_iterate] = current_eps
            
            points_from_this_step = []
            
            # 5. Décider : Récursion ou Solve ?
            if is_innermost_loop:
                # --- CAS DE BASE ---
                # Nous sommes dans la boucle la plus interne. On résout.
                print(f"\n[Run] Résolution pour Epsilon = {constraints_for_this_run}")
                point = _solve_single_epsilon_run(constraints_for_this_run)
                if point:
                    points_from_this_step.append(point)
            
            else:
                # --- ÉTAPE RÉCURSIVE ---
                # Appeler la fonction pour le prochain objectif
                points_from_inner_loop = _recursive_adaptive_search(
                    remaining_objectives[1:], # Le reste de la liste
                    constraints_for_this_run   # Les contraintes actuelles + la nôtre
                )
                if points_from_inner_loop:
                    points_from_this_step.extend(points_from_inner_loop)
            
            # 6. Logique de mise à jour de la boucle "while"
            
            if not points_from_this_step:
                # Cette valeur d'epsilon (current_eps) est trop stricte.
                # Les appels internes (ou le solve) n'ont rien donné.
                # On arrête cette boucle "while".
                break
            
            # Ajouter les points trouvés à notre liste
            all_points_found_in_this_loop.extend(points_from_this_step)
            
            # 7. Calculer le prochain epsilon basé sur les résultats
            # On prend la valeur obtenue (la plus contraignante)
            
            resulting_values = [p[obj_to_iterate] for p in points_from_this_step]
            
            if sense == minimize:
                # valeur obtenue = la plus petite valeur de l'objectif
                trigger_value = min(resulting_values)
                # "strictement inférieure... moins 0.5"
                next_eps = trigger_value - 0.5
                # Vérifier si on doit arrêter
                if next_eps < end_bound or next_eps >= current_eps:
                    break
            else: # maximize
                # valeur obtenue = la plus grande valeur de l'objectif
                trigger_value = max(resulting_values)
                # On adapte "moins 0.5" en "plus 0.5" pour resserrer la contrainte
                next_eps = trigger_value + 0.5
                # Vérifier si on doit arrêter
                if next_eps > end_bound or next_eps <= current_eps:
                    break
            
            # Mettre à jour l'epsilon pour la prochaine itération de la boucle "while"
            current_eps = next_eps
            
        # Renvoyer tous les points trouvés par cette boucle et ses sous-boucles
        return all_points_found_in_this_loop

    # --- Lancement de la recherche récursive ---
    print(f"\n--- Lancement de la recherche adaptative Epsilon-Constraint ---")
    
    pareto_points = _recursive_adaptive_search(
        secondary_objectives, # La liste complète pour démarrer
        {}                    # Commencer avec un dict de contraintes vide
    )

    # Nettoyer l'option du solveur
    if time_limit_sec > 0:
        solver.options.pop('TimeLimit', None)

    print(f"\nRecherche terminée. {len(pareto_points)} points trouvés.")

    return pareto_points

# Filtre les points obtenus pour ne garder que les solutions non dominées
def filter_dominated_solutions(points, primary_objective, secondary_objectives):

    all_objectives = [primary_objective] + secondary_objectives
    
    # 1. Filtrer les points non valides (ex: 'infeasible')
    # Nous gardons 'maxTimeLimit' et 'feasible' car ils peuvent être valides, même si non-optimaux pour leur tranche epsilon.
    valid_statuses = ['Optimal', 'maxTimeLimit', 'feasible', 'optimal']
    valid_points = [p for p in points if p['status'] in valid_statuses and not any(np.isnan(p[obj]) for obj in all_objectives)]

    if not valid_points:
        return []

    filtered_points = []
    
    # Ne pas se comparer à soi-même
    for i, point_a in enumerate(valid_points):
        is_dominated = False
        for j, point_b in enumerate(valid_points):
            if i == j:
                continue
 

            # Est-ce que point_b domine point_a ?
            # b doit être meilleur ou égal sur tous les objectifs et strictement meilleur sur au moins un objectif.
            
            b_is_better_or_equal = True
            b_is_strictly_better = False

            for obj in all_objectives:
                #on manipule des valeurs entières
                val_a = int(round(point_a[obj]))
                val_b = int(round(point_b[obj]))

                sense = OBJECTIVE_SENSE[obj]

                if sense == maximize: # Ex: profit
                    if val_b < val_a:
                        b_is_better_or_equal = False
                        break # b n'est pas meilleur ou égal
                    if val_b > val_a:
                        b_is_strictly_better = True
                
                elif sense == minimize: # Ex: duree, retard
                    if val_b > val_a:
                        b_is_better_or_equal = False
                        break # b n'est pas meilleur ou égal
                    if val_b < val_a:
                        b_is_strictly_better = True
            
            if b_is_better_or_equal and b_is_strictly_better:
                # 'point_b' domine 'point_a'
                is_dominated = True
                break # 'point_a' est dominé, inutile de continuer
        
        if not is_dominated:
            filtered_points.append(point_a)
            
    return filtered_points

# Résolution d'un unique problème d'optimisation multicritère avec des bornes prédéfinies
def solve_with_specific_epsilons(nom_instance, primary_objective, secondary_objectives, epsilon_values,tee=False):
    print(f"\n--- Lancement d'une résolution unique avec contraintes Epsilon manuelles ---")
    print(f" Objectif Primaire: {primary_objective}")
    
    # 1. Créer un nouveau solveur 
    solver = SolverFactory('gurobi') 
    
    # 2. Construire le modèle
    model = build_model(nom_instance)
    
    # 3. Définir l'objectif principal
    set_objective(model, primary_objective)
    
    # 4. Ajouter les contraintes Epsilon basées sur le dict 'epsilon_values'
    model.epsilon_constraints = ConstraintList()
    
    if not secondary_objectives:
        print(" (Aucun objectif secondaire, résolution simple)")

    for sec_obj in secondary_objectives:
        if sec_obj not in epsilon_values:
            print(f"[ERREUR] '{sec_obj}' est listé comme secondaire mais n'a pas de valeur Epsilon fournie.")
            print(f"   Valeurs fournies : {epsilon_values}")
            return None, None
        
        eps_val = epsilon_values[sec_obj]
        expr = get_objective_expression(model, sec_obj)
        sense = OBJECTIVE_SENSE[sec_obj]
        
        # La contrainte est <= si on minimise (ex: retard), >= si on maximise
        if sense == minimize:
            # Ex: 'retard' <= 50
            model.epsilon_constraints.add(expr <= eps_val)
            print(f"   Ajout contrainte : {sec_obj} <= {eps_val}")
        else:
            # Ex: 'un_objectif_max' >= 100
            model.epsilon_constraints.add(expr >= eps_val)
            print(f"   Ajout contrainte : {sec_obj} >= {eps_val}")

    # 5. Résoudre le modèle contraint
    print("\nLancement du solveur Gurobi...")
    result = solver.solve(model, tee=tee)
    
    status_str = str(result.solver.termination_condition)
    
    # 6. Retourner le modèle résolu et le résultat
    if status_str in ['optimal', 'feasible']:
        print(f"-> Solution unique trouvée (Status: {status_str})")
        return model, result
    elif status_str == 'infeasible':
        print(f"--- ÉCHEC : MODÈLE INFÉISABLE ---")
        print("     Vérifiez vos contraintes Epsilon, elles sont probablement trop strictes.")
        return None, None
    else:
        print(f"--- ÉCHEC de la résolution (Status: {status_str}) ---")
        return None, None




