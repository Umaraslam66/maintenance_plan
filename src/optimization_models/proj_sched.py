# This file is part of the SATT-BP tool

# src/optimization_models/proj_sched.py
import xml.etree.ElementTree as ET
import logging
import datetime
import pandas as pd
import numpy as np
from pyscipopt import Model, quicksum

class Resources:
    """
    Class to store resource data for project scheduling
    """
    def __init__(self):
        self.resources = {}  # resource_id -> resource data
    
    def add_resource(self, resource_id, name=None, capacity=1):
        """Add a resource with given capacity"""
        self.resources[resource_id] = {
            'id': resource_id,
            'name': name,
            'capacity': capacity
        }
        return self.resources[resource_id]
    
    def get_resource(self, resource_id):
        """Get a resource by ID"""
        return self.resources.get(resource_id, None)
    
    def get_capacity(self, resource_id):
        """Get capacity of a resource"""
        resource = self.get_resource(resource_id)
        if resource:
            return resource.get('capacity', 1)
        return 0
    
    @classmethod
    def from_xml(cls, xml_elem):
        """Load resources from XML element"""
        resources = cls()
        
        try:
            for res_elem in xml_elem.findall('resource'):
                resource_id = res_elem.get('id')
                name = res_elem.get('name')
                capacity = int(res_elem.get('capacity', 1))
                resources.add_resource(resource_id, name, capacity)
            
            return resources
        
        except Exception as e:
            logging.error(f"Error loading resources from XML: {e}")
            return None
    
    def __str__(self):
        return f"Resources: {len(self.resources)} resources defined"


class Projects:
    """
    Class to store project data for scheduling
    """
    def __init__(self):
        self.projects = {}  # project_id -> project data
    
    def add_project(self, project_id, description=None, earliest_start=None, latest_end=None):
        """Add a project"""
        self.projects[project_id] = {
            'id': project_id,
            'desc': description,
            'earliest_start': earliest_start,
            'latest_end': latest_end,
            'tasks': []
        }
        return self.projects[project_id]
    
    def add_task(self, project_id, task_id, description=None, duration=None, count=1, 
                 min_rest_between=0, max_rest_between=None, min_rest_after=0, max_rest_after=None,
                 earliest_start=None, latest_end=None):
        """Add a task to a project"""
        if project_id not in self.projects:
            self.add_project(project_id)
        
        task = {
            'id': task_id,
            'desc': description,
            'duration': duration,
            'count': count,
            'min_rest_between': min_rest_between,
            'max_rest_between': max_rest_between,
            'min_rest_after': min_rest_after,
            'max_rest_after': max_rest_after,
            'earliest_start': earliest_start,
            'latest_end': latest_end,
            'traffic_blocking': [],
            'required_resources': []
        }
        
        self.projects[project_id]['tasks'].append(task)
        return task
    
    def add_traffic_blocking(self, project_id, task_id, link_id, amount):
        """Add traffic blocking information to a task"""
        # Find the task
        for task in self.projects[project_id]['tasks']:
            if task['id'] == task_id:
                # Add blocking info
                blocking = {
                    'link': link_id,
                    'amount': amount
                }
                task['traffic_blocking'].append(blocking)
                return blocking
        
        return None
    
    def add_resource_requirement(self, project_id, task_id, resource_id, amount=1):
        """Add resource requirement to a task"""
        # Find the task
        for task in self.projects[project_id]['tasks']:
            if task['id'] == task_id:
                # Add resource requirement
                requirement = {
                    'resource': resource_id,
                    'amount': amount
                }
                task['required_resources'].append(requirement)
                return requirement
        
        return None
    
    def get_project(self, project_id):
        """Get a project by ID"""
        return self.projects.get(project_id, None)
    
    def get_all_project_ids(self):
        """Get all project IDs"""
        return list(self.projects.keys())
    
    def get_all_tasks(self):
        """Get all tasks from all projects"""
        all_tasks = []
        for project in self.projects.values():
            for task in project['tasks']:
                task_copy = task.copy()
                task_copy['project_id'] = project['id']
                all_tasks.append(task_copy)
        
        return all_tasks
    
    @classmethod
    def from_xml(cls, xml_elem):
        """Load projects from XML element"""
        projects = cls()
        
        try:
            for proj_elem in xml_elem.findall('project'):
                project_id = proj_elem.get('id')
                description = proj_elem.get('desc')
                earliest_start = proj_elem.get('earliestStart')
                latest_end = proj_elem.get('latestEnd')
                
                projects.add_project(project_id, description, earliest_start, latest_end)
                
                # Load tasks
                for task_elem in proj_elem.findall('task'):
                    task_id = task_elem.get('id')
                    task_desc = task_elem.get('desc')
                    duration = float(task_elem.get('durationHr')) if task_elem.get('durationHr') else None
                    count = int(task_elem.get('count', 1))
                    
                    # Rest times
                    min_rest_between = float(task_elem.get('minRestBetween', 0))
                    max_rest_between = float(task_elem.get('maxRestBetween')) if task_elem.get('maxRestBetween') else None
                    min_rest_after = float(task_elem.get('minRestAfter', 0))
                    max_rest_after = float(task_elem.get('maxRestAfter')) if task_elem.get('maxRestAfter') else None
                    
                    # Time constraints
                    task_earliest = task_elem.get('earliestStart')
                    task_latest = task_elem.get('latestEnd')
                    
                    # Add the task
                    projects.add_task(
                        project_id, task_id, task_desc, duration, count,
                        min_rest_between, max_rest_between, min_rest_after, max_rest_after,
                        task_earliest, task_latest
                    )
                    
                    # Load traffic blocking
                    for block_elem in task_elem.findall('traffic_blocking'):
                        link_id = block_elem.get('link')
                        amount = block_elem.get('amount')
                        # Handle the 'esp' special case (single track operation)
                        if amount == 'esp':
                            amount = 'esp'
                        else:
                            amount = float(amount)
                        
                        projects.add_traffic_blocking(project_id, task_id, link_id, amount)
                    
                    # Load resource requirements
                    res_elem = task_elem.find('requiredResources')
                    if res_elem is not None:
                        for req_elem in res_elem.findall('resource'):
                            resource_id = req_elem.get('id')
                            amount = int(req_elem.get('amount', 1))
                            
                            projects.add_resource_requirement(project_id, task_id, resource_id, amount)
            
            return projects
        
        except Exception as e:
            logging.error(f"Error loading projects from XML: {e}")
            return None
    
    def __str__(self):
        task_count = sum(len(p['tasks']) for p in self.projects.values())
        return f"Projects: {len(self.projects)} projects with {task_count} tasks"


