import json
import os
from pyomo.environ import *

def load_instance(instance_name):
    """
    Load instance data from JSON file and set up Pyomo model
    
    Parameters:
    instance_name (str): Name of the instance ('toy', 'medium', or 'large')
    
    Returns:
    model: Pyomo ConcreteModel with all parameters and variables set
    """
    
    # Load the JSON data
    base_path = os.path.dirname(__file__)
    filepath = os.path.join(base_path, f"{instance_name}_instance.json")
    with open(filepath, "r") as f:
        data = json.load(f)
    
    # Extract data from JSON
    Hmax = data['horizon']  # Time horizon
    staff = data['staff']   # Staff information
    jobs = data['jobs']     # Job information
    qualifications = data['qualifications']  # Qualifications
    
    # Calculate dimensions
    Smax = len(staff)       # Number of staff members
    Pmax = len(jobs)        # Number of jobs
    Qmax = len(qualifications)  # Number of qualifications
    
    # Create mappings for indices
    staff_names = [s['name'] for s in staff]
    job_names = [j['name'] for j in jobs]
    qual_names = qualifications
    
    # Create qualification to index mapping
    qual_to_index = {q: i+1 for i, q in enumerate(qualifications)}

    # Parameters initialization
    n_values = {}  # Number of working days per job per qualification
    v_values = {}  # Vacations (1 if on vacation, 0 otherwise)
    g_values = {}  # Gain per project
    c_values = {}  # Skills (1 if staff has qualification, 0 otherwise)
    d_values = {}  # Due date per project
    dp_values = {} # Daily penalty per project
    
    # Fill n_values (working days per job per qualification)
    # Initialize all values to 0 first
    for p in range(1, Pmax+1):
        for q in range(1, Qmax+1):
            n_values[p, q] = 0
    
    for p, job in enumerate(jobs, 1):
        d_values[p] = job['due_date']
        g_values[p] = job['gain']
        dp_values[p] = job['daily_penalty']  # Adding daily penalty
        for qual, days in job['working_days_per_qualification'].items():
            q = qual_to_index[qual]
            n_values[p, q] = days
    
    # Fill c_values (skills matrix)
    for s, staff_member in enumerate(staff, 1):
        for q, qual in enumerate(qualifications, 1):
            if qual in staff_member['qualifications']:
                c_values[s, q] = 1
            else:
                c_values[s, q] = 0
    
    # Fill v_values (vacations)
    for s, staff_member in enumerate(staff, 1):
        for h in range(1, Hmax+1):
            if h in staff_member['vacations']:
                v_values[s, h] = 1
            else:
                v_values[s, h] = 0

    return Hmax, Smax, Pmax,Qmax,n_values,v_values,g_values,c_values,d_values,dp_values, staff_names, job_names, qual_names
