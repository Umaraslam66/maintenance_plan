# src/execution/tcr_opt.py
import os
import sys
import logging
import datetime
import xml.etree.ElementTree as ET
import yaml
from pathlib import Path

# Add parent directory to path to import optimization_models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from optimization_models.plan_data import Network, Plan
from optimization_models.proj_sched import Resources, Projects, Params as SchedParams, ProjectSchedulingModel
from optimization_models.traffic_flow import Demand, Routes, Params as TrafficParams, TrafficFlowModel

class ProblemParser:
    """Class to parse problem description from XML or YAML files"""
    
    @staticmethod
    def parse_problem(file_path, directory=None):
        """Parse problem from a file (XML or YAML)"""
        if directory:
            file_path = os.path.join(directory, file_path)
        
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None
        
        if file_path.endswith('.xml'):
            return ProblemParser.parse_xml_problem(file_path)
        elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
            return ProblemParser.parse_yaml_problem(file_path)
        else:
            logging.error(f"Unsupported file format: {file_path}")
            return None
    
    @staticmethod
    def parse_xml_problem(file_path):
        """Parse problem from XML file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Check if this is a problem description
            if root.tag != 'problem':
                logging.error(f"Not a valid problem description: {file_path}")
                return None
            
            problem = {
                'network': None,
                'projects': None,
                'resources': None,
                'demand': None,
                'routes': None,
                'params': {
                    'scheduling': None,
                    'traffic': None
                },
                'plan': None
            }
            
            # Parse network
            network_elem = root.find('network')
            if network_elem is not None:
                problem['network'] = Network()
                
                # Parse nodes
                nodes_elem = network_elem.find('nodes')
                if nodes_elem is not None:
                    for node_elem in nodes_elem.findall('node'):
                        node_id = node_elem.get('id')
                        name = node_elem.get('name')
                        lat = float(node_elem.get('lat')) if node_elem.get('lat') is not None else None
                        lon = float(node_elem.get('lon')) if node_elem.get('lon') is not None else None
                        merge_group = node_elem.get('merge_group')
                        
                        problem['network'].add_node(node_id, name, lat, lon, merge_group)
                
                # Parse links
                links_elem = network_elem.find('links')
                if links_elem is not None:
                    for link_elem in links_elem.findall('link'):
                        link_id = link_elem.get('id')
                        from_node = link_elem.get('from')
                        to_node = link_elem.get('to')
                        length = float(link_elem.get('length')) if link_elem.get('length') is not None else None
                        tracks = int(link_elem.get('tracks')) if link_elem.get('tracks') is not None else None
                        capacity = int(link_elem.get('capacity')) if link_elem.get('capacity') is not None else 10
                        
                        problem['network'].add_link(link_id, from_node, to_node, length, tracks, capacity)
            
            # Parse resources
            resources_elem = root.find('resources')
            if resources_elem is not None:
                problem['resources'] = Resources.from_xml(resources_elem)
            
            # Parse projects
            projects_elem = root.find('projects')
            if projects_elem is not None:
                problem['projects'] = Projects.from_xml(projects_elem)
            
            # Parse traffic data
            traffic_elem = root.find('traffic')
            if traffic_elem is not None:
                # Parse demand
                demand_elem = traffic_elem.find('demand')
                if demand_elem is not None:
                    problem['demand'] = Demand.from_xml(traffic_elem)
                
                # Parse routes
                routes_elem = traffic_elem.find('routes')
                if routes_elem is not None:
                    problem['routes'] = Routes.from_xml(traffic_elem)
            
            # Parse parameters
            params_elem = root.find('params')
            if params_elem is not None:
                # Parse scheduling parameters
                sched_params_elem = params_elem.find('scheduling')
                if sched_params_elem is not None:
                    problem['params']['scheduling'] = SchedParams.from_xml(sched_params_elem)
                else:
                    # Try to parse from the main params element
                    problem['params']['scheduling'] = SchedParams.from_xml(params_elem)
                
                # Parse traffic parameters
                traffic_params_elem = params_elem.find('traffic')
                if traffic_params_elem is not None:
                    problem['params']['traffic'] = TrafficParams.from_xml(traffic_params_elem)
                else:
                    # Try to parse from the main params element
                    problem['params']['traffic'] = TrafficParams.from_xml(params_elem)
            
            # Parse plan
            plan_elem = root.find('plan')
            if plan_elem is not None:
                problem['plan'] = Plan()
                
                # Parse planning period
                start_str = plan_elem.get('start')
                end_str = plan_elem.get('end')
                period_length = float(plan_elem.get('period_length', 8))
                
                if start_str and end_str:
                    start_time = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                    problem['plan'].set_planning_period(start_time, end_time, period_length)
                
                # Parse traffic window
                traffic_start_str = plan_elem.get('traffic_start')
                traffic_end_str = plan_elem.get('traffic_end')
                
                if traffic_start_str and traffic_end_str:
                    traffic_start = datetime.datetime.strptime(traffic_start_str, "%Y-%m-%d %H:%M:%S")
                    traffic_end = datetime.datetime.strptime(traffic_end_str, "%Y-%m-%d %H:%M:%S")
                    problem['plan'].set_traffic_window(traffic_start, traffic_end)
            
            return problem
        
        except Exception as e:
            logging.error(f"Error parsing XML problem: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def parse_yaml_problem(file_path):
        """Parse problem from YAML file"""
        try:
            with open(file_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            # Check if this is a valid problem description
            if not isinstance(yaml_data, dict):
                logging.error(f"Not a valid problem description: {file_path}")
                return None
            
            # Initialize problem structure
            problem = {
                'network': None,
                'projects': None,
                'resources': None,
                'demand': None,
                'routes': None,
                'params': {
                    'scheduling': None,
                    'traffic': None
                },
                'plan': None
            }
            
            # Get base directory for resolving relative paths
            base_dir = os.path.dirname(file_path)
            
            # Parse network
            if 'network' in yaml_data:
                network_file = yaml_data['network']
                if os.path.isabs(network_file):
                    network_path = network_file
                else:
                    network_path = os.path.join(base_dir, network_file)
                
                if os.path.exists(network_path):
                    problem['network'] = Network.from_xml(network_path)
            
            # Parse projects
            if 'projects' in yaml_data:
                projects_file = yaml_data['projects']
                if os.path.isabs(projects_file):
                    projects_path = projects_file
                else:
                    projects_path = os.path.join(base_dir, projects_file)
                
                if os.path.exists(projects_path):
                    # Parse the projects XML
                    tree = ET.parse(projects_path)
                    root = tree.getroot()
                    projects_elem = root.find('projects')
                    
                    if projects_elem is not None:
                        problem['projects'] = Projects.from_xml(projects_elem)
            
            # Parse resources
            if 'resources' in yaml_data:
                resources_file = yaml_data['resources']
                if os.path.isabs(resources_file):
                    resources_path = resources_file
                else:
                    resources_path = os.path.join(base_dir, resources_file)
                
                if os.path.exists(resources_path):
                    # Parse the resources XML
                    tree = ET.parse(resources_path)
                    root = tree.getroot()
                    resources_elem = root.find('resources')
                    
                    if resources_elem is not None:
                        problem['resources'] = Resources.from_xml(resources_elem)
            
            # Parse traffic data
            if 'traffic' in yaml_data:
                traffic_file = yaml_data['traffic']
                if os.path.isabs(traffic_file):
                    traffic_path = traffic_file
                else:
                    traffic_path = os.path.join(base_dir, traffic_file)
                
                if os.path.exists(traffic_path):
                    # Parse traffic XML for demand and routes
                    tree = ET.parse(traffic_path)
                    root = tree.getroot()
                    
                    # Parse demand
                    problem['demand'] = Demand.from_xml(traffic_path)
                    
                    # Parse routes
                    problem['routes'] = Routes.from_xml(traffic_path)
            
            # Parse parameters
            if 'params' in yaml_data:
                params_file = yaml_data['params']
                if os.path.isabs(params_file):
                    params_path = params_file
                else:
                    params_path = os.path.join(base_dir, params_file)
                
                if os.path.exists(params_path):
                    # Parse the parameters XML
                    tree = ET.parse(params_path)
                    root = tree.getroot()
                    params_elem = root.find('params')
                    
                    if params_elem is not None:
                        # Parse scheduling parameters
                        sched_params_elem = params_elem.find('scheduling')
                        if sched_params_elem is not None:
                            problem['params']['scheduling'] = SchedParams.from_xml(sched_params_elem)
                        else:
                            # Try to parse from the main params element
                            problem['params']['scheduling'] = SchedParams.from_xml(params_elem)
                        
                        # Parse traffic parameters
                        traffic_params_elem = params_elem.find('traffic')
                        if traffic_params_elem is not None:
                            problem['params']['traffic'] = TrafficParams.from_xml(traffic_params_elem)
                        else:
                            # Try to parse from the main params element
                            problem['params']['traffic'] = TrafficParams.from_xml(params_elem)
            
            # Parse plan
            if 'plan' in yaml_data:
                plan_data = yaml_data['plan']
                problem['plan'] = Plan()
                
                # Parse planning period
                if 'start' in plan_data and 'end' in plan_data:
                    start_str = plan_data['start']
                    end_str = plan_data['end']
                    period_length = float(plan_data.get('period_length', 8))
                    
                    start_time = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    end_time = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                    problem['plan'].set_planning_period(start_time, end_time, period_length)
                
                # Parse traffic window
                if 'traffic_start' in plan_data and 'traffic_end' in plan_data:
                    traffic_start_str = plan_data['traffic_start']
                    traffic_end_str = plan_data['traffic_end']
                    
                    traffic_start = datetime.datetime.strptime(traffic_start_str, "%Y-%m-%d %H:%M:%S")
                    traffic_end = datetime.datetime.strptime(traffic_end_str, "%Y-%m-%d %H:%M:%S")
                    problem['plan'].set_traffic_window(traffic_start, traffic_end)
            
            return problem
        
        except Exception as e:
            logging.error(f"Error parsing YAML problem: {e}")
            import traceback
            traceback.print_exc()
            return None


class TCROptimizer:
    """Main optimizer class for TCR (Temporary Capacity Restriction) scheduling"""
    
    def __init__(self, problem=None):
        """Initialize the optimizer with a problem"""
        self.problem = problem
        self.sched_model = None
        self.traffic_model = None
        self.results = {
            'sched': None,
            'traffic': None
        }
    
    def load_problem(self, file_path, directory=None):
        """Load problem from a file"""
        self.problem = ProblemParser.parse_problem(file_path, directory)
        return self.problem is not None
    
    def set_defaults(self):
        """Set default values for missing components"""
        if self.problem is None:
            return False
        
        # Create default network if not present
        if self.problem['network'] is None:
            self.problem['network'] = Network()
        
        # Create default resources if not present
        if self.problem['resources'] is None:
            self.problem['resources'] = Resources()
        
        # Create default projects if not present
        if self.problem['projects'] is None:
            self.problem['projects'] = Projects()
        
        # Create default demand if not present
        if self.problem['demand'] is None:
            self.problem['demand'] = Demand()
        
        # Create default routes if not present
        if self.problem['routes'] is None:
            self.problem['routes'] = Routes()
        
        # Create default parameters if not present
        if self.problem['params']['scheduling'] is None:
            self.problem['params']['scheduling'] = SchedParams()
        
        if self.problem['params']['traffic'] is None:
            self.problem['params']['traffic'] = TrafficParams()
        
        # Create default plan if not present
        if self.problem['plan'] is None:
            self.problem['plan'] = Plan()
            # Set default planning period
            start_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + datetime.timedelta(days=7)
            self.problem['plan'].set_planning_period(start_time, end_time, 8)
            self.problem['plan'].set_traffic_window(start_time, end_time)
        
        return True
    
    def initialize_models(self, traffic_capacity_usage=None):
        """Initialize the scheduling and traffic flow models"""
        if self.problem is None:
            logging.error("Problem not loaded. Call load_problem() first.")
            return False
        
        # Normalize network names
        if self.problem['network']:
            self.problem['network'].normalize_names()
        
        # Normalize project links
        if self.problem['projects']:
            for project in self.problem['projects'].projects.values():
                for task in project['tasks']:
                    for blocking in task['traffic_blocking']:
                        blocking['link'] = self.problem['network']._normalize_name(blocking['link'])
        
        # Normalize routes if exists
        if self.problem['routes']:
            normalized_routes = {}
            for line_id, route in self.problem['routes'].line_routes.items():
                normalized_line_id = self.problem['network']._normalize_name(line_id)
                normalized_routes[normalized_line_id] = route
            self.problem['routes'].line_routes = normalized_routes
        
        # Initialize scheduling model
        self.sched_model = ProjectSchedulingModel(
            network=self.problem['network'],
            projects=self.problem['projects'],
            resources=self.problem['resources'],
            params=self.problem['params']['scheduling'],
            plan=self.problem['plan'],
            traffic_capacity_usage=traffic_capacity_usage
        )
        
        # Initialize traffic flow model
        self.traffic_model = TrafficFlowModel(
            network=self.problem['network'],
            demand=self.problem['demand'],
            routes=self.problem['routes'],
            params=self.problem['params']['traffic'],
            plan=self.problem['plan']
        )
        
        return True
    
    def solve_scheduling(self, fixed_blockings=None, time_limit=3600, gap=0.01, verbose=1):
        """Solve the scheduling model"""
        if self.sched_model is None:
            logging.error("Models not initialized. Call initialize_models() first.")
            return False
        
        # Add fixed blockings if provided
        if fixed_blockings is not None:
            self.sched_model.add_fixed_blockings(fixed_blockings)
        
        # Build the model
        self.sched_model.build_model()
        
        # Solve the model
        success = self.sched_model.solve(time_limit, gap, verbose)
        
        if success:
            self.results['sched'] = self.sched_model.results
        
        return success
    
    def solve_traffic(self, capacity_constraints=None, time_limit=3600, gap=0.01, verbose=1):
        """Solve the traffic flow model"""
        if self.traffic_model is None:
            logging.error("Models not initialized. Call initialize_models() first.")
            return False
        
        # Build the model
        self.traffic_model.build_model(capacity_constraints)
        
        # Solve the model
        success = self.traffic_model.solve(time_limit, gap, verbose)
        
        if success:
            self.results['traffic'] = self.traffic_model.results
        
        return success
    
    def solve_integrated(self, max_iterations=5, time_limit=3600, gap=0.01, verbose=1):
        """Solve the integrated scheduling and traffic flow problem"""
        if self.sched_model is None or self.traffic_model is None:
            logging.error("Models not initialized. Call initialize_models() first.")
            return False
        
        # 1. First, solve the traffic flow model without capacity constraints
        # to get the undisturbed traffic flows
        logging.info("Solving undisturbed traffic flow model...")
        success = self.solve_traffic(None, time_limit, gap, verbose)
        if not success:
            logging.error("Failed to solve undisturbed traffic flow model.")
            return False
        
        # Get undisturbed link flows for scheduling model
        undisturbed_capacity_usage = self.traffic_model.get_capacity_utilization()
        
        # 2. Initialize the scheduling model with undisturbed traffic
        logging.info("Initializing scheduling model with undisturbed traffic...")
        self.sched_model.traffic_capacity_usage = undisturbed_capacity_usage
        
        # 3. Iteratively solve both models until convergence
        iteration = 0
        converged = False
        
        while not converged and iteration < max_iterations:
            iteration += 1
            logging.info(f"Iteration {iteration}...")
            
            # 3.1. Solve the scheduling model
            logging.info("Solving scheduling model...")
            success = self.solve_scheduling(None, time_limit, gap, verbose)
            if not success:
                logging.error("Failed to solve scheduling model.")
                return False
            
            # Get capacity blockings from scheduling model
            capacity_blockings = self.sched_model.get_capacity_blockings()
            
            # 3.2. Solve the traffic flow model with capacity constraints
            logging.info("Solving traffic flow model with capacity constraints...")
            success = self.solve_traffic(capacity_blockings, time_limit, gap, verbose)
            if not success:
                logging.error("Failed to solve traffic flow model with capacity constraints.")
                return False
            
            # 3.3. Check for convergence
            # For simplicity, we'll just stop after a fixed number of iterations
            # In a real implementation, you might check if the solutions have stabilized
            if iteration >= max_iterations:
                converged = True
                logging.info("Reached maximum iterations.")
            
            # Update traffic capacity usage for next iteration
            if not converged:
                capacity_usage = self.traffic_model.get_capacity_utilization()
                self.sched_model.traffic_capacity_usage = capacity_usage
        
        logging.info(f"Integrated solution completed in {iteration} iterations.")
        return True
    
    def solve_daily(self, traffic_dates=None, traffic_data=None, time_limit=3600, gap=0.01, verbose=1):
        """Solve the daily traffic flow problems for affected days"""
        if self.sched_model is None:
            logging.error("Models not initialized. Call initialize_models() first.")
            return False
        
        # 1. First, solve the scheduling model
        logging.info("Solving scheduling model...")
        success = self.solve_scheduling(None, time_limit, gap, verbose)
        if not success:
            logging.error("Failed to solve scheduling model.")
            return False
        
        # Get capacity blockings from scheduling model
        capacity_blockings = self.sched_model.get_capacity_blockings()
        
        # Get affected traffic days
        affected_days = self.sched_model.get_affected_traffic_days()
        
        # 2. For each affected day, solve the traffic flow model
        daily_results = {}
        
        for day in affected_days:
            logging.info(f"Solving traffic flow model for {day}...")
            
            # Filter capacity blockings for this day
            day_blockings = {}
            day_start = datetime.datetime.combine(day, datetime.time.min)
            day_end = datetime.datetime.combine(day, datetime.time.max)
            
            for (link_id, period), blocking in capacity_blockings.items():
                period_start = self.problem['plan'].get_period_start(period)
                if day_start <= period_start <= day_end:
                    day_blockings[(link_id, period)] = blocking
            
            # If no blockings for this day, skip it
            if not day_blockings:
                continue
            
            # Create a new traffic model for this day
            day_model = TrafficFlowModel(
                network=self.problem['network'],
                demand=self.problem['demand'],
                routes=self.problem['routes'],
                params=self.problem['params']['traffic'],
                plan=self.problem['plan']
            )
            
            # Solve the model for this day
            day_model.build_model(day_blockings)
            success = day_model.solve(time_limit, gap, verbose)
            
            if success:
                daily_results[day] = day_model.results
            else:
                logging.error(f"Failed to solve traffic flow model for {day}.")
        
        # Store the daily results
        self.results['daily_traffic'] = daily_results
        
        return len(daily_results) > 0
    
    def get_results(self):
        """Get the results of the optimization"""
        return self.results
    
    def get_schedule(self):
        """Get the project schedule"""
        if self.results['sched'] is None:
            logging.error("No scheduling results available.")
            return None
        
        return self.sched_model.get_project_schedule()
    
    def get_capacity_blockings(self):
        """Get the capacity blockings"""
        if self.results['sched'] is None:
            logging.error("No scheduling results available.")
            return None
        
        return self.sched_model.get_capacity_blockings()
    
    def get_affected_days(self):
        """Get the affected traffic days"""
        if self.results['sched'] is None:
            logging.error("No scheduling results available.")
            return None
        
        return self.sched_model.get_affected_traffic_days()
    
    def get_traffic_impact(self):
        """Get the traffic impact summary"""
        if self.results['traffic'] is None:
            logging.error("No traffic results available.")
            return None
        
        return self.traffic_model.get_traffic_impact_summary()
    
    def get_daily_traffic_impact(self):
        """Get the daily traffic impact summary"""
        if 'daily_traffic' not in self.results or not self.results['daily_traffic']:
            logging.error("No daily traffic results available.")
            return None
        
        daily_impact = {}
        for day, results in self.results['daily_traffic'].items():
            if 'flows' in results:
                # Create a temporary traffic model to calculate the impact
                temp_model = TrafficFlowModel(
                    network=self.problem['network'],
                    demand=self.problem['demand'],
                    routes=self.problem['routes'],
                    params=self.problem['params']['traffic'],
                    plan=self.problem['plan']
                )
                temp_model.results = results
                daily_impact[day] = temp_model.get_traffic_impact_summary()
        
        return daily_impact
    
    def write_results_to_files(self, output_dir):
        """Write results to files"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write scheduling results
        if self.results['sched'] is not None:
            sched_file = os.path.join(output_dir, 'schedule_results.xml')
            self.sched_model.write_results_to_file(sched_file)
            logging.info(f"Scheduling results written to {sched_file}")
        
        # Write traffic results
        if self.results['traffic'] is not None:
            traffic_file = os.path.join(output_dir, 'traffic_results.xml')
            self.traffic_model.write_results_to_file(traffic_file)
            logging.info(f"Traffic results written to {traffic_file}")
        
        # Write daily traffic results
        if 'daily_traffic' in self.results and self.results['daily_traffic']:
            daily_dir = os.path.join(output_dir, 'daily_traffic')
            if not os.path.exists(daily_dir):
                os.makedirs(daily_dir)
            
            for day, results in self.results['daily_traffic'].items():
                day_str = day.strftime('%Y-%m-%d')
                day_file = os.path.join(daily_dir, f'traffic_{day_str}.xml')
                
                # Create a temporary traffic model to write the results
                temp_model = TrafficFlowModel(
                    network=self.problem['network'],
                    demand=self.problem['demand'],
                    routes=self.problem['routes'],
                    params=self.problem['params']['traffic'],
                    plan=self.problem['plan']
                )
                temp_model.results = results
                temp_model.write_results_to_file(day_file)
            
            logging.info(f"Daily traffic results written to {daily_dir}")
        
        # Write summary report
        summary_file = os.path.join(output_dir, 'summary_report.txt')
        with open(summary_file, 'w') as f:
            f.write("TCR Optimization Summary Report\n")
            f.write("==============================\n\n")
            
            # Scheduling summary
            if self.results['sched'] is not None:
                f.write("Scheduling Results:\n")
                f.write(f"  - Objective: {self.results['sched']['objective']:.2f}\n")
                f.write(f"  - Cancelled projects: {len(self.results['sched']['cancelled_projects'])}\n")
                f.write(f"  - Affected days: {len(self.get_affected_days())}\n\n")
            
            # Traffic summary
            if self.results['traffic'] is not None:
                impact = self.get_traffic_impact()
                f.write("Traffic Impact:\n")
                f.write(f"  - Cancelled trains: {impact['total_cancelled']:.2f}\n")
                f.write(f"  - Delayed trains: {impact['total_delayed']:.2f}\n")
                f.write(f"  - Diverted trains: {impact['total_diverted']:.2f}\n\n")
                
                f.write("Traffic Impact by Train Type:\n")
                for train_type, count in impact.get('cancelled_by_type', {}).items():
                    f.write(f"  - {train_type} cancelled: {count:.2f}\n")
                for train_type, count in impact.get('delayed_by_type', {}).items():
                    f.write(f"  - {train_type} delayed: {count:.2f}\n")
                for train_type, count in impact.get('diverted_by_type', {}).items():
                    f.write(f"  - {train_type} diverted: {count:.2f}\n\n")
            
            # Daily traffic summary
            if 'daily_traffic' in self.results and self.results['daily_traffic']:
                daily_impact = self.get_daily_traffic_impact()
                f.write("Daily Traffic Impact:\n")
                for day, impact in daily_impact.items():
                    day_str = day.strftime('%Y-%m-%d')
                    f.write(f"  {day_str}:\n")
                    f.write(f"    - Cancelled trains: {impact['total_cancelled']:.2f}\n")
                    f.write(f"    - Delayed trains: {impact['total_delayed']:.2f}\n")
                    f.write(f"    - Diverted trains: {impact['total_diverted']:.2f}\n")
        
        logging.info(f"Summary report written to {summary_file}")
        
        return True