class Params:
    """
    Class to store parameters for the project scheduling model
    """
    def __init__(self):
        self.blocking_cost = 1.0  # Cost of traffic blocking
        self.coordination_factor = 0.5  # Factor for traffic coordination (0-1)
        self.project_cancellation_cost = {}  # project_id -> cost
        self.resource_cost = {}  # resource_id -> cost
    
    def set_blocking_cost(self, value):
        """Set the cost of traffic blocking"""
        self.blocking_cost = value
    
    def set_coordination_factor(self, value):
        """Set the factor for traffic coordination (0-1)"""
        self.coordination_factor = max(0, min(1, value))
    
    def set_project_cancellation_cost(self, project_id, cost):
        """Set cancellation cost for a project"""
        self.project_cancellation_cost[project_id] = cost
    
    def set_resource_cost(self, resource_id, cost):
        """Set cost for a resource"""
        self.resource_cost[resource_id] = cost
    
    def get_project_cancellation_cost(self, project_id):
        """Get cancellation cost for a project"""
        if project_id in self.project_cancellation_cost:
            return self.project_cancellation_cost[project_id]
        return self.project_cancellation_cost.get('*', 100)  # Default value
    
    def get_resource_cost(self, resource_id):
        """Get cost for a resource"""
        if resource_id in self.resource_cost:
            return self.resource_cost[resource_id]
        return self.resource_cost.get('*', 1)  # Default value
    
    @classmethod
    def from_xml(cls, xml_elem):
        """Load parameters from XML element"""
        params = cls()
        
        try:
            # Parse key-value parameters
            for key_val in xml_elem.findall('keyVal'):
                key = key_val.get('key')
                value = float(key_val.text)
                
                if key == 'cp_block':
                    params.set_blocking_cost(value)
                elif key == 'cp_bs':
                    params.set_coordination_factor(value)
                elif key.startswith('cp_cancel_'):
                    project_id = key.replace('cp_cancel_', '')
                    params.set_project_cancellation_cost(project_id, value)
                elif key.startswith('cp_res_'):
                    resource_id = key.replace('cp_res_', '')
                    params.set_resource_cost(resource_id, value)
                elif key == '*':
                    # Default project cancellation cost
                    params.set_project_cancellation_cost('*', value)
            
            return params
        
        except Exception as e:
            logging.error(f"Error loading parameters from XML: {e}")
            return None
    
    def __str__(self):
        return f"Scheduling parameters: blocking_cost={self.blocking_cost}, coordination_factor={self.coordination_factor}"


