import pyomo.environ as pyo

def check_solution(model, tolerance=1e-6):
    """
    Vérifie que la solution (stockée dans model.a et model.f) 
    respecte toutes les contraintes du problème.
    
    Prend en entrée le modèle Pyomo *résolu*.
    Retourne True si tout est valide, False sinon.
    """
    print("---  DÉBUT DE LA VÉRIFICATION DE LA SOLUTION ---")
    all_ok = True

    # Accès aux ensembles pour itérer
    try:
        H_set = model.H
        S_set = model.S
        Q_set = model.Q
        P_set = model.P
    except AttributeError:
        print("ERREUR: Le modèle ne semble pas contenir les ensembles H, S, Q, P.")
        return False

    # ---
    # 1. Contrainte de qualification (competences_rule)
    # ---
    print("\n## 1. Vérification : Qualifications du personnel")
    temp_ok = True
    for h in H_set:
        for s in S_set:
            for q in Q_set:
                # Si la personne n'a PAS la compétence...
                if model.c[s,q] < 0.5:  # <-- CORRIGÉ (sans .value)
                    for p in P_set:
                        # ... elle ne doit jamais y être affectée
                        if model.a[h,s,q,p].value > tolerance: # (variable, .value est correct)
                            print(f"  ⛔ ERREUR [Qualification]: Staff {s} (n'a pas Qual {q}) "
                                  f"est affecté à Proj {p} au jour {h}.")
                            all_ok = temp_ok = False
    if temp_ok:
        print("  ✅ OK : Personne n'est affecté à une tâche sans la compétence requise.")

    # ---
    # 2. Contrainte d'unicité journalière et de congés (vacances_rule)
    # ---
    print("\n## 2. Vérification : Unicité journalière et congés")
    temp_ok = True
    for h in H_set:
        for s in S_set:
            # On somme tout le travail de la personne 's' le jour 'h'
            daily_work = sum(model.a[h,s,q,p].value for q in Q_set for p in P_set) # (variable, .value est correct)
            
            # Cas 1: Vérification des congés
            if model.v[s,h] > 0.5: # <-- CORRIGÉ (sans .value)
                if daily_work > tolerance:
                    print(f"  ⛔ ERREUR [Congés]: Staff {s} travaille le jour {h} "
                          f"({daily_work} affectations) mais est en congé.")
                    all_ok = temp_ok = False
            
            # Cas 2: Vérification de l'unicité (s'il n'est pas en congé)
            else:
                if daily_work > 1 + tolerance:
                    print(f"  ⛔ ERREUR [Unicité]: Staff {s} est affecté à {daily_work} tâches "
                          f"le jour {h} (max 1).")
                    all_ok = temp_ok = False
    if temp_ok:
        print("  ✅ OK : Chaque personne a au plus une tâche par jour et ne travaille pas en congé.")

    # ---
    # 3. Contrainte de couverture des qualifications (LOGIQUE MÉTIER)
    # ---
    print("\n## 3. Vérification : Logique métier de complétion")
    temp_ok = True
    
    # Vérif "non-dépassement" (votre unicite_rule)
    for p in P_set:
        for q in Q_set:
            if model.n[p,q] == 0: continue  # <-- CORRIGÉ (sans .value)
            
            total_skill_work = sum(model.a[h,s,q,p].value for h in H_set for s in S_set) # (variable, .value est correct)
            
            if total_skill_work > model.n[p,q] + tolerance: # <-- CORRIGÉ (sans .value)
                print(f"  ⛔ ERREUR [Dépassement]: Proj {p}/Qual {q}: {total_skill_work} jours affectés "
                      f"(max requis {model.n[p,q]}).") # <-- CORRIGÉ
                all_ok = temp_ok = False

    # Vérif logique de complétion
    for p in P_set:
        total_work_required_projet = sum(model.n[p,q] for q in Q_set) # <-- CORRIGÉ
        if total_work_required_projet == 0: continue

        # On regarde si le projet est marqué "fini" (maintenant sans dépendance temporelle)
        if model.f[p].value > 0.5: # (variable, .value est correct)
            # Si FINI, on vérifie CHAQUE compétence
            for q in Q_set:
                if model.n[p,q] > 0: # <-- CORRIGÉ
                    
                    total_work_for_skill = sum(model.a[h,s,q,p].value for h in H_set for s in S_set) # (variable)
                    
                    if total_work_for_skill < model.n[p,q] - tolerance: # <-- CORRIGÉ
                        print(f"  ⛔ ERREUR [Logique Métier]: Proj {p} est marqué 'fini'")
                        print(f"     mais Qual {q} n'a que {total_work_for_skill:.1f} / {model.n[p,q]} jours.") # <-- CORRIGÉ
                        all_ok = temp_ok = False
    
    if temp_ok:
        print("  ✅ OK : Les projets marqués 'finis' ont bien toutes leurs compétences couvertes.")

    # ---
    # 4. Contrainte de cohérence (fini_rule)
    # ---
    print("\n## 4. Vérification : Cohérence interne (variable 'f' vs 'a')")
    temp_ok = True
    for p in P_set:
        total_work_required = sum(model.n[p,q] for q in Q_set) # <-- CORRIGÉ
        if total_work_required == 0: continue

        # Calcul du travail total effectué pour ce projet
        total_work_done = sum(model.a[t,s,q,p].value for s in S_set for q in Q_set for t in H_set) # (variable)
        
        ratio = 0.0
        if total_work_required > 0:
            ratio = total_work_done / total_work_required
        
        if model.f[p].value > 0.5 and ratio < 1.0 - tolerance: # (variable)
            print(f"  ⛔ ERREUR [Cohérence f]: Proj {p}: f=1 mais ratio travail = {ratio:.2f}.")
            all_ok = temp_ok = False
        
        if model.f[p].value < 0.5 and ratio >= 1.0 - tolerance: # (variable)
             print(f"  ⚠️ AVERTISSEMENT [Cohérence f]: Proj {p}: f=0 mais ratio travail = {ratio:.2f}.")
 
    if temp_ok:
        print("  ✅ OK : La variable 'f' est (globalement) cohérente avec les affectations.")

    # ---
    # 5. Contrainte d'unicité de réalisation
    # ---
    print("\n## 5. Vérification : Unicité de réalisation")
    print("  ✅ OK : Garanti par la contrainte (3) de couverture maximale.")

    # ---
    # CONCLUSION
    # ---
    print("\n--- 🏁 FIN DE LA VÉRIFICATION ---")
    if all_ok:
        print("\n🎉 Félicitations ! La solution semble valide et respecte toutes les contraintes.")
    else:
        print("\n❌ ATTENTION ! La solution est INVALIDE. Des contraintes ont été violées.")
        
    return all_ok