# This file is part of the SATT-BP tool

# src/optimization_models/traffic_flow.py
import xml.etree.ElementTree as ET
import logging
import datetime
import pandas as pd
import numpy as np
from pyscipopt import Model, quicksum

class Demand:
    """
    Class to store traffic demand data (train lines, volumes, etc.)
    """
    def __init__(self):
        self.lines = {}  # line_id -> line object
        self.demand = {}  # (line_id, start_hr, end_hr) -> demand (trains)
        self.train_types = {}  # train_type_id -> train_type object
    
    def add_train_type(self, type_id, name=None):
        """Add a train type"""
        self.train_types[type_id] = {
            'id': type_id,
            'name': name
        }
        return self.train_types[type_id]
    
    def add_line(self, line_id, origin, destination, train_type):
        """Add a traffic line"""
        self.lines[line_id] = {
            'id': line_id,
            'origin': origin,
            'destination': destination,
            'train_type': train_type
        }
        return self.lines[line_id]
    
    def add_demand(self, line_id, start_hr, end_hr, demand):
        """Add demand for a traffic line during a time window"""
        key = (line_id, start_hr, end_hr)
        self.demand[key] = demand
        return demand
    
    def get_demand(self, line_id, start_hr, end_hr):
        """Get demand for a traffic line during a time window"""
        key = (line_id, start_hr, end_hr)
        return self.demand.get(key, 0)
    
    def get_all_lines(self):
        """Get all traffic lines"""
        return self.lines.keys()
    
    def get_line_train_type(self, line_id):
        """Get train type for a line"""
        if line_id in self.lines:
            return self.lines[line_id]['train_type']
        return None
    
    @classmethod
    def from_xml(cls, xml_file):
        """Load demand data from XML file"""
        demand = cls()
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Parse train types
            train_types_elem = root.find('train_types')
            if train_types_elem is not None:
                for type_elem in train_types_elem.findall('train_type'):
                    type_id = type_elem.get('id')
                    name = type_elem.get('name')
                    demand.add_train_type(type_id, name)
            
            # Parse lines
            lines_elem = root.find('lines')
            if lines_elem is not None:
                for line_elem in lines_elem.findall('line'):
                    line_id = line_elem.get('id')
                    origin = line_elem.get('origin')
                    destination = line_elem.get('destination')
                    train_type = line_elem.get('train_type')
                    demand.add_line(line_id, origin, destination, train_type)
            
            # Parse demand
            demand_elem = root.find('line_demand')
            if demand_elem is not None:
                for dem_elem in demand_elem.findall('demand'):
                    line_id = dem_elem.get('line')
                    start_hr = float(dem_elem.get('startHr'))
                    end_hr = float(dem_elem.get('endHr'))
                    dem_value = float(dem_elem.get('demand'))
                    demand.add_demand(line_id, start_hr, end_hr, dem_value)
            
            return demand
        
        except Exception as e:
            logging.error(f"Error loading demand from XML: {e}")
            return None
    
    def __str__(self):
        return f"Demand with {len(self.lines)} lines and {len(self.demand)} demand entries"


