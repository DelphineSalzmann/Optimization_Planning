from pyomo.environ import *
from check import check_solution
import matplotlib.pyplot as plt
from pyomo.environ import value
import numpy as np
from matplotlib import gridspec
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
from pyomo.environ import value, Param
import numpy as np
import re

def afficher_solution(model, result, seuil_affichage=0.5):
    """
    Affiche la solution avec deux visualisations principales améliorées.
    (Version corrigée V3)
    """

    # --- Données ---
    H = list(model.H)
    S = list(model.S)
    Q = list(model.Q)
    P = list(model.P)

    staff_names = getattr(model, "staff_names", [f"Staffeur {s}" for s in S])
    project_names = getattr(model, "job_names", [f"Projet {p}" for p in P])
    qual_names = getattr(model, "qual_names", [f"Qualification {q}" for q in Q])

    # --- Assignations ---
    assignments_data = []
    for h in H:
        for s in S:
            for q in Q:
                for p in P:
                    if value(model.a[h, s, q, p]) >= seuil_affichage:
                        assignments_data.append({
                            'Période': h,
                            'Staffeur': staff_names[s-1],
                            'Qualification': qual_names[q-1],
                            'Projet': project_names[p-1],
                            'Projet_ID': p
                        })
    df_assignments = pd.DataFrame(assignments_data)

    # --- Vacances ---
    vacations_data = []
    for s in S:
        for h in H:
            if hasattr(model, 'v') and (s, h) in model.v:
                if value(model.v[s, h]) > 0.5:
                    vacations_data.append({
                        'Période': h,
                        'Staffeur': staff_names[s-1],
                        'Type': 'Vacances'
                    })
    df_vacations = pd.DataFrame(vacations_data)

    # --- Résumé projets (MODIFIÉ V3) ---
    
    # 1. Durées théoriques
    theoretical_durations = {}
    if hasattr(model, 'n'):
        for p in model.P:
            try:
                total_days = sum(value(model.n[p, q]) for q in model.Q if (p, q) in model.n)
                theoretical_durations[p] = total_days
            except Exception:
                theoretical_durations[p] = 0 
    else:
        for p in model.P:
            theoretical_durations[p] = 0 

    project_summary_data = []
    for p in P:
        project_name = project_names[p-1]
        is_finished = value(model.f[p]) > 0.5
        
        # 2. Jours de travail réels
        project_assignments = df_assignments[df_assignments['Projet_ID'] == p]
        actual_work_days = len(project_assignments['Période'].unique())
        
        # 3. Durée théorique
        duree_theorique = theoretical_durations.get(p, 0)
        
        # 4. Deadline et Pénalité
        deadline = value(model.d[p]) if hasattr(model, 'd') and p in model.d and value(model.d[p]) is not None else float('inf')
        deadline_str = f"{deadline:.0f}" if deadline is not None and deadline != float('inf') else "N/A"
        penalty_rate = value(model.r[p]) if hasattr(model, 'r') and p in model.r else 0
        
        # 5. Jour de complétion (MODIFIÉ V3)
        completion_day = value(model.fin[p])
        completion_day_str = f"{completion_day:.0f}" if completion_day is not None else "N/A"

        # --- Logique pour Statut, Couleur, Hauteur de Barre, et Survol ---
        bar_height = actual_work_days # Par défaut
        color = ''
        status_text = ''
        hover_details = ''
        
        if is_finished:
            jours_de_retard = value(model.R[p])
            bar_height = completion_day if completion_day is not None else actual_work_days
            
            if jours_de_retard > 0:
                # CAS 2: Terminé (en retard)
                status_text = "Terminé (en retard)"
                color = 'orange'
                penalty_amount = jours_de_retard * penalty_rate
                hover_details = (
                    f"<b>Jours de retard: {jours_de_retard}</b><br>"
                    f"Pénalité: {penalty_amount:,.2f}€ ({jours_de_retard}j * {penalty_rate}€/j)"
                )
            else:
                # CAS 3: Terminé (à l'heure)
                status_text = "Terminé"
                color = '#2ca02c' # Vert
                hover_details = "Projet terminé à temps."
        
        else:
            # CAS 1: Non fini (inchangé)
            color = '#d62728' # Rouge
            bar_height = duree_theorique # Hauteur = objectif théorique
            
            if actual_work_days > 0:
                status_text = "En cours"
                hover_details = f"Objectif: {duree_theorique}j / Travaillés: {actual_work_days}j"
            else:
                status_text = "Non commencé" 
                hover_details = f"Objectif: {duree_theorique} jours-homme."

            if bar_height == 0 and actual_work_days > 0:
                bar_height = actual_work_days
                hover_details = "Jours travaillés affichés (durée théorique = 0)."

        project_summary_data.append({
            'Projet': project_name,
            'Statut': status_text,
            'Jours_travailles': actual_work_days,
            'Bar_Height': bar_height,
            'Duree_Theorique': duree_theorique,
            'Gain': value(model.g[p]) if hasattr(model, 'g') and p in model.g else 0,
            'Color': color,
            'Deadline_Raw': deadline, # Gardé pour le tracé de la ligne
            'Deadline_Str': deadline_str, # Pour hover
            'Completion_Day_Str': completion_day_str, # Pour hover
            'Hover_Details': hover_details
        })
        
    df_projects = pd.DataFrame(project_summary_data)

    # --- Demande qualifications (inchangé) ---
    qual_demand_data = []
    if hasattr(model, 'jobs_data'):
        for job in model.jobs_data:
            for qual, days in job.get('working_days_per_qualification', {}).items():
                qual_demand_data.append({
                    'Qualification': qual,
                    'Jours_demande': days,
                    'Projet': job.get('name', 'Unknown')
                })
    else:
        for qual in qual_names:
            count = len(df_assignments[df_assignments['Qualification'] == qual])
            qual_demand_data.append({
                'Qualification': qual,
                'Jours_demande': count,
                'Projet': 'Total'
            })
    df_qual_demand = pd.DataFrame(qual_demand_data)


    # --- VISUALISATION ---
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Timeline des Projets',
            'Timeline des Staffeurs',
            'Résumé des Projets',
            'Demande en Qualifications'
        ],
        specs=[
            [{"type": "scatter", "colspan": 2}, None],
            [{"type": "scatter"}, {"type": "bar"}]
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    # Axes: (1,1) -> x1, y1 | (2,1) -> x2, y2 | (2,2) -> x3, y3

    # Couleurs cohérentes par projet
    projects = project_names
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel + px.colors.qualitative.Bold
    project_colors = dict(zip(projects, colors[:len(projects)]))

    # --- 1. TIMELINE DES PROJETS ---
    fig.update_yaxes(categoryorder='array', categoryarray=list(reversed(projects)), row=1, col=1)

    if hasattr(model, "d"):
        y_positions = list(reversed(projects)) 
        for p in model.P:
            try:
                if p in model.d and value(model.d[p]) is not None:
                    deadline_x = float(value(model.d[p]))
                    project_label = project_names[p-1]
                    y_pos = y_positions.index(project_label)
                    y0 = y_pos - 0.35
                    y1 = y_pos + 0.35
                    fig.add_shape(
                        type="line",
                        x0=deadline_x, x1=deadline_x,
                        y0=y0, y1=y1,
                        xref="x1", yref="y1",
                        # MODIFIÉ V3: Couleur de la deadline
                        line=dict(color="red", width=2),
                        layer="above"
                    )
            except Exception:
                continue

    if not df_assignments.empty:
        timeline_data = df_assignments.groupby(['Projet', 'Période']).agg({
            'Staffeur': list,
            'Qualification': list
        }).reset_index()
        for project in projects:
            project_data = timeline_data[timeline_data['Projet'] == project]
            if project_data.empty:
                continue
            sizes = [8 + 4 * len(staffs) for staffs in project_data['Staffeur']]

            hover_texts = []
            for _, row in project_data.iterrows():
                txt = "<br>".join(f"{s} ({q})" for s, q in zip(row['Staffeur'], row['Qualification']))
                hover_texts.append(f"<b>{row['Projet']}</b><br>Période: {row['Période']}<br>{txt}")

            fig.add_trace(
                go.Scatter(
                    x=project_data['Période'],
                    y=[project] * len(project_data),
                    mode='markers',
                    marker=dict(
                        size=sizes,
                        color=project_colors[project],
                        opacity=0.8,
                        line=dict(width=2, color='darkgrey')
                    ),
                    name=project,
                    text=hover_texts,
                    hovertemplate='%{text}<extra></extra>',
                    showlegend=True
                ),
                row=1, col=1
            )

    fig.update_xaxes(title_text="Périodes", row=1, col=1)
    fig.update_yaxes(title_text="Projets", row=1, col=1)

    # --- 2. TIMELINE DES STAFFEURS (inchangé) ---
    if not df_assignments.empty:
        for staff in staff_names:
            staff_assignments = df_assignments[df_assignments['Staffeur'] == staff]
            
            if staff_assignments.empty:
                continue

            periods = staff_assignments['Période']
            projects_staff = staff_assignments['Projet']
            quals = staff_assignments['Qualification']
            
            hover_texts_staff = [
                f"<b>Projet :</b> {p}<br><b>Qualification :</b> {q}"
                for p, q in zip(projects_staff, quals)
            ]
            
            point_colors = [project_colors[p] for p in projects_staff]

            fig.add_trace(
                go.Scatter(
                    x=periods,
                    y=[staff] * len(periods),
                    mode='markers',
                    name=staff,
                    marker=dict(
                        size=12,
                        color=point_colors,
                        opacity=0.8,
                        symbol='circle'
                    ),
                    text=hover_texts_staff,
                    hovertemplate='%{text}<extra></extra>',
                    showlegend=False
                ),
                row=2, col=1
            )

    if not df_vacations.empty:
        vacation_texts = [
            f"<b>{s}</b><br>Période: {h}<br>En vacances" 
            for s, h in zip(df_vacations['Staffeur'], df_vacations['Période'])
        ]
        
        fig.add_trace(
            go.Scatter(
                x=df_vacations['Période'],
                y=df_vacations['Staffeur'],
                mode='markers',
                marker=dict(
                    size=10,
                    color='red',
                    opacity=0.8,
                    symbol='x',
                    line=dict(width=2)
                ),
                name='Vacances',
                text=vacation_texts,
                hovertemplate='%{text}<extra></extra>',
                showlegend=True
            ),
            row=2, col=1
        )

    fig.update_xaxes(title_text="Périodes", row=2, col=1)
    fig.update_yaxes(title_text="Staffeurs", row=2, col=1)

    # --- 3. RÉSUMÉ DES PROJETS (MODIFIÉ V3) ---
    
    # MODIFIÉ V3: Template de survol mis à jour
    hovertemplate_str = (
        '<b>%{x}</b><br>' +
        'Statut: <b>%{customdata[0]}</b><br>' +
        '--------------------<br>' +
        'Deadline: Jour %{customdata[4]}<br>' +
        '<b>Rendu du projet: Jour %{customdata[5]}</b><br>' + # <-- Ligne ajoutée
        'Nombre de jours/hommes nécessaires: %{customdata[2]}<br>' +
        'Gain: %{customdata[3]:,.0f}€<br>' +

        '<extra></extra>'
    )

    # Ajout des barres principales
    fig.add_trace(
        go.Bar(
            x=df_projects['Projet'],
            y=df_projects['Bar_Height'], # Hauteur dynamique (delta si fini, N si non fini)
            marker_color=df_projects['Color'], 
            text=[f"{j}j<br>{g:,.0f}€" for j, g in zip(df_projects['Jours_travailles'], df_projects['Gain'])],
            textposition='auto',
            hovertemplate=hovertemplate_str,
            # MODIFIÉ V3: customdata mis à jour
            customdata=df_projects[[
                'Statut', 
                'Jours_travailles',
                'Duree_Theorique',
                'Gain', 
                'Deadline_Str',
                'Completion_Day_Str', # <-- Ligne ajoutée
                'Hover_Details'
            ]],
            name="Projets",
            showlegend=False
        ),
        row=2, col=2
    )

    # Ajout des lignes de Deadline (inchangé, utilise x3/y3)
    for i, row in df_projects.iterrows():
        deadline_val = row['Deadline_Raw'] # Utilise la valeur numérique
        if deadline_val is not None and deadline_val != float('inf'):
            fig.add_shape(
                type="line",
                x0=i-0.4, 
                x1=i+0.4, 
                y0=deadline_val,
                y1=deadline_val,
                xref="x3", # Axe X du subplot (2,2)
                yref="y3", # Axe Y du subplot (2,2)
                line=dict(color="black", width=2),
                layer="above",
            )
            
    fig.update_xaxes(title_text="Projets", row=2, col=2)
    fig.update_yaxes(title_text="Jours", row=2, col=2)


    # --- Nettoyage des légendes parasites (inchangé) ---
    for trace in fig.data:
        name = getattr(trace, "name", None)
        if name is None or str(name).strip() == "":
            trace.showlegend = False
        else:
            if isinstance(name, str) and re.match(r'(?i)^\s*trace\s*\d+\s*$', name):
                trace.showlegend = False

    # --- Mise en forme finale ---
    fig.update_layout(
        title_text=f"Solution d'Optimisation - {len(P)} Projets, {len(S)} Staffeurs, {len(Q)} Qualifications",
        height=1000,
        showlegend=True,
        template="plotly_white",
        font=dict(size=10),
        margin=dict(t=100, b=50, l=50, r=50),
        barmode='overlay' 
    )

    print("Affichage du dashboard...")
    fig.show()