import numpy as np
from solve_model import solve_multiobjective_epsilon_constraint_v1, solve_multiobjective_epsilon_constraint_v2, filter_dominated_solutions, solve_with_specific_epsilons, get_obj_value
from pareto import plot_pareto_front
from visualise import afficher_solution
import warnings
from pyomo.environ import value

# Ignorer les avertissements spécifiques de Pyomo s'ils apparaissent
warnings.filterwarnings("ignore", category=DeprecationWarning)

## -- Entrées utilisateur --

if __name__ == "__main__":

    # Choix instance 
    NOM_INSTANCE = "medium" # "toy", "medium", "large"

    # Choix problème multiobjectif
    PRIMAIRE= 'profit'                     # Fonction objectif: 'nb_projets_max', 'retard', 'duree', 'profit'

    #SECONDAIRES = []                     # Cas 1: seul l'objectif primaire est pris en compte
    #SECONDAIRES = ['nb_projets_max']              # Cas 2: 2 objectifs (Pareto 2D) 'nb_projets_max', 'retard', 'duree', 'profit'
    SECONDAIRES = ['nb_projets_max','retard']    # Cas 3: 3 objectifs (Pareto 3D)
    #SECONDAIRES = ['nb_projets_max', 'duree', 'retard'] # Cas 4: 4 obkectifs (Pareto 4D)

    # Pour visualiser le résultat avec la valeur d'epsilon spécifiée
    VALEURS_EPSILON_MANUELLES = {
        'nb_projets_max': 2,  # 'nb_projets_max' soit <= 10"
        #'retard': 0,      # 'retard' soit <= 50"
        #'duree':6,
        #'profit':50
    }

    # Temps de résolution max On garde cette limite grande pour ne pas avoir à s'en servir. Elle est là au cas où.
    TIME_LIMIT_SEC = 180

    # Nombre de points du front de Pareto (pour solve_multiobjective_epsilon_constraint_v1)
    NB_POINTS_PARETO = 10
    
    # ==============================================
    


    print(f"Lancement de l'optimisation multi-objectif pour l'instance : {NOM_INSTANCE}")
    print(f"Objectif principal : profit (maximisé)")
    print(f"Objectifs secondaires : {SECONDAIRES}")
    print(f"Nb points Epsilon / dim : {NB_POINTS_PARETO}")
    print(f"Limite de temps / run : {TIME_LIMIT_SEC}s")
    # Lancer la résolution
    # Etape 1: Obtenir tous les résultats bruts
    all_results = solve_multiobjective_epsilon_constraint_v2(
        nom_instance=NOM_INSTANCE,
        primary_objective=PRIMAIRE,
        secondary_objectives=SECONDAIRES,
        #nb_epsilon_steps=NB_POINTS_PARETO,
        tee=False, # Mettre à True pour voir le log détaillé de Gurobi
        time_limit_sec=TIME_LIMIT_SEC
    )

    # Etape 2: Filtrer les résultats pour ne garder que le front de Pareto
    print(f"\n--- Filtrage des solutions dominées ---")
    print(f"Points trouvés (bruts) : {len(all_results)}")
    
    pareto_results = filter_dominated_solutions(points=all_results, primary_objective=PRIMAIRE, secondary_objectives=SECONDAIRES)
    print(f"Points sur le front de Pareto (non-dominés) : {len(pareto_results)}")

    
    # Afficher le résumé (maintenant basé sur les points filtrés)

    print("\n--- Résumé des points de Pareto (non-dominés) ---")


    # Lancer la visualisation (utilise maintenant 'pareto_results' filtrés)

    if pareto_results:

        # Afficher un résumé textuel des points finaux

        for i, r in enumerate(pareto_results):

            print(f"  Point {i+1}: {r}")

        plot_pareto_front(pareto_points=pareto_results, primary_objective=PRIMAIRE, secondary_objectives=SECONDAIRES)

    else:

        print("Aucun résultat à visualiser.")



    print(f"Lancement d'une analyse de scénario unique pour l'instance : {NOM_INSTANCE}")
    print(f"Objectif principal : profit (maximisé)")
    print(f"Contraintes Epsilon manuelles : {VALEURS_EPSILON_MANUELLES}")

    ## Lancer la résolution unique

    # 'tee=True' est utile ici pour voir le détail de cette unique résolution
    model, result = solve_with_specific_epsilons(
        nom_instance=NOM_INSTANCE,
        primary_objective=PRIMAIRE,
        secondary_objectives=SECONDAIRES,
        epsilon_values=VALEURS_EPSILON_MANUELLES,
        tee=True 
    )
    print("--- Valeurs des variables model.z[p, h] ---")

    ## Itérer et afficher

    # Itère sur tous les jeux d'indices (p, h) de la variable z
    for p in model.P:
        for h in model.H:
            # Utiliser value() pour récupérer la valeur numérique de la variable
            z_valeur = value(model.z[p, h])
            
            # Afficher uniquement les valeurs non nulles pour la clarté
            if abs(z_valeur) > 1e-6: # Utiliser une petite tolérance pour les valeurs proches de zéro
                print(f"z[{p}, {h}] = {z_valeur:.4f}")
    # Etape 2: Afficher le planning si la solution est trouvée
    if model is not None and result is not None:
        print("\n--- Affichage du planning pour la solution trouvée ---")
        
        # Appeler la fonction de visualisation de planning
        afficher_solution(model, result)
        
        # Afficher les valeurs d'objectif finales
        print("\n--- Valeurs d'objectif pour cette solution ---")
        all_objs = ["profit"] + SECONDAIRES
        for obj in all_objs:
            val = get_obj_value(model, obj)
            print(f" -> {obj}: {val:.2f}")

    else:
        print("\nAucune solution trouvée pour ces contraintes. Aucun planning à afficher.")