class Routes:
    """
    Class to store route data (paths through the network for each line)
    """
    def __init__(self):
        self.line_routes = {}  # line_id -> route object
        self.link_durations = {}  # (line_id, link_id) -> duration
        self.diversions = {}  # (line_id, blocked_link) -> alternative route
    
    def add_line_route(self, line_id, route):
        """Add a route for a traffic line"""
        self.line_routes[line_id] = route
        return route
    
    def add_link_duration(self, line_id, link_id, duration):
        """Add travel time for a link on a specific line"""
        key = (line_id, link_id)
        self.link_durations[key] = duration
        return duration
    
    def add_diversion(self, line_id, blocked_link, alternative_route, additional_time=0):
        """Add a diversion route for when a link is blocked"""
        key = (line_id, blocked_link)
        self.diversions[key] = {
            'route': alternative_route,
            'additional_time': additional_time
        }
        return self.diversions[key]
    
    def get_line_route(self, line_id):
        """Get the normal route for a traffic line"""
        return self.line_routes.get(line_id, None)
    
    def get_link_duration(self, line_id, link_id):
        """Get travel time for a link on a specific line"""
        key = (line_id, link_id)
        return self.link_durations.get(key, 0)
    
    def get_diversion(self, line_id, blocked_link):
        """Get a diversion route for when a link is blocked"""
        key = (line_id, blocked_link)
        return self.diversions.get(key, None)
    
    def get_all_links_for_line(self, line_id):
        """Get all links used by a line in its normal route"""
        if line_id not in self.line_routes:
            return []
        
        route = self.line_routes[line_id]
        return route.split('-')
    
    @classmethod
    def from_xml(cls, xml_file):
        """Load routes data from XML file"""
        routes = cls()
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Parse line routes
            route_elems = root.findall('.//line_route')
            for route_elem in route_elems:
                line_id = route_elem.get('line')
                route = route_elem.get('route')
                routes.add_line_route(line_id, route)
                
                # Parse link durations
                for dur_elem in route_elem.findall('dur'):
                    link_id = dur_elem.get('link')
                    duration = float(dur_elem.text)
                    routes.add_link_duration(line_id, link_id, duration)
            
            # Parse diversions if they exist
            diversion_elems = root.findall('.//diversion')
            for div_elem in diversion_elems:
                line_id = div_elem.get('line')
                blocked_link = div_elem.get('blocked_link')
                alternative_route = div_elem.get('route')
                additional_time = float(div_elem.get('additional_time', 0))
                routes.add_diversion(line_id, blocked_link, alternative_route, additional_time)
            
            return routes
        
        except Exception as e:
            logging.error(f"Error loading routes from XML: {e}")
            return None
    
    def __str__(self):
        return f"Routes for {len(self.line_routes)} lines with {len(self.diversions)} diversions"


class Params:
    """
    Class to store parameters for the traffic flow model
    """
    def __init__(self):
        self.cancellation_cost = {}  # train_type or line_id -> cost
        self.displacement_cost = {}  # train_type or line_id -> cost
        self.operation_cost = {}  # train_type or line_id -> cost
        self.max_rel_increase = {}  # train_type or line_id -> max relative travel time increase
        self.max_abs_increase = {}  # train_type or line_id -> max absolute travel time increase (hours)
    
    def set_cancellation_cost(self, key, value):
        """Set cancellation cost for a train type or line"""
        self.cancellation_cost[key] = value
    
    def set_displacement_cost(self, key, value):
        """Set displacement cost for a train type or line"""
        self.displacement_cost[key] = value
    
    def set_operation_cost(self, key, value):
        """Set operation cost for a train type or line"""
        self.operation_cost[key] = value
    
    def set_max_rel_increase(self, key, value):
        """Set maximum relative travel time increase for a train type or line"""
        self.max_rel_increase[key] = value
    
    def set_max_abs_increase(self, key, value):
        """Set maximum absolute travel time increase for a train type or line"""
        self.max_abs_increase[key] = value
    
    def get_cancellation_cost(self, line_id, train_type):
        """Get cancellation cost for a line, falling back to train type if not specified"""
        if line_id in self.cancellation_cost:
            return self.cancellation_cost[line_id]
        if train_type in self.cancellation_cost:
            return self.cancellation_cost[train_type]
        return self.cancellation_cost.get('*', 10)  # Default value
    
    def get_displacement_cost(self, line_id, train_type):
        """Get displacement cost for a line, falling back to train type if not specified"""
        if line_id in self.displacement_cost:
            return self.displacement_cost[line_id]
        if train_type in self.displacement_cost:
            return self.displacement_cost[train_type]
        return self.displacement_cost.get('*', 5)  # Default value
    
    def get_operation_cost(self, line_id, train_type):
        """Get operation cost for a line, falling back to train type if not specified"""
        if line_id in self.operation_cost:
            return self.operation_cost[line_id]
        if train_type in self.operation_cost:
            return self.operation_cost[train_type]
        return self.operation_cost.get('*', 1)  # Default value
    
    def get_max_rel_increase(self, line_id, train_type):
        """Get maximum relative travel time increase for a line"""
        if line_id in self.max_rel_increase:
            return self.max_rel_increase[line_id]
        if train_type in self.max_rel_increase:
            return self.max_rel_increase[train_type]
        return self.max_rel_increase.get('*', 1.2)  # Default: 20% increase
    
    def get_max_abs_increase(self, line_id, train_type):
        """Get maximum absolute travel time increase for a line"""
        if line_id in self.max_abs_increase:
            return self.max_abs_increase[line_id]
        if train_type in self.max_abs_increase:
            return self.max_abs_increase[train_type]
        return self.max_abs_increase.get('*', 2.0)  # Default: 2 hours
    
    @classmethod
    def from_xml(cls, xml_elem):
        """Load parameters from XML element"""
        params = cls()
        
        try:
            # Parse key-value parameters
            for key_val in xml_elem.findall('keyVal'):
                key = key_val.get('key')
                value = float(key_val.text)
                
                if key.startswith('ct_cancel'):
                    params.set_cancellation_cost(key.replace('ct_cancel_', ''), value)
                elif key.startswith('ct_post'):
                    params.set_displacement_cost(key.replace('ct_post_', ''), value)
                elif key.startswith('ct_time'):
                    params.set_operation_cost(key.replace('ct_time_', ''), value)
                elif key.startswith('mx_inc_rel'):
                    params.set_max_rel_increase(key.replace('mx_inc_rel_', ''), value)
                elif key.startswith('mx_inc_abs'):
                    params.set_max_abs_increase(key.replace('mx_inc_abs_', ''), value)
            
            return params
        
        except Exception as e:
            logging.error(f"Error loading parameters from XML: {e}")
            return None
    
    def __str__(self):
        return f"Traffic flow parameters with {len(self.cancellation_cost)} cancellation costs, {len(self.displacement_cost)} displacement costs"


