import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pandas as pd
from matplotlib.ticker import MaxNLocator

#PLot un front de Pareto 2D
def _plot_2d(df, primary, secondary):
    sense_map = {'profit': ' (max)', 'retard': ' (min)', 'nb_projets': ' (min)', 'duree': ' (min)'}
    
    plt.figure(figsize=(10, 6))
    plt.scatter(df[secondary], df[primary], c='blue', alpha=0.7)
    
    plt.title('Front de Pareto 2D')
    plt.xlabel(f'{secondary}{sense_map.get(secondary, "")}')
    plt.ylabel(f'{primary}{sense_map.get(primary, "")}')
    plt.grid(True, linestyle='--', alpha=0.5)
    ax = plt.gca()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()
    print("Affichage du graphique 2D Matplotlib...")
    plt.show()

#Plot du front de Pareto 3D
def _plot_3d(df, primary, sec1, sec2):
    
    sense_map = {'profit': ' (max)', 'retard': ' (min)', 'nb_projets': ' (min)', 'duree': ' (min)'}

    fig = go.Figure(data=[go.Scatter3d(
        x=df[sec1],
        y=df[sec2],
        z=df[primary],
        mode='markers',
        marker=dict(
            size=5,
            color='blue',
            opacity=0.8
        ),
        text=[f"Profit: {p:.0f}<br>{sec1}: {s1:.0f}<br>{sec2}: {s2:.0f}" 
              for p, s1, s2 in zip(df[primary], df[sec1], df[sec2])],
        hoverinfo='text'
    )])

    fig.update_layout(
        title='Front de Pareto 3D',
        scene=dict(
            xaxis_title=f'{sec1}{sense_map.get(sec1, "")}',
            yaxis_title=f'{sec2}{sense_map.get(sec2, "")}',
            zaxis_title=f'{primary}{sense_map.get(primary, "")}'
        ),
        margin=dict(r=20, b=10, l=10, t=40)
    )
    print("Lancement du graphique 3D interactif Plotly...")
    fig.show()

# Plot du front de Pareto 4D
def _plot_4d(df, primary, sec1, sec2, sec3):
    
    sense_map = {'profit': ' (max)', 'retard': ' (min)', 'nb_projets': ' (min)', 'duree': ' (min)'}

    fig = go.Figure(data=[go.Scatter3d(
        x=df[sec1],
        y=df[sec2],
        z=df[primary],
        mode='markers',
        marker=dict(
            size=5,
            color=df[sec3], # Le 4ème objectif est mappé sur la couleur
            colorscale='Viridis',
            showscale=True,
            colorbar_title=f'{sec3}{sense_map.get(sec3, "")}'
        ),
        text=[f"Profit: {p:.0f}<br>{sec1}: {s1:.0f}<br>{sec2}: {s2:.0f}<br>{sec3}: {s3:.0f}"
              for p, s1, s2, s3 in zip(df[primary], df[sec1], df[sec2], df[sec3])],
        hoverinfo='text'
    )])

    fig.update_layout(
        title='Front de Pareto 4D (3D + Couleur)',
        scene=dict(
            xaxis_title=f'{sec1}{sense_map.get(sec1, "")}',
            yaxis_title=f'{sec2}{sense_map.get(sec2, "")}',
            zaxis_title=f'{primary}{sense_map.get(primary, "")}'
        ),
        margin=dict(r=20, b=10, l=10, t=40)
    )
    print("Lancement du graphique 4D interactif Plotly...")
    fig.show()

# Fonction de visualisation du front de Pareto avec choix du plot adapté
def plot_pareto_front(pareto_points, primary_objective, secondary_objectives):

    if not pareto_points:
        print("Aucun point de Pareto à visualiser.")
        return

    df = pd.DataFrame(pareto_points)
    
    num_secondary = len(secondary_objectives)
    
    if num_secondary == 0:
        print("Visualisation non applicable pour un seul objectif (résultat unique).")
        print(df)
        
    elif num_secondary == 1:
        # Cas 2D : Profit vs 1 autre
        _plot_2d(df, primary_objective, secondary_objectives[0])
        
    elif num_secondary == 2:
        # Cas 3D : Profit vs 2 autres
        _plot_3d(df, primary_objective, secondary_objectives[0], secondary_objectives[1])
        
    elif num_secondary == 3:
        # Cas  : 3D + Couleur
        print("4 objectifs : Affichage 3D (Profit, Sec1, Sec2) où la couleur représente le 3ème objectif secondaire.")
        _plot_4d(df, primary_objective, secondary_objectives[0], secondary_objectives[1], secondary_objectives[2])
        
    else:
        print(f"La visualisation pour {num_secondary+1} objectifs n'est pas supportée nativement.")
        print("Voici les données brutes du front de Pareto :")
        print(df)