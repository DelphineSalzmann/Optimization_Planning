import matplotlib.pyplot as plt
from LP_Min_duree import LP_durée

def Pareto_duree_profit(nom_instance, Gmin_values):
    pareto_points = []

    for Gmin in Gmin_values:
        model, result = LP_durée(nom_instance, Gmin)

        # Extract duration from the objective value
        duration = model.obj.expr()
        
        # Calculate profit
        profit = sum(model.f[p].value * model.g[p] - model.R[p].value * model.r[p] for p in model.P)

        pareto_points.append((duration, profit))

    return pareto_points

def filtre_pareto(points):

    pareto_front = []

    for i, (d_i, p_i) in enumerate(points):
        dominated = False
        for j, (d_j, p_j) in enumerate(points):
            if j == i:
                continue
            # Point j domine point i ?
            if d_j <= d_i and p_j >= p_i and (d_j < d_i or p_j > p_i):
                dominated = True
                break
        if not dominated:
            pareto_front.append((d_i, p_i))

    return pareto_front


def plot_pareto(pareto_points):
    durations, profits = zip(*pareto_points)
    print(pareto_points)
   
    plt.figure(figsize=(10, 6))
    plt.scatter(profits, durations, color='blue', s=50)  # s=taille des points
    plt.title('Front de Pareto: Durée vs Profit')
    plt.xlabel('Profit')
    plt.ylabel('Durée totale des projets')
    plt.grid(True)
    plt.show()

plot_pareto(filtre_pareto(Pareto_duree_profit('large', range(0, 817, 50))))