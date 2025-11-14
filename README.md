## Optimization_Planning

# Guide d'utilisation

Seul le fichier main.py a besoin d'être modifié. 

On peut choisir :

    - l'instance de données
    - le problème multicritère ou unicritère à résoudre
    - les valeurs pour lesquelles afficher une visualisation des valeurs des variables du problème
    - le temps maximal de résolution dans le cas où celle-ci prend trop de temps
    - le nombre de points souhaités du front de pareto dans le cas où la version solve_multiobjective_epsilon_constraint_v1 est utilisée. Si on utilise solve_multiobjective_epsilon_constraint_v2, ce nombre n'a pas d'influence puisque le front obtenu est exhaustif.

On obtient :
    - un graphe 2D, 3D ou 4D selon le nombre d'objectifs choisis représentant le front de pareto des solutions
    - une visualisation de la répartition des tâches et durée des projets pour la solution choisie ci-dessus


# Organisation du code

L'architecture du code est la suivante :

    - Trois instances .json de taille croissante : 'toy', 'medium' et 'large'

    - un fichier build_model.py qui construit le modèle d'optimisation sous Pyomo/Gurobi

    - un fichier solve_model.py qui résout le problème d'optimisation. Si le problème est multicritères, il le résout par méthode epsilon-constraint
    
    - un fichier check.py qui permet de valider que la solution respecte bien les contraintes imposées

    - un fichier visualise.py qui permet de visualiser la solution sous forme d'un dashboard qui présente:

        - une timeline des projets : pour chaque projet, pour chaque jour, quelles personnes travaillent et au titre de quelle qualification

        - une timeline des Staffeurs : pour chaque personne, pour chaque jour, sur quel projet et au titre de quelle qualification travaille la personne

        - un résumé des projets qui indique si le projet est terminé ou non, le temps de réalisation, la deadline et les gain et pénalité associés

    - un fichier pareto.py qui affiche le front de pareto

    - un fichier main.py avec lequel intéragir pour lancer la résolution des problèmes d'optimisation souhaités


# Bibliothèques nécessaires

    - pyomo
    - gurobi (avec license)
    - matplotlib.pyplot
    - plotly
    - numpy
    