class ProjectSchedulingModel:
    """
    Class to solve the project scheduling problem
    """
    def __init__(self, network, projects, resources, params, plan, traffic_capacity_usage=None):
        self.network = network
        self.projects = projects
        self.resources = resources
        self.params = params
        self.plan = plan
        self.traffic_capacity_usage = traffic_capacity_usage  # {(link_id, period): usage} from traffic model
        self.model = None
        self.variables = {}
        self.results = {}
        
        # Fixed capacity blockings (from other sources)
        self.fixed_blockings = {}  # {(link_id, period): blocked_capacity}
    
    def add_fixed_blockings(self, blockings):
        """Add fixed capacity blockings"""
        self.fixed_blockings.update(blockings)
    
    def build_model(self):
        """Build the project scheduling model"""
        self.model = Model("ProjectScheduling")
        
        # Get all time periods in the planning horizon
        periods = range(self.plan.num_periods)
        
        # Dictionary to store all variables
        self.variables = {
                    'start': {},     # (project_id, task_id, subtask_index) -> start time variable
                    'blocking': {},  # (link_id, period) -> blocking variable
                    'cancel': {},    # project_id -> cancellation variable
                    'resource': {},  # (resource_id, period) -> resource usage variable
                    'aux': {}        # Store auxiliary variables
                }
                        
        # 1. Create variables
        
        # Start time variables for each task and subtask
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Cancellation variable for the project
            self.variables['cancel'][project_id] = self.model.addVar(
                vtype="B",  # Binary variable
                name=f"cancel_{project_id}"
            )
            
            # Process each task in the project
            for task in project['tasks']:
                task_id = task['id']
                
                # For each repetition of the task
                for i in range(task['count']):
                    # Create start time variable
                    key = (project_id, task_id, i)
                    self.variables['start'][key] = self.model.addVar(
                        vtype="I",  # Integer variable (period index)
                        name=f"start_{project_id}_{task_id}_{i}",
                        lb=0,
                        ub=self.plan.num_periods - 1
                    )
        
        # Create blocking variables for each link and period
        for link_id in self.network.links:
            for period in periods:
                key = (link_id, period)
                self.variables['blocking'][key] = self.model.addVar(
                    vtype="C",  # Continuous variable
                    name=f"blocking_{link_id}_{period}",
                    lb=0.0,
                    ub=1.0  # Normalized blocking (0-1)
                )

        # Create resource usage variables for each resource and period
        for resource_id in self.resources.resources:
            for period in periods:
                key = (resource_id, period)
                self.variables['resource'][key] = self.model.addVar(
                    vtype="C",  # Continuous variable
                    name=f"resource_{resource_id}_{period}",
                    lb=0.0
                )
        
        # 2. Add constraints
        
        # Time window constraints for tasks
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Process each task in the project
            for task in project['tasks']:
                task_id = task['id']
                duration_periods = int(task['duration'] / self.plan.period_length)
                
                # Use project time constraints if task-specific ones aren't provided
                earliest_start = task.get('earliest_start') or project.get('earliest_start')
                latest_end = task.get('latest_end') or project.get('latest_end')
                
                # Convert time constraints to period indices
                earliest_period = 0
                latest_period = self.plan.num_periods - 1
                
                if earliest_start:
                    # Parse the time string and convert to period index
                    if earliest_start.startswith('v'):
                        # Week-based format (e.g., 'v2410')
                        year = int(earliest_start[1:3]) + 2000
                        week = int(earliest_start[3:5])
                        # Approximate conversion to date
                        date = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                        earliest_period = self.plan.get_period_index(date)
                    else:
                        # Date-time format
                        date = datetime.datetime.strptime(earliest_start, "%Y-%m-%d %H:%M:%S")
                        earliest_period = self.plan.get_period_index(date)
                
                if latest_end:
                    # Parse the time string and convert to period index
                    if latest_end.startswith('v'):
                        # Week-based format
                        year = int(latest_end[1:3]) + 2000
                        week = int(latest_end[3:5])
                        # Approximate conversion to date (end of week)
                        # Convert to date using the last day of the week
                        date = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                        # Add 6 days to get to Sunday (end of week)
                        date = date + datetime.timedelta(days=6)
                        latest_period = self.plan.get_period_index(date)
                    else:
                        # Date-time format
                        date = datetime.datetime.strptime(latest_end, "%Y-%m-%d %H:%M:%S")
                        latest_period = self.plan.get_period_index(date)
                
                # For each repetition of the task
                for i in range(task['count']):
                    key = (project_id, task_id, i)
                    
                    # Skip if the project is cancelled
                    cancel_var = self.variables['cancel'][project_id]
                    
                    # Add time window constraints
                    # Start within the earliest_period and latest_period - duration + 1
                    if earliest_period is not None:
                        self.model.addCons(
                            self.variables['start'][key] >= earliest_period * (1 - cancel_var),
                            name=f"earliest_{project_id}_{task_id}_{i}"
                        )
                    
                    if latest_period is not None:
                        max_start = latest_period - duration_periods + 1
                        if max_start >= 0:
                            self.model.addCons(
                                self.variables['start'][key] <= max_start + 
                                self.plan.num_periods * cancel_var,
                                name=f"latest_{project_id}_{task_id}_{i}"
                            )
        
        # Sequence constraints between repetitions of a task
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Process each task in the project
            for task in project['tasks']:
                task_id = task['id']
                duration_periods = int(task['duration'] / self.plan.period_length)
                
                # Min/max rest times between repetitions
                min_rest_periods = int(task['min_rest_between'] / self.plan.period_length)
                max_rest_periods = None
                if task['max_rest_between'] is not None:
                    max_rest_periods = int(task['max_rest_between'] / self.plan.period_length)
                
                # For each repetition except the last
                for i in range(task['count'] - 1):
                    key1 = (project_id, task_id, i)
                    key2 = (project_id, task_id, i + 1)
                    
                    # Skip if the project is cancelled
                    cancel_var = self.variables['cancel'][project_id]
                    
                    # Minimum rest time between repetitions
                    self.model.addCons(
                        self.variables['start'][key2] >= 
                        self.variables['start'][key1] + duration_periods + min_rest_periods - 
                        self.plan.num_periods * cancel_var,
                        name=f"min_rest_between_{project_id}_{task_id}_{i}"
                    )
                    
                    # Maximum rest time between repetitions (if specified)
                    if max_rest_periods is not None:
                        self.model.addCons(
                            self.variables['start'][key2] <= 
                            self.variables['start'][key1] + duration_periods + max_rest_periods + 
                            self.plan.num_periods * cancel_var,
                            name=f"max_rest_between_{project_id}_{task_id}_{i}"
                        )
        
        # Sequence constraints between consecutive tasks in a project
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Process tasks in pairs (each task with the next one)
            for i in range(len(project['tasks']) - 1):
                task1 = project['tasks'][i]
                task2 = project['tasks'][i + 1]
                
                task1_id = task1['id']
                task2_id = task2['id']
                
                # Last repetition of first task and first repetition of second task
                key1 = (project_id, task1_id, task1['count'] - 1)
                key2 = (project_id, task2_id, 0)
                
                duration_periods = int(task1['duration'] / self.plan.period_length)
                
                # Min/max rest times after task1
                min_rest_periods = int(task1['min_rest_after'] / self.plan.period_length)
                max_rest_periods = None
                if task1['max_rest_after'] is not None:
                    max_rest_periods = int(task1['max_rest_after'] / self.plan.period_length)
                
                # Skip if the project is cancelled
                cancel_var = self.variables['cancel'][project_id]
                
                # Minimum rest time after task1
                self.model.addCons(
                    self.variables['start'][key2] >= 
                    self.variables['start'][key1] + duration_periods + min_rest_periods - 
                    self.plan.num_periods * cancel_var,
                    name=f"min_rest_after_{project_id}_{task1_id}"
                )
                
                # Maximum rest time after task1 (if specified)
                if max_rest_periods is not None:
                    self.model.addCons(
                        self.variables['start'][key2] <= 
                        self.variables['start'][key1] + duration_periods + max_rest_periods + 
                        self.plan.num_periods * cancel_var,
                        name=f"max_rest_after_{project_id}_{task1_id}"
                    )
        
        # Blocking constraints - link the start variables to the blocking variables
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Process each task in the project
            for task in project['tasks']:
                task_id = task['id']
                duration_periods = int(task['duration'] / self.plan.period_length)
                
                # For each repetition
                for i in range(task['count']):
                    key = (project_id, task_id, i)
                    start_var = self.variables['start'][key]
                    
                    # Skip if the project is cancelled
                    cancel_var = self.variables['cancel'][project_id]
                    
                    # For each link blocked by this task
                    for blocking in task['traffic_blocking']:
                        link_id = blocking['link']
                        amount = blocking['amount']
                        
                        # Convert 'esp' to a blocking value (e.g., 0.5 for single track)
                        blocking_value = 0.5 if amount == 'esp' else float(amount)
                        
                        # For each period that could be affected by this task
                        for offset in range(duration_periods):
                            # For each period in the planning horizon
                            for period in periods:
                                # This constraint is active if start_var + offset == period
                                # We use a big-M formulation for this conditional constraint
                                M = 1.0  # Maximum blocking value
                                
                                # Create an auxiliary variable
                                aux_var_name = f"aux_{project_id}_{task_id}_{i}_{link_id}_{period}_{offset}"
                                aux_var = self.model.addVar(vtype="B", name=aux_var_name)
                                self.variables['aux'][aux_var_name] = aux_var

                                # Add constraint: blocking[link, period] >= blocking_value * (1 - aux_var) * (1 - cancel_var)
                                self.model.addCons(
                                    self.variables['blocking'][(link_id, period)] >= 
                                    blocking_value * (1 - aux_var) * (1 - cancel_var),
                                    name=f"blocking_{project_id}_{task_id}_{i}_{link_id}_{period}_{offset}"
                                )

                                # Add constraints for the auxiliary binary variable
                                self.model.addCons(
                                    start_var + offset <= period + self.plan.num_periods * aux_var,
                                    name=f"aux1_{project_id}_{task_id}_{i}_{link_id}_{period}_{offset}"
                                )

                                self.model.addCons(
                                    start_var + offset >= period + 1 - self.plan.num_periods * (1 - aux_var),
                                    name=f"aux2_{project_id}_{task_id}_{i}_{link_id}_{period}_{offset}"
                                )
        
        # Add fixed blockings
        for (link_id, period), blocked_amount in self.fixed_blockings.items():
            if (link_id, period) in self.variables['blocking']:
                self.model.addCons(
                    self.variables['blocking'][(link_id, period)] >= blocked_amount,
                    name=f"fixed_blocking_{link_id}_{period}"
                )
        
        # Resource constraints
        # Link task executions to resource usage
        for project in self.projects.projects.values():
            project_id = project['id']
            
            # Process each task in the project
            for task in project['tasks']:
                task_id = task['id']
                duration_periods = int(task['duration'] / self.plan.period_length)
                
                # For each repetition
                for i in range(task['count']):
                    key = (project_id, task_id, i)
                    start_var = self.variables['start'][key]
                    
                    # Skip if the project is cancelled
                    cancel_var = self.variables['cancel'][project_id]
                    
                    # For each resource required by this task
                    for requirement in task['required_resources']:
                        resource_id = requirement['resource']
                        amount = requirement['amount']
                        
                        # For each period that could be affected by this task
                        for offset in range(duration_periods):
                            # For each period in the planning horizon
                            for period in periods:
                                # This constraint is active if start_var + offset == period
                                # We use a big-M formulation for this conditional constraint
                                M = amount  # Maximum resource usage
                                
                                # Create resource auxiliary variable
                                res_aux_var_name = f"res_aux_{project_id}_{task_id}_{i}_{resource_id}_{period}_{offset}"
                                res_aux_var = self.model.addVar(vtype="B", name=res_aux_var_name)
                                self.variables['aux'][res_aux_var_name] = res_aux_var

                                # Add constraint: resource[resource, period] >= amount * (1 - res_aux_var) * (1 - cancel_var)
                                self.model.addCons(
                                    self.variables['resource'][(resource_id, period)] >= 
                                    amount * (1 - res_aux_var) * (1 - cancel_var),
                                    name=f"resource_{project_id}_{task_id}_{i}_{resource_id}_{period}_{offset}"
                                )

                                # Add constraints for the auxiliary binary variable
                                self.model.addCons(
                                    start_var + offset <= period + self.plan.num_periods * res_aux_var,
                                    name=f"res_aux1_{project_id}_{task_id}_{i}_{resource_id}_{period}_{offset}"
                                )

                                self.model.addCons(
                                    start_var + offset >= period + 1 - self.plan.num_periods * (1 - res_aux_var),
                                    name=f"res_aux2_{project_id}_{task_id}_{i}_{resource_id}_{period}_{offset}"
                                )
        
        # Resource capacity constraints
        for resource_id, resource in self.resources.resources.items():
            capacity = resource['capacity']
            
            # For each period
            for period in periods:
                key = (resource_id, period)
                
                # Resource usage cannot exceed capacity
                self.model.addCons(
                    self.variables['resource'][key] <= capacity,
                    name=f"capacity_{resource_id}_{period}"
                )
        
        # 3. Set objective function
        obj_terms = []
        
        # Project cancellation costs
        for project_id, var in self.variables['cancel'].items():
            cost = self.params.get_project_cancellation_cost(project_id)
            obj_terms.append(cost * var)
        
        # Blocking costs (considering traffic impact)
        if self.traffic_capacity_usage:
            # For each link and period, calculate the impact of blocking on traffic
            for (link_id, period), blocking_var in self.variables['blocking'].items():
                # Get traffic usage for this link and period
                traffic_usage = self.traffic_capacity_usage.get((link_id, period), 0)
                
                # Calculate impact as blocking * traffic_usage * blocking_cost
                impact = blocking_var * traffic_usage * self.params.blocking_cost
                obj_terms.append(impact)
        else:
            # If no traffic data, just use a flat blocking cost
            for blocking_var in self.variables['blocking'].values():
                obj_terms.append(self.params.blocking_cost * blocking_var)
        
        # Resource costs
        for (resource_id, _), resource_var in self.variables['resource'].items():
            cost = self.params.get_resource_cost(resource_id)
            obj_terms.append(cost * resource_var)
        
        # Set the objective
        self.model.setObjective(quicksum(obj_terms), "minimize")
    
    def solve(self, time_limit=3600, gap=0.01, verbose=1):
        """Solve the project scheduling model"""
        if self.model is None:
            logging.error("Model not built. Call build_model() first.")
            return False
        
        # Set solver parameters
        self.model.setRealParam('limits/time', time_limit)
        self.model.setRealParam('limits/gap', gap)
        self.model.setIntParam('display/verblevel', verbose)
        
        # Solve the model
        self.model.optimize()
        
        # Check solution status
        status = self.model.getStatus()
        if status == 'optimal' or status == 'feasible':
            # Extract results
            self.results = {
                'status': status,
                'objective': self.model.getObjVal(),
                'start_times': {},
                'blockings': {},
                'cancelled_projects': [],
                'resource_usage': {}
            }
            
            # Extract start times
            for key, var in self.variables['start'].items():
                start_val = self.model.getVal(var)
                if start_val is not None:
                    self.results['start_times'][key] = int(start_val)
            
            # Extract blockings
            for key, var in self.variables['blocking'].items():
                block_val = self.model.getVal(var)
                if block_val > 1e-6:  # Filter out very small values
                    self.results['blockings'][key] = block_val
            
            # Extract cancelled projects
            for project_id, var in self.variables['cancel'].items():
                cancel_val = self.model.getVal(var)
                if cancel_val > 0.5:  # Binary variable, should be 0 or 1
                    self.results['cancelled_projects'].append(project_id)
            
            # Extract resource usage
            for key, var in self.variables['resource'].items():
                usage_val = self.model.getVal(var)
                if usage_val > 1e-6:  # Filter out very small values
                    self.results['resource_usage'][key] = usage_val
            
            return True
        else:
            logging.error(f"Optimization failed with status: {status}")
            return False
    
    def get_capacity_blockings(self):
        """Get capacity blockings for all links and periods"""
        if not self.results:
            return {}
        
        return self.results['blockings']
    
    def get_affected_traffic_days(self):
        """Determine which traffic days are affected by capacity blockings"""
        if not self.results:
            return []
        
        affected_days = set()
        
        # For each blocking, determine which traffic day it falls into
        for (link_id, period), _ in self.results['blockings'].items():
            period_start = self.plan.get_period_start(period)
            period_end = self.plan.get_period_end(period)
            
            # If the period overlaps with traffic window
            if self.plan.is_in_traffic_window(period_start) or self.plan.is_in_traffic_window(period_end):
                # Extract the date (ignore time)
                date = period_start.date()
                affected_days.add(date)
        
        return sorted(list(affected_days))
    
    def get_project_schedule(self):
        """Get a schedule of all projects and tasks"""
        if not self.results:
            return {}
        
        schedule = {}
        
        # For each project
        for project_id in self.projects.get_all_project_ids():
            # Skip cancelled projects
            if project_id in self.results['cancelled_projects']:
                continue
            
            project = self.projects.get_project(project_id)
            schedule[project_id] = {
                'id': project_id,
                'desc': project['desc'],
                'tasks': []
            }
            
            # For each task in the project
            for task in project['tasks']:
                task_id = task['id']
                duration = task['duration']
                
                task_schedule = {
                    'id': task_id,
                    'desc': task['desc'],
                    'duration': duration,
                    'instances': []
                }
                
                # For each repetition of the task
                for i in range(task['count']):
                    key = (project_id, task_id, i)
                    
                    # Get the start period
                    if key in self.results['start_times']:
                        start_period = self.results['start_times'][key]
                        start_time = self.plan.get_period_start(start_period)
                        end_time = start_time + datetime.timedelta(hours=duration)
                        
                        instance = {
                            'index': i,
                            'start_time': start_time,
                            'end_time': end_time,
                            'blocking': [b for (link, period), b in self.results['blockings'].items() 
                                        if start_period <= period < start_period + int(duration / self.plan.period_length)]
                        }
                        
                        task_schedule['instances'].append(instance)
                
                schedule[project_id]['tasks'].append(task_schedule)
        
        return schedule
    
    def write_results_to_file(self, filename):
        """Write results to a file in a structured format"""
        if not self.results:
            logging.error("No results to write. Solve the model first.")
            return False
        
        try:
            with open(filename, 'w') as f:
                f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
                f.write("<project_schedule>\n")
                
                # Write summary
                f.write("  <summary>\n")
                f.write(f"    <status>{self.results['status']}</status>\n")
                f.write(f"    <objective>{self.results['objective']:.2f}</objective>\n")
                f.write(f"    <cancelled_projects>{len(self.results['cancelled_projects'])}</cancelled_projects>\n")
                f.write("  </summary>\n")
                
                # Write cancelled projects
                if self.results['cancelled_projects']:
                    f.write("  <cancelled>\n")
                    for project_id in self.results['cancelled_projects']:
                        f.write(f"    <project id=\"{project_id}\"/>\n")
                    f.write("  </cancelled>\n")
                
                # Write schedule
                schedule = self.get_project_schedule()
                f.write("  <schedule>\n")
                
                for project_id, project in schedule.items():
                    f.write(f"    <project id=\"{project_id}\" desc=\"{project['desc']}\">\n")
                    
                    for task in project['tasks']:
                        f.write(f"      <task id=\"{task['id']}\" desc=\"{task['desc']}\" duration=\"{task['duration']}\">\n")
                        
                        for instance in task['instances']:
                            start_str = instance['start_time'].strftime("%Y-%m-%d %H:%M:%S")
                            end_str = instance['end_time'].strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"        <instance index=\"{instance['index']}\" start=\"{start_str}\" end=\"{end_str}\"/>\n")
                        
                        f.write("      </task>\n")
                    
                    f.write("    </project>\n")
                
                f.write("  </schedule>\n")
                
                # Write capacity blockings
                f.write("  <capacity_blockings>\n")
                for (link_id, period), blocking in self.results['blockings'].items():
                    period_start = self.plan.get_period_start(period)
                    start_str = period_start.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"    <blocking link=\"{link_id}\" period=\"{period}\" start=\"{start_str}\" value=\"{blocking:.2f}\"/>\n")
                f.write("  </capacity_blockings>\n")
                
                # Write affected traffic days
                affected_days = self.get_affected_traffic_days()
                f.write("  <affected_days>\n")
                for day in affected_days:
                    f.write(f"    <day date=\"{day}\"/>\n")
                f.write("  </affected_days>\n")
                
                # Write resource usage
                f.write("  <resource_usage>\n")
                for (resource_id, period), usage in self.results['resource_usage'].items():
                    period_start = self.plan.get_period_start(period)
                    start_str = period_start.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"    <usage resource=\"{resource_id}\" period=\"{period}\" start=\"{start_str}\" value=\"{usage:.2f}\"/>\n")
                f.write("  </resource_usage>\n")
                
                f.write("</project_schedule>")
            
            return True
        
        except Exception as e:
            logging.error(f"Error writing results to file: {e}")
            return False