class TrafficFlowModel:
    """
    Class to solve the traffic flow allocation problem
    """
    def __init__(self, network, demand, routes, params, plan):
        self.network = network
        self.demand = demand
        self.routes = routes
        self.params = params
        self.plan = plan
        self.model = None
        self.variables = {}
        self.results = {}
    
    def build_model(self, capacity_constraints=None):
        """
        Build the traffic flow optimization model
        
        Parameters:
        ----------
        capacity_constraints : dict
            Dictionary of capacity constraints in the form {(link_id, period): blocked_capacity}
        """
        self.model = Model("TrafficFlow")
        
        # Get all time periods in the planning horizon
        periods = range(self.plan.num_periods)
        
        # Dictionary to store all variables
        self.variables = {
            'flow': {},     # (line, route, period) -> flow variable
            'cancel': {},   # line -> cancellation variable
            'delay': {}     # line -> delay variable
        }
        
        # 1. Create variables for each line
        for line_id in self.demand.get_all_lines():
            train_type = self.demand.get_line_train_type(line_id)
            
            # Create cancellation variable for the line
            self.variables['cancel'][line_id] = self.model.addVar(
                vtype="C",
                name=f"cancel_{line_id}",
                lb=0.0,
                ub=1.0
            )
            
            # Create delay variable for the line
            self.variables['delay'][line_id] = self.model.addVar(
                vtype="C",
                name=f"delay_{line_id}",
                lb=0.0
            )
            
            # Get normal route for the line
            normal_route = self.routes.get_line_route(line_id)
            if normal_route is None:
                continue
            
            # Create flow variables for the line's normal route
            for period in periods:
                if self.plan.is_in_traffic_window(self.plan.get_period_start(period)):
                    key = (line_id, 'normal', period)
                    self.variables['flow'][key] = self.model.addVar(
                        vtype="C",
                        name=f"flow_{line_id}_normal_{period}",
                        lb=0.0
                    )
            
            # Create flow variables for each diversion route
            for link_id in self.routes.get_all_links_for_line(line_id):
                diversion = self.routes.get_diversion(line_id, link_id)
                if diversion is not None:
                    for period in periods:
                        if self.plan.is_in_traffic_window(self.plan.get_period_start(period)):
                            key = (line_id, f"div_{link_id}", period)
                            self.variables['flow'][key] = self.model.addVar(
                                vtype="C",
                                name=f"flow_{line_id}_div_{link_id}_{period}",
                                lb=0.0
                            )
        
        # 2. Add constraints
        
        # Demand satisfaction constraints
        for line_id in self.demand.get_all_lines():
            total_demand = 0
            
            # Sum up all demand for this line across all time periods
            for key, demand_val in self.demand.demand.items():
                if key[0] == line_id:
                    total_demand += demand_val
            
            # Total flow variables for all routes of this line
            flow_vars = []
            for key, var in self.variables['flow'].items():
                if key[0] == line_id:
                    flow_vars.append(var)
            
            # Constraint: sum of flows + cancellations = total demand
            if flow_vars:
                self.model.addCons(
                    quicksum(flow_vars) + self.variables['cancel'][line_id] * total_demand == total_demand,
                    name=f"demand_{line_id}"
                )
        
        # Capacity constraints
        if capacity_constraints is not None:
            for (link_id, period), blocked_capacity in capacity_constraints.items():
                if link_id not in self.network.links:
                    continue
                
                # Get all flow variables using this link in this period
                link_vars = []
                for key, var in self.variables['flow'].items():
                    line_id, route_type, route_period = key
                    
                    # Skip if not the current period
                    if route_period != period:
                        continue
                    
                    # Check if this route uses the link
                    uses_link = False
                    if route_type == 'normal':
                        normal_route = self.routes.get_line_route(line_id)
                        if normal_route and link_id in normal_route.split('-'):
                            uses_link = True
                    elif route_type.startswith('div_'):
                        # Diversion routes - check if they DON'T avoid this link
                        blocked_link = route_type.replace('div_', '')
                        diversion = self.routes.get_diversion(line_id, blocked_link)
                        if diversion and link_id in diversion['route'].split('-'):
                            uses_link = True
                    
                    if uses_link:
                        link_vars.append(var)
                
                # Add capacity constraint if there are flows using this link
                if link_vars:
                    available_capacity = self.network.get_link_capacity(link_id) - blocked_capacity
                    if available_capacity > 0:
                        self.model.addCons(
                            quicksum(link_vars) <= available_capacity,
                            name=f"capacity_{link_id}_{period}"
                        )
        
        # Travel time constraints
        for line_id in self.demand.get_all_lines():
            train_type = self.demand.get_line_train_type(line_id)
            
            # Get normal route and travel time
            normal_route = self.routes.get_line_route(line_id)
            if normal_route is None:
                continue
            
            normal_time = sum(self.routes.get_link_duration(line_id, link_id) 
                              for link_id in normal_route.split('-'))
            
            # Get maximum allowed travel time increases
            max_rel_increase = self.params.get_max_rel_increase(line_id, train_type)
            max_abs_increase = self.params.get_max_abs_increase(line_id, train_type)
            
            # Calculate maximum allowed travel time
            max_time = min(
                normal_time * max_rel_increase,
                normal_time + max_abs_increase
            )
            
            # Add constraint for each diversion route
            for link_id in self.routes.get_all_links_for_line(line_id):
                diversion = self.routes.get_diversion(line_id, link_id)
                if diversion is not None:
                    # Calculate travel time for the diversion
                    div_time = sum(self.routes.get_link_duration(line_id, link) 
                                   for link in diversion['route'].split('-'))
                    div_time += diversion['additional_time']
                    
                    # If diversion time exceeds maximum allowed time, set the flow to 0
                    if div_time > max_time:
                        for period in periods:
                            key = (line_id, f"div_{link_id}", period)
                            if key in self.variables['flow']:
                                self.model.addCons(
                                    self.variables['flow'][key] == 0,
                                    name=f"max_time_{line_id}_div_{link_id}_{period}"
                                )
        
        # 3. Set objective function
        obj_terms = []
        
        # Cancellation costs
        for line_id, var in self.variables['cancel'].items():
            train_type = self.demand.get_line_train_type(line_id)
            total_demand = 0
            
            # Sum up all demand for this line
            for key, demand_val in self.demand.demand.items():
                if key[0] == line_id:
                    total_demand += demand_val
            
            # Get cancellation cost and add to objective
            cancel_cost = self.params.get_cancellation_cost(line_id, train_type)
            obj_terms.append(cancel_cost * var * total_demand)
        
        # Delay costs
        for line_id, var in self.variables['delay'].items():
            train_type = self.demand.get_line_train_type(line_id)
            delay_cost = self.params.get_displacement_cost(line_id, train_type)
            obj_terms.append(delay_cost * var)
        
        # Operation costs for each flow
        for key, var in self.variables['flow'].items():
            line_id, route_type, period = key
            train_type = self.demand.get_line_train_type(line_id)
            op_cost = self.params.get_operation_cost(line_id, train_type)
            
            # Add extra cost for diversions
            if route_type.startswith('div_'):
                blocked_link = route_type.replace('div_', '')
                diversion = self.routes.get_diversion(line_id, blocked_link)
                if diversion:
                    # Calculate extra cost based on additional time
                    extra_cost = diversion['additional_time'] * op_cost
                    obj_terms.append((op_cost + extra_cost) * var)
            else:
                obj_terms.append(op_cost * var)
        
        # Set the objective
        self.model.setObjective(quicksum(obj_terms), "minimize")
    
    def solve(self, time_limit=3600, gap=0.01, verbose=1):
        """Solve the traffic flow model"""
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
                'flows': {},
                'cancelled': {},
                'delayed': {}
            }
            
            # Extract flow values
            for key, var in self.variables['flow'].items():
                flow_val = self.model.getVal(var)
                if flow_val > 1e-6:  # Filter out very small values
                    self.results['flows'][key] = flow_val
            
            # Extract cancellation values
            for line_id, var in self.variables['cancel'].items():
                cancel_val = self.model.getVal(var)
                if cancel_val > 1e-6:  # Filter out very small values
                    self.results['cancelled'][line_id] = cancel_val
            
            # Extract delay values
            for line_id, var in self.variables['delay'].items():
                delay_val = self.model.getVal(var)
                if delay_val > 1e-6:  # Filter out very small values
                    self.results['delayed'][line_id] = delay_val
            
            return True
        else:
            logging.error(f"Optimization failed with status: {status}")
            return False
    
    def get_link_flows(self):
        """Calculate flows on each link in each period"""
        if not self.results:
            return {}
        
        link_flows = {}
        
        # Process each flow variable
        for key, flow_val in self.results['flows'].items():
            line_id, route_type, period = key
            
            # Determine which links this flow uses
            if route_type == 'normal':
                # Normal route
                normal_route = self.routes.get_line_route(line_id)
                if normal_route:
                    links = normal_route.split('-')
                    for link_id in links:
                        # Add flow to the link in this period
                        link_key = (link_id, period)
                        if link_key not in link_flows:
                            link_flows[link_key] = 0
                        link_flows[link_key] += flow_val
            elif route_type.startswith('div_'):
                # Diversion route
                blocked_link = route_type.replace('div_', '')
                diversion = self.routes.get_diversion(line_id, blocked_link)
                if diversion:
                    links = diversion['route'].split('-')
                    for link_id in links:
                        # Add flow to the link in this period
                        link_key = (link_id, period)
                        if link_key not in link_flows:
                            link_flows[link_key] = 0
                        link_flows[link_key] += flow_val
        
        return link_flows
    
    def get_capacity_utilization(self):
        """Calculate capacity utilization percentage for each link in each period"""
        link_flows = self.get_link_flows()
        capacity_utilization = {}
        
        for (link_id, period), flow in link_flows.items():
            capacity = self.network.get_link_capacity(link_id)
            utilization = flow / capacity if capacity > 0 else 1.0
            capacity_utilization[(link_id, period)] = utilization
        
        return capacity_utilization
    
    def get_traffic_impact_summary(self):
        """Get a summary of traffic impacts from the solution"""
        if not self.results:
            return {}
        
        summary = {
            'total_cancelled': 0,
            'total_delayed': 0,
            'total_diverted': 0,
            'cancelled_by_type': {},
            'delayed_by_type': {},
            'diverted_by_type': {}
        }
        
        # Calculate total cancelled trains
        for line_id, cancel_val in self.results['cancelled'].items():
            train_type = self.demand.get_line_train_type(line_id)
            total_demand = 0
            
            # Sum up all demand for this line
            for key, demand_val in self.demand.demand.items():
                if key[0] == line_id:
                    total_demand += demand_val
            
            cancelled_trains = cancel_val * total_demand
            summary['total_cancelled'] += cancelled_trains
            
            # Group by train type
            if train_type not in summary['cancelled_by_type']:
                summary['cancelled_by_type'][train_type] = 0
            summary['cancelled_by_type'][train_type] += cancelled_trains
        
        # Calculate total delayed trains
        for line_id, delay_val in self.results['delayed'].items():
            train_type = self.demand.get_line_train_type(line_id)
            
            # For simplicity, consider each delayed line as 1 delayed train
            summary['total_delayed'] += 1
            
            # Group by train type
            if train_type not in summary['delayed_by_type']:
                summary['delayed_by_type'][train_type] = 0
            summary['delayed_by_type'][train_type] += 1
        
        # Calculate total diverted trains
        for key, flow_val in self.results['flows'].items():
            line_id, route_type, period = key
            
            if route_type.startswith('div_'):
                train_type = self.demand.get_line_train_type(line_id)
                
                # Count the flow value as diverted trains
                summary['total_diverted'] += flow_val
                
                # Group by train type
                if train_type not in summary['diverted_by_type']:
                    summary['diverted_by_type'][train_type] = 0
                summary['diverted_by_type'][train_type] += flow_val
        
        return summary
    
    def write_results_to_file(self, filename):
        """Write results to a file in a structured format"""
        if not self.results:
            logging.error("No results to write. Solve the model first.")
            return False
        
        try:
            with open(filename, 'w') as f:
                f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
                f.write("<traffic_flows>\n")
                
                # Write summary
                f.write("  <summary>\n")
                f.write(f"    <status>{self.results['status']}</status>\n")
                f.write(f"    <objective>{self.results['objective']:.2f}</objective>\n")
                
                # Get and write impact summary
                impact = self.get_traffic_impact_summary()
                f.write(f"    <cancelled>{impact['total_cancelled']:.2f}</cancelled>\n")
                f.write(f"    <delayed>{impact['total_delayed']:.2f}</delayed>\n")
                f.write(f"    <diverted>{impact['total_diverted']:.2f}</diverted>\n")
                f.write("  </summary>\n")
                
                # Write flows
                f.write("  <flows>\n")
                for key, flow_val in self.results['flows'].items():
                    line_id, route_type, period = key
                    f.write(f"    <flow line=\"{line_id}\" route=\"{route_type}\" period=\"{period}\" value=\"{flow_val:.2f}\"/>\n")
                f.write("  </flows>\n")
                
                # Write cancellations
                f.write("  <cancellations>\n")
                for line_id, cancel_val in self.results['cancelled'].items():
                    f.write(f"    <cancel line=\"{line_id}\" value=\"{cancel_val:.2f}\"/>\n")
                f.write("  </cancellations>\n")
                
                # Write delays
                f.write("  <delays>\n")
                for line_id, delay_val in self.results['delayed'].items():
                    f.write(f"    <delay line=\"{line_id}\" value=\"{delay_val:.2f}\"/>\n")
                f.write("  </delays>\n")
                
                # Write capacity utilization
                f.write("  <capacity_utilization>\n")
                for (link_id, period), util in self.get_capacity_utilization().items():
                    f.write(f"    <util link=\"{link_id}\" period=\"{period}\" value=\"{util:.2f}\"/>\n")
                f.write("  </capacity_utilization>\n")
                
                f.write("</traffic_flows>")
            
            return True
        
        except Exception as e:
            logging.error(f"Error writing results to file: {e}")
            return False