# This file is part of the SATT-BP tool

# src/optimization_models/plan_data.py
import xml.etree.ElementTree as ET
import logging
import datetime

class Network:
    """
    Class to store network data (nodes and links)
    """
    def __init__(self):
        self.nodes = {}  # node_id -> node object
        self.links = {}  # link_id -> link object
    
    def add_node(self, node_id, name=None, lat=None, lon=None, merge_group=None):
        """Add a node to the network"""
        self.nodes[node_id] = {
            'id': node_id,
            'name': name,
            'lat': lat,
            'lon': lon,
            'merge_group': merge_group
        }
        return self.nodes[node_id]
    
    def add_link(self, link_id, from_node, to_node, length=None, tracks=None, capacity=10):
        """Add a link to the network"""
        self.links[link_id] = {
            'id': link_id,
            'from_node': from_node,
            'to_node': to_node,
            'length': length,
            'tracks': tracks,
            'capacity': capacity
        }
        return self.links[link_id]
    
    def get_link_capacity(self, link_id):
        """Get capacity for a link, defaulting to 10 if not specified"""
        if link_id in self.links and 'capacity' in self.links[link_id]:
            return self.links[link_id]['capacity']
        return 10  # Default capacity
    

    def normalize_names(self):
        """
        Normalize node and link names to handle special characters
        """
        # Normalize nodes
        normalized_nodes = {}
        for node_id, node_data in list(self.nodes.items()):
            normalized_id = self._normalize_name(node_id)
            normalized_node = node_data.copy()
            normalized_node['id'] = normalized_id
            normalized_nodes[normalized_id] = normalized_node
        self.nodes = normalized_nodes

        # Normalize links
        normalized_links = {}
        for link_id, link_data in list(self.links.items()):
            normalized_id = self._normalize_name(link_id)
            normalized_link = link_data.copy()
            
            # Normalize link ID
            normalized_link['id'] = normalized_id
            
            # Normalize from and to nodes
            normalized_link['from_node'] = self._normalize_name(normalized_link['from_node'])
            normalized_link['to_node'] = self._normalize_name(normalized_link['to_node'])
            
            normalized_links[normalized_id] = normalized_link
        self.links = normalized_links

    def _normalize_name(self, name):
        """
        Normalize a single name by replacing special characters
        """
        return (name.replace('ö', 'o')
                .replace('ä', 'a')
                .replace('å', 'a')
                .replace('Ö', 'O')
                .replace('Ä', 'A')
                .replace('Å', 'A')
                .replace('Ü', 'U')
                .replace('ü', 'u'))
    

    @classmethod
    def from_xml(cls, xml_file):
        """Load network data from XML file"""
        network = cls()
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Parse nodes
            nodes_elem = root.find('nodes')
            if nodes_elem is not None:
                for node_elem in nodes_elem.findall('node'):
                    node_id = node_elem.get('id')
                    name = node_elem.get('name')
                    lat = float(node_elem.get('lat')) if node_elem.get('lat') is not None else None
                    lon = float(node_elem.get('lon')) if node_elem.get('lon') is not None else None
                    merge_group = node_elem.get('merge_group')
                    
                    network.add_node(node_id, name, lat, lon, merge_group)
            
            # Parse links
            links_elem = root.find('links')
            if links_elem is not None:
                for link_elem in links_elem.findall('link'):
                    link_id = link_elem.get('id')
                    from_node = link_elem.get('from')
                    to_node = link_elem.get('to')
                    length = float(link_elem.get('length')) if link_elem.get('length') is not None else None
                    tracks = int(link_elem.get('tracks')) if link_elem.get('tracks') is not None else None
                    capacity = int(link_elem.get('capacity')) if link_elem.get('capacity') is not None else 10
                    
                    network.add_link(link_id, from_node, to_node, length, tracks, capacity)

            network.normalize_names()
            
            return network
        
        except Exception as e:
            logging.error(f"Error loading network from XML: {e}")
            return None
    
    def __str__(self):
        return f"Network with {len(self.nodes)} nodes and {len(self.links)} links"


class Plan:
    """
    Class to store planning period information
    """
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.period_length = None  # Length of time periods in hours
        self.num_periods = None
        self.traffic_start = None  # When traffic starts within the plan
        self.traffic_end = None    # When traffic ends within the plan
    
    def set_planning_period(self, start_time, end_time, period_length=8):
        """Set the planning period and calculate the number of periods"""
        self.start_time = start_time
        self.end_time = end_time
        self.period_length = period_length
        
        # Calculate number of periods
        time_diff = (end_time - start_time).total_seconds() / 3600  # Hours
        self.num_periods = int(time_diff / period_length)
        
        return self.num_periods
    
    def set_traffic_window(self, traffic_start, traffic_end):
        """Set when traffic starts and ends within the planning period"""
        self.traffic_start = traffic_start
        self.traffic_end = traffic_end
    
    def is_in_traffic_window(self, time):
        """Check if a given time is within the traffic window"""
        return self.traffic_start <= time <= self.traffic_end
    
    def get_period_index(self, time):
        """Get the index of the period that contains the given time"""
        if time < self.start_time or time > self.end_time:
            return None
        
        hours_since_start = (time - self.start_time).total_seconds() / 3600
        return int(hours_since_start / self.period_length)
    
    def get_period_start(self, period_index):
        """Get the start time of a period by its index"""
        if period_index < 0 or period_index >= self.num_periods:
            return None
        
        return self.start_time + datetime.timedelta(hours=period_index * self.period_length)
    
    def get_period_end(self, period_index):
        """Get the end time of a period by its index"""
        if period_index < 0 or period_index >= self.num_periods:
            return None
        
        return self.start_time + datetime.timedelta(hours=(period_index + 1) * self.period_length)
    
    def __str__(self):
        return f"Plan with {self.num_periods} periods of {self.period_length}h from {self.start_time} to {self.end_time}"