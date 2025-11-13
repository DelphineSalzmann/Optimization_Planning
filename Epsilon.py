import matplotlib.pyplot as plt
from LP_Min_duree import LP_durée
from LP_retard import LP_retard
from LP_profit import LP_gain
from LP_min_projet import LP_nb_projet
from LP_multi import LP_multi
from extraction import load_instance
from pyomo.environ import value
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def epsilon_constraint_projet(nom_instance):
    i=0
    pareto_points = []
    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    model,result=LP_multi(nom_instance, Pmax*Hmax, Pmax,1000)
    epsilon=max(sum(value(model.k[s,p]) for p in model.P) for s in model.S)
    profit=value(model.obj)
    pareto_points.append((profit, epsilon))

    while epsilon>0 and i<15:
        i+=1
        print(i)
        print(epsilon)
        epsilon=epsilon-1
        model,result=LP_multi(nom_instance, Hmax, epsilon,1000)
        profit=value(model.obj)
        epsilon=max(sum(value(model.k[s,p]) for p in model.P) for s in model.S)
        pareto_points.append((profit, epsilon))

    return pareto_points

def epsilon_constraint_duree(nom_instance):
    i=0
    pareto_points = []
    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    model,result=LP_multi(nom_instance, Pmax*Hmax, Pmax, Pmax)
    epsilon=sum(value(model.fin[p]) - value(model.debut[p]) +1 for p in model.P)
    profit=value(model.obj)
    pareto_points.append((profit, epsilon))

    while epsilon>=1 and i<30:
        i+=1
        print(i)
        print(epsilon)
        epsilon=epsilon-1
        model,result=LP_multi(nom_instance, epsilon, Pmax,Pmax)
        profit=value(model.obj)
        epsilon=sum(value(model.fin[p]) - value(model.debut[p])+1 for p in model.P)
        pareto_points.append((profit, epsilon))
        print("avant filtre",pareto_points)

    return pareto_points


def epsilon_constraint_retard(nom_instance):
    i=0
    pareto_points = []
    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    model,result=LP_multi(nom_instance, Pmax*Hmax, Pmax,sum(r_values)*Hmax)
    epsilon=sum(value(model.p_retard[p]) for p in model.P)
    profit=value(model.obj)
    pareto_points.append((profit, epsilon))

    while epsilon>=1 and i<27:
        i+=1
        print(i)
        print(epsilon)
        epsilon=epsilon-1
        model,result=LP_multi(nom_instance, Hmax*Pmax, Pmax,epsilon)
        profit=value(model.obj)
        epsilon=sum(value(model.p_retard[p]) for p in model.P)
        pareto_points.append((profit, epsilon))
        print("avant filtre",pareto_points)

    return pareto_points

def multi_3(nom_instance):
    i=0
    pareto_points = []
    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    model,result=LP_multi(nom_instance, Pmax*Hmax, Pmax,1000)
    epsilon1=max(sum(value(model.k[s,p]) for p in model.P) for s in model.S)
    epsilon2=sum(value(model.p_retard[p]) for p in model.P)
    profit=value(model.obj)
    pareto_points.append((profit, epsilon1, epsilon2))

    while epsilon1>0 and i<15:
        j=0
        i+=1
        print(i)
        print(epsilon1)
        epsilon1=epsilon1-1
        model,result=LP_multi(nom_instance, Pmax*Hmax, epsilon1,1000)
        profit=value(model.obj)
        epsilon1=max(sum(value(model.k[s,p]) for p in model.P) for s in model.S)
        epsilon2=sum(value(model.p_retard[p]) for p in model.P)

        while epsilon1>0 and j<15:
            j+=1
            epsilon2=epsilon2-1
            model,result=LP_multi(nom_instance, Pmax*Hmax, epsilon1,epsilon2)
            profit=value(model.obj)
            epsilon2=sum(value(model.p_retard[p]) for p in model.P)
            pareto_points.append((profit, epsilon1, epsilon2))

    return pareto_points

def filtre_pareto(points):
    pareto_front = []

    for i, (profit_i, autre_i) in enumerate(points):
        dominated = False
        for j, (profit_j, autre_j) in enumerate(points):
            if j == i:
                continue
            # Le point j domine le point i ?
            if (profit_j >= profit_i and autre_j <= autre_i
                and (profit_j > profit_i or autre_j < autre_i)):
                dominated = True
                break
        if not dominated:
            pareto_front.append((profit_i, autre_i))

    return pareto_front

def filtre_pareto_3crit(points):
    pareto_front = []

    for i, (c1_i, c2_i, c3_i) in enumerate(points):
        dominated = False
        for j, (c1_j, c2_j, c3_j) in enumerate(points):
            if j == i:
                continue
            # j domine i si :
            #   - c1_j >= c1_i  (maximiser)
            #   - c2_j <= c2_i  (minimiser)
            #   - c3_j <= c3_i  (minimiser)
            # et strictement meilleur sur au moins un critère
            if (c1_j >= c1_i and c2_j <= c2_i and c3_j <= c3_i
                and (c1_j > c1_i or c2_j < c2_i or c3_j < c3_i)):
                dominated = True
                break
        if not dominated:
            pareto_front.append((c1_i, c2_i, c3_i))

    return pareto_front


def plot_pareto(pareto_points):
    profits, durations = zip(*pareto_points)
    print(pareto_points)
   
    plt.figure(figsize=(10, 6))
    plt.scatter(profits, durations, color='blue', s=50)  # s=taille des points
    plt.title('Front de Pareto: Nb max de projets par personne vs Profit')
    plt.xlabel('Profit')
    plt.ylabel('Nombre max de projets par personne')
    plt.grid(True)
    plt.show()

def plot_pareto_3crit(pareto_points):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Points non dominés
    c1_nd, c2_nd, c3_nd = zip(*pareto_points)
    ax.scatter(c1_nd, c2_nd, c3_nd, c='red', label='Front de Pareto', s=80)

    ax.set_xlabel('profit')
    ax.set_ylabel('Nb max de projets par personne')
    ax.set_zlabel('Nb de projets en retard')
    ax.legend()
    plt.show()


#plot_pareto(filtre_pareto(epsilon_constraint_projet('medium')))
plot_pareto_3crit(filtre_pareto_3crit(multi_3('medium')))
    
