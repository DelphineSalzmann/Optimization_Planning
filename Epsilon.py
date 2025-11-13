import matplotlib.pyplot as plt
from LP_Min_duree import LP_durée
from LP_retard import LP_retard
from LP_profit import LP_gain
from LP_min_projet import LP_nb_projet
from LP_multi import LP_multi
from extraction import load_instance
from pyomo.environ import value

def epsilon_constraint(nom_instance):
    i=0
    pareto_points = []
    Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,r_values, staff_names, job_names, qual_names = load_instance(nom_instance)
    model,result=LP_multi(nom_instance, Hmax, Pmax,sum(r_values)*Hmax)
    epsilon=sum(value(model.k[s,p]) for s in model.S for p in model.P)/Smax
    profit=value(model.obj)
    pareto_points.append((profit, epsilon))

    while epsilon>=1 and i<10:
        i+=1
        print(i)
        print(epsilon)
        epsilon=epsilon-1
        model,result=LP_multi(nom_instance, Hmax, epsilon,sum(r_values)*Hmax)
        profit=value(model.obj)
        epsilon=sum(value(model.k[s,p]) for s in model.S for p in model.P)/Smax
        pareto_points.append((profit, epsilon))

    return pareto_points


def plot_pareto(pareto_points):
    profits, durations = zip(*pareto_points)
    print(pareto_points)
   
    plt.figure(figsize=(10, 6))
    plt.scatter(profits, durations, color='blue', s=50)  # s=taille des points
    plt.title('Front de Pareto: Nb moyen de projets vs Profit')
    plt.xlabel('Profit')
    plt.ylabel('Nombre moyen de projets par personne')
    plt.grid(True)
    plt.show()

plot_pareto(epsilon_constraint('toy'))
    
