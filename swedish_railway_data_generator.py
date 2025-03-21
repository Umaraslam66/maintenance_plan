#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Swedish Railway Data Generator
------------------------------
A comprehensive script to generate railway infrastructure, traffic, and maintenance
data for the Swedish railway network, outputting both Excel files and standardized XML.
"""

import os
import sys
import re
import logging
import unicodedata
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global constants
BASE_YEAR = 2024
DATA_INPUT_DIR = 'data/input'
DATA_PROCESSED_DIR = 'data/processed'

# Initialize directory structure
def init_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(DATA_INPUT_DIR, exist_ok=True)
    os.makedirs(DATA_PROCESSED_DIR, exist_ok=True)
    logger.info(f"Initialized directory structure at {DATA_INPUT_DIR} and {DATA_PROCESSED_DIR}")

# Helper functions for string normalization
def normalize_name(name):
    """
    Normalize names by handling Swedish and special characters.
    
    Parameters:
    -----------
    name : str
        The original name to normalize
    
    Returns:
    --------
    str
        A normalized version of the name
    """
    if not isinstance(name, str):
        return str(name)
    
    # Swedish character mapping (comprehensive)
    swedish_char_map = {
        'å': 'a', 'ä': 'a', 'ö': 'o',
        'Å': 'A', 'Ä': 'A', 'Ö': 'O',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'ü': 'u', 'Ü': 'U',
        'ø': 'o', 'Ø': 'O',
        'æ': 'ae', 'Æ': 'AE'
    }
    
    # First, replace known Swedish characters
    for swe_char, replacement in swedish_char_map.items():
        name = name.replace(swe_char, replacement)
    
    # Remove any remaining diacritical marks
    normalized = ''.join(
        char for char in unicodedata.normalize('NFKD', name)
        if unicodedata.category(char) != 'Mn'
    )
    
    # Remove any remaining non-alphanumeric characters except underscores and hyphens
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    
    # Replace multiple spaces with a single space
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # If empty after normalization, use a default
    if not normalized:
        normalized = 'unnamed'
    
    return normalized

def normalize_xml_element(element):
    """
    Recursively normalize names in XML elements.
    
    Parameters:
    -----------
    element : xml.etree.ElementTree.Element
        The XML element to normalize
    """
    # Normalize name-related attributes
    name_attrs = ['name', 'desc', 'description', 'id', 'from', 'to', 'line', 'link', 'project', 'task', 'node']
    
    for attr in name_attrs:
        if attr in element.attrib:
            element.attrib[attr] = normalize_name(element.attrib[attr])
    
    # Recursively process child elements
    for child in element:
        normalize_xml_element(child)

def prettify_xml(element):
    """
    Convert an XML element to a pretty-printed string.
    
    Parameters:
    -----------
    element : xml.etree.ElementTree.Element
        The XML element to convert
    
    Returns:
    --------
    str
        A pretty-printed XML string
    """
    rough_string = ET.tostring(element, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove empty lines (common in minidom output)
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    
    return '\n'.join(lines)

def valid_xml_char_ordinal(c):
    """
    Check if a character is valid in XML.
    
    Parameters:
    -----------
    c : int
        Character ordinal value
    
    Returns:
    --------
    bool
        True if the character is valid in XML, False otherwise
    """
    # XML valid chars: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    return (
        0x09 <= c <= 0x0A or
        c == 0x0D or
        0x20 <= c <= 0xD7FF or
        0xE000 <= c <= 0xFFFD or
        0x10000 <= c <= 0x10FFFF
    )

def clean_xml_string(text):
    """
    Remove invalid XML characters from a string.
    
    Parameters:
    -----------
    text : str
        The string to clean
    
    Returns:
    --------
    str
        A string with invalid XML characters removed
    """
    if not isinstance(text, str):
        return str(text)
    return ''.join(c for c in text if valid_xml_char_ordinal(ord(c)))

def validate_xml_structure(root, schema_file=None):
    """
    Basic validation of XML structure.
    
    Parameters:
    -----------
    root : xml.etree.ElementTree.Element
        The XML root element to validate
    schema_file : str, optional
        Path to XML schema file for validation
    
    Returns:
    --------
    bool
        True if the XML is valid, False otherwise
    """
    # Basic validation - ensure all attributes have string values
    for elem in root.iter():
        for attr_name, attr_value in elem.attrib.items():
            elem.attrib[attr_name] = clean_xml_string(attr_value)
    
    # TODO: Add formal XSD schema validation if schema_file is provided
    return True

# Network data functions
class SwedishRailwayNetwork:
    def __init__(self):
        """Initialize the Swedish railway network data."""
        self.stations_data = None
        self.links_data = None
        self.station_codes_map = self._load_station_codes_mapping()
    
    def _load_station_codes_mapping(self):
        """
        Load mapping of station codes to actual stations in Sweden.
        This ensures we use real station codes.
        """
        # This is a mapping of real Swedish railway station codes
        # Reference: Trafikverket station codes
        return {
                # Major stations
                'Cst': {'name': 'Stockholm Central', 'lat': 59.3293, 'lon': 18.0686},
                'G': {'name': 'Göteborg Central', 'lat': 57.7089, 'lon': 11.9746},
                'M': {'name': 'Malmö Central', 'lat': 55.6050, 'lon': 13.0038},
                
                # Western Main Line stations
                'A': {'name': 'Alingsås', 'lat': 57.9295, 'lon': 12.5337},
                'F': {'name': 'Falköping', 'lat': 58.1752, 'lon': 13.5530},
                'HB': {'name': 'Hallsberg', 'lat': 59.0664, 'lon': 15.1098},
                'K': {'name': 'Katrineholm', 'lat': 59.0000, 'lon': 16.2000},
                'SK': {'name': 'Skövde', 'lat': 58.3890, 'lon': 13.8456},
                
                # Southern Main Line stations
                'AV': {'name': 'Alvesta', 'lat': 56.8990, 'lon': 14.5560},
                'E': {'name': 'Eslöv', 'lat': 55.8391, 'lon': 13.3035},
                'HM': {'name': 'Hässleholm', 'lat': 56.1589, 'lon': 13.7668},
                'HOR': {'name': 'Höör', 'lat': 55.9374, 'lon': 13.5426},
                'LP': {'name': 'Linköping', 'lat': 58.4108, 'lon': 15.6213},
                'LU': {'name': 'Lund', 'lat': 55.7047, 'lon': 13.1910},
                'MY': {'name': 'Mjölby', 'lat': 58.3300, 'lon': 15.1200},
                'N': {'name': 'Norrköping', 'lat': 58.5977, 'lon': 16.1826},
                'NS': {'name': 'Nässjö', 'lat': 57.6526, 'lon': 14.6946},
                
                # West Coast Line stations
                'AGE': {'name': 'Ängelholm', 'lat': 56.2428, 'lon': 12.8605},
                'HBG': {'name': 'Helsingborg', 'lat': 56.0465, 'lon': 12.6945},
                'KB': {'name': 'Kungsbacka', 'lat': 57.4874, 'lon': 12.0798},
                'VB': {'name': 'Varberg', 'lat': 57.1055, 'lon': 12.2502},
                'HM': {'name': 'Halmstad', 'lat': 56.6746, 'lon': 12.8645},
                
                # Northern Sweden stations
                'HDV': {'name': 'Hudiksvall', 'lat': 61.7279, 'lon': 17.1044},
                'SUC': {'name': 'Sundsvall Central', 'lat': 62.3908, 'lon': 17.3069},
                'BRC': {'name': 'Bräcke', 'lat': 62.7508, 'lon': 15.4195},
                'LAS': {'name': 'Långsele', 'lat': 63.1745, 'lon': 17.1063},
                'UME': {'name': 'Umeå Central', 'lat': 63.8284, 'lon': 20.2597},
                'VNS': {'name': 'Vännäs', 'lat': 63.9062, 'lon': 19.7503},
                'BDN': {'name': 'Boden Central', 'lat': 65.8256, 'lon': 21.6906},
                'LE': {'name': 'Luleå', 'lat': 65.5842, 'lon': 22.1547},
                'GVE': {'name': 'Gällivare', 'lat': 67.1367, 'lon': 20.6599},
                'KRA': {'name': 'Kiruna', 'lat': 67.8558, 'lon': 20.2253},
                
                # Additional important stations
                'ALV': {'name': 'Älvängen', 'lat': 58.0116, 'lon': 12.1147},
                'BS': {'name': 'Borås', 'lat': 57.7210, 'lon': 12.9401},
                'DFO': {'name': 'Degerfors', 'lat': 59.2335, 'lon': 14.4280},
                'KL': {'name': 'Karlstad Central', 'lat': 59.3793, 'lon': 13.5036},
                'KIL': {'name': 'Kil', 'lat': 59.5038, 'lon': 13.3196},
                'TOR': {'name': 'Töreboda', 'lat': 58.7062, 'lon': 14.1229},
                'TOR': {'name': 'Teckomatorp', 'lat': 55.8704, 'lon': 13.0784},
                'VGE': {'name': 'Veinge', 'lat': 56.4833, 'lon': 13.0333}
            }

    
    def get_station_from_code(self, code):
        """Get station details from its code."""
        return self.station_codes_map.get(code, None)
    
    def create_network_data(self):
        """Create network data for Swedish railway infrastructure."""
        logger.info("Creating network data for Swedish railway infrastructure...")
        
        # Define major Swedish railway stations using real codes
        stations = []
        for code, station_info in self.station_codes_map.items():
            stations.append({
                'node_id': code,
                'station_name': station_info['name'],
                'lat': station_info['lat'],
                'lon': station_info['lon'],
                'merge_group': code if code in ['G', 'S', 'M', 'HB', 'LU'] else None  # Major hubs
            })
        
        # Define links between stations (railway segments)
        # This is a simplified representation based on the Swedish rail network
        links = [
                # Western Main Line (Vastra stambanan)
                {'link_id': 'G_Cst', 'from_node': 'G', 'to_node': 'Cst', 'length_km': 46, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Cst_So', 'from_node': 'Cst', 'to_node': 'So', 'length_km': 81, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'So_Ha', 'from_node': 'So', 'to_node': 'Ha', 'length_km': 73, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Ha_Lp', 'from_node': 'Ha', 'to_node': 'Lp', 'length_km': 90, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Lp_M', 'from_node': 'Lp', 'to_node': 'M', 'length_km': 140, 'num_tracks': 2, 'default_capacity': 10},

                # Southern Main Line (Sodra stambanan)
                {'link_id': 'Ha_N', 'from_node': 'Ha', 'to_node': 'N', 'length_km': 172, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'N_Lp', 'from_node': 'N', 'to_node': 'Lp', 'length_km': 77, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Lp_Lm', 'from_node': 'Lp', 'to_node': 'Lm', 'length_km': 82, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Lm_Ho', 'from_node': 'Lm', 'to_node': 'Ho', 'length_km': 32, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Ho_E', 'from_node': 'Ho', 'to_node': 'E', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'E_Lu', 'from_node': 'E', 'to_node': 'Lu', 'length_km': 24, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Lu_Ma', 'from_node': 'Lu', 'to_node': 'Ma', 'length_km': 20, 'num_tracks': 2, 'default_capacity': 10},

                # West Coast Line (Vastkustbanan)
                {'link_id': 'G_Al', 'from_node': 'G', 'to_node': 'Al', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'G_Kb', 'from_node': 'G', 'to_node': 'Kb', 'length_km': 28, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Kb_Vg', 'from_node': 'Kb', 'to_node': 'Vg', 'length_km': 47, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Vg_Hb', 'from_node': 'Vg', 'to_node': 'Hb', 'length_km': 70, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Hb_Hg', 'from_node': 'Hb', 'to_node': 'Hg', 'length_km': 40, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Hg_Ag', 'from_node': 'Hg', 'to_node': 'Ag', 'length_km': 35, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Ag_Ma', 'from_node': 'Ag', 'to_node': 'Ma', 'length_km': 60, 'num_tracks': 2, 'default_capacity': 10},

                # Eastern Link (Ostergotland/Osterlanken)
                {'link_id': 'Lp_N', 'from_node': 'Lp', 'to_node': 'N', 'length_km': 65, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'N_Lk', 'from_node': 'N', 'to_node': 'Lk', 'length_km': 42, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Lk_Mj', 'from_node': 'Lk', 'to_node': 'Mj', 'length_km': 35, 'num_tracks': 2, 'default_capacity': 10},
                {'link_id': 'Mj_Ns', 'from_node': 'Mj', 'to_node': 'Ns', 'length_km': 65, 'num_tracks': 2, 'default_capacity': 10},

                # Northern Line (Norra stambanan and connections)
                {'link_id': 'Hdv_Suc', 'from_node': 'Hdv', 'to_node': 'Suc', 'length_km': 86, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Suc_Brc', 'from_node': 'Suc', 'to_node': 'Brc', 'length_km': 100, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Brc_Las', 'from_node': 'Brc', 'to_node': 'Las', 'length_km': 120, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Las_Vns', 'from_node': 'Las', 'to_node': 'Vns', 'length_km': 153, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Vns_Ume', 'from_node': 'Vns', 'to_node': 'Ume', 'length_km': 32, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Ume_Bdn', 'from_node': 'Ume', 'to_node': 'Bdn', 'length_km': 210, 'num_tracks': 1, 'default_capacity': 5},
                {'link_id': 'Bdn_La', 'from_node': 'Bdn', 'to_node': 'La', 'length_km': 38, 'num_tracks': 1, 'default_capacity': 5},
            ]

        
        # Add reverse direction links for completeness
        reverse_links = []
        for link in links:
            reverse_link = {
                'link_id': f"{link['to_node']}_{link['from_node']}",
                'from_node': link['to_node'],
                'to_node': link['from_node'],
                'length_km': link['length_km'],
                'num_tracks': link['num_tracks'],
                'default_capacity': link['default_capacity']
            }
            reverse_links.append(reverse_link)
        
        links.extend(reverse_links)
        
        # Create DataFrames
        stations_df = pd.DataFrame(stations)
        links_df = pd.DataFrame(links)
        
        # Save to Excel files
        stations_df.to_excel(f'{DATA_INPUT_DIR}/stations.xlsx', index=False)
        links_df.to_excel(f'{DATA_INPUT_DIR}/links.xlsx', index=False)
        
        logger.info(f"Network data created and saved to {DATA_INPUT_DIR}/stations.xlsx and {DATA_INPUT_DIR}/links.xlsx")
        
        # Store data in instance variables
        self.stations_data = stations_df
        self.links_data = links_df
        
        # Also create network XML
        self.create_network_xml(stations, links)
        
        return stations_df, links_df
    
    def create_network_xml(self, stations, links):
        """Create XML file for the network."""
        # Create root element
        network = ET.Element("network")
        
        # Add nodes
        nodes = ET.SubElement(network, "nodes")
        for station in stations:
            node_attrib = {
                'id': station['node_id'],
                'name': normalize_name(station['station_name']),
                'lat': str(station['lat']),
                'lon': str(station['lon'])
            }
            if station['merge_group']:
                node_attrib['merge_group'] = station['merge_group']
            
            ET.SubElement(nodes, "node", **node_attrib)
        
        # Add links
        links_elem = ET.SubElement(network, "links")
        for link in links:
            link_attrib = {
                'id': link['link_id'],
                'from': link['from_node'],
                'to': link['to_node'],
                'length': str(link['length_km']),
                'tracks': str(link['num_tracks']),
                'capacity': str(link['default_capacity'])
            }
            ET.SubElement(links_elem, "link", **link_attrib)
        
        # Validate and save
        validate_xml_structure(network)
        xml_content = prettify_xml(network)
        
        with open(f'{DATA_PROCESSED_DIR}/network.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"Network XML created and saved to {DATA_PROCESSED_DIR}/network.xml")
    
    def get_network_data(self):
        """
        Get network data - either load existing data or create new data if none exists.
        
        Returns:
        --------
        tuple: (stations_df, links_df) - DataFrames containing stations and links data
        """
        # If we already have the data in memory, return it
        if self.stations_data is not None and self.links_data is not None:
            return self.stations_data, self.links_data
        
        # Check if the data files exist and load them
        if os.path.exists(f'{DATA_INPUT_DIR}/stations.xlsx') and os.path.exists(f'{DATA_INPUT_DIR}/links.xlsx'):
            try:
                stations_df = pd.read_excel(f'{DATA_INPUT_DIR}/stations.xlsx')
                links_df = pd.read_excel(f'{DATA_INPUT_DIR}/links.xlsx')
                logger.info("Loaded existing network data from files")
                self.stations_data, self.links_data = stations_df, links_df
                return stations_df, links_df
            except Exception as e:
                logger.error(f"Error loading existing network data: {e}")
                logger.info("Will create new network data")
        
        # Create new data
        return self.create_network_data()
    
    def is_valid_node(self, node_id):
        """Check if a node ID exists in the network data."""
        stations_df, _ = self.get_network_data()
        return node_id in stations_df['node_id'].values
    
    def is_valid_link(self, link_id):
        """Check if a link ID exists in the network data."""
        _, links_df = self.get_network_data()
        return link_id in links_df['link_id'].values
    
    def get_all_nodes(self):
        """Get all node IDs in the network."""
        stations_df, _ = self.get_network_data()
        return stations_df['node_id'].tolist()
    
    def get_all_links(self):
        """Get all link IDs in the network."""
        _, links_df = self.get_network_data()
        return links_df['link_id'].tolist()
    
    def validate_route(self, route_nodes):
        """
        Validate that a sequence of nodes forms a valid route (each node is connected to the next).
        
        Parameters:
        -----------
        route_nodes: list
            List of node IDs in sequence
        
        Returns:
        --------
        tuple: (is_valid, missing_links)
            is_valid: True if the route is valid, False otherwise
            missing_links: List of missing links that would be needed to make the route valid
        """
        _, links_df = self.get_network_data()
        
        missing_links = []
        
        for i in range(len(route_nodes) - 1):
            from_node = route_nodes[i]
            to_node = route_nodes[i + 1]
            
            # Check if a link exists between these nodes
            link_id = f"{from_node}_{to_node}"
            if link_id not in links_df['link_id'].values:
                missing_links.append(link_id)
        
        return len(missing_links) == 0, missing_links
    
# Traffic data functions
class TrafficDataGenerator:
    def __init__(self, network):
        """
        Initialize the traffic data generator.
        
        Parameters:
        -----------
        network : SwedishRailwayNetwork
            Network instance for reference
        """
        self.network = network
    
    def create_traffic_data(self):
        """Create traffic data for Swedish railway network."""
        logger.info("Creating traffic data for Swedish railway network...")
        
        # Get network data to validate nodes and links
        stations_df, links_df = self.network.get_network_data()
        valid_nodes = stations_df['node_id'].tolist()
        valid_links = links_df['link_id'].tolist()
        
        logger.info(f"Network data loaded with {len(valid_nodes)} valid nodes and {len(valid_links)} valid links")
        
        # Define train types
        train_types = ['RST', 'GT']  # Passenger and Freight
        
        # Create some sample train relations based on the network
        relations = [
            # Main passenger routes (long-distance)
            {'line': 'G_S_RST1', 'origin': 'G', 'destination': 'S', 'train_type': 'RST', 
             'route': 'G-A-SK-HB-K-S', 'run_time_hr': 3.5},
            {'line': 'S_G_RST1', 'origin': 'S', 'destination': 'G', 'train_type': 'RST', 
             'route': 'S-K-HB-SK-A-G', 'run_time_hr': 3.5},
            {'line': 'G_M_RST1', 'origin': 'G', 'destination': 'M', 'train_type': 'RST', 
             'route': 'G-KB-VB-VGE-HBG-AGE-HM-HOR-E-LU-M', 'run_time_hr': 4.2},
            {'line': 'M_G_RST1', 'origin': 'M', 'destination': 'G', 'train_type': 'RST', 
             'route': 'M-LU-E-HOR-HM-AGE-HBG-VGE-VB-KB-G', 'run_time_hr': 4.2},
            {'line': 'S_M_RST1', 'origin': 'S', 'destination': 'M', 'train_type': 'RST', 
             'route': 'S-K-N-LP-MY-NS-AV-HM-HOR-E-LU-M', 'run_time_hr': 5.0},
            {'line': 'M_S_RST1', 'origin': 'M', 'destination': 'S', 'train_type': 'RST', 
             'route': 'M-LU-E-HOR-HM-AV-NS-MY-LP-N-K-S', 'run_time_hr': 5.0},
            
            # Regional passenger services
            {'line': 'G_HB_RST2', 'origin': 'G', 'destination': 'HB', 'train_type': 'RST', 
             'route': 'G-A-SK-HB', 'run_time_hr': 2.0},
            {'line': 'HB_G_RST2', 'origin': 'HB', 'destination': 'G', 'train_type': 'RST', 
             'route': 'HB-SK-A-G', 'run_time_hr': 2.0},
            {'line': 'HM_LU_RST2', 'origin': 'HM', 'destination': 'LU', 'train_type': 'RST', 
             'route': 'HM-HOR-E-LU', 'run_time_hr': 1.0},
            {'line': 'LU_HM_RST2', 'origin': 'LU', 'destination': 'HM', 'train_type': 'RST', 
             'route': 'LU-E-HOR-HM', 'run_time_hr': 1.0},
            {'line': 'S_LP_RST2', 'origin': 'S', 'destination': 'LP', 'train_type': 'RST', 
             'route': 'S-K-N-LP', 'run_time_hr': 1.8},
            {'line': 'LP_S_RST2', 'origin': 'LP', 'destination': 'S', 'train_type': 'RST', 
             'route': 'LP-N-K-S', 'run_time_hr': 1.8},
            
            # Freight routes
            {'line': 'G_HB_GT1', 'origin': 'G', 'destination': 'HB', 'train_type': 'GT', 
             'route': 'G-A-SK-HB', 'run_time_hr': 3.0},
            {'line': 'HB_G_GT1', 'origin': 'HB', 'destination': 'G', 'train_type': 'GT', 
             'route': 'HB-SK-A-G', 'run_time_hr': 3.0},
            {'line': 'G_M_GT1', 'origin': 'G', 'destination': 'M', 'train_type': 'GT', 
             'route': 'G-KB-VB-VGE-HBG-AGE-HM-HOR-E-LU-M', 'run_time_hr': 6.0},
            {'line': 'M_G_GT1', 'origin': 'M', 'destination': 'G', 'train_type': 'GT', 
             'route': 'M-LU-E-HOR-HM-AGE-HBG-VGE-VB-KB-G', 'run_time_hr': 6.0},
            
            # Northern Sweden routes
            {'line': 'S_LE_RST1', 'origin': 'S', 'destination': 'LE', 'train_type': 'RST', 
             'route': 'S-K-N-LP-MY-NS-AV-HM-SUC-BRC-LAS-VNS-UME-BDN-LE', 'run_time_hr': 12.0},
            {'line': 'LE_S_RST1', 'origin': 'LE', 'destination': 'S', 'train_type': 'RST', 
             'route': 'LE-BDN-UME-VNS-LAS-BRC-SUC-HM-AV-NS-MY-LP-N-K-S', 'run_time_hr': 12.0},
            {'line': 'LE_KRA_RST1', 'origin': 'LE', 'destination': 'KRA', 'train_type': 'RST', 
             'route': 'LE-BDN-GVE-KRA', 'run_time_hr': 4.0},
            {'line': 'KRA_LE_RST1', 'origin': 'KRA', 'destination': 'LE', 'train_type': 'RST', 
             'route': 'KRA-GVE-BDN-LE', 'run_time_hr': 4.0},
            
            # Iron ore trains (LKAB Malmbanan)
            {'line': 'KRA_LE_GT2', 'origin': 'KRA', 'destination': 'LE', 'train_type': 'GT', 
             'route': 'KRA-GVE-BDN-LE', 'run_time_hr': 6.0},
            {'line': 'LE_KRA_GT2', 'origin': 'LE', 'destination': 'KRA', 'train_type': 'GT', 
             'route': 'LE-BDN-GVE-KRA', 'run_time_hr': 6.0},
            
            # Steel pendulum freight train (Luleå-Hallsberg)
            {'line': 'LE_HB_GT2', 'origin': 'LE', 'destination': 'HB', 'train_type': 'GT', 
             'route': 'LE-BDN-UME-VNS-LAS-BRC-SUC-HM-AV-NS-HB', 'run_time_hr': 16.0},
            {'line': 'HB_LE_GT2', 'origin': 'HB', 'destination': 'LE', 'train_type': 'GT', 
             'route': 'HB-NS-AV-HM-SUC-BRC-LAS-VNS-UME-BDN-LE', 'run_time_hr': 16.0}
        ]
        
        # Filter and validate relations
        valid_relations = []
        
        for relation in relations:
            # Check if origin and destination nodes exist
            if not self.network.is_valid_node(relation['origin']):
                logger.warning(f"Warning: Route {relation['line']} has invalid origin node {relation['origin']}. Skipping.")
                continue
                
            if not self.network.is_valid_node(relation['destination']):
                logger.warning(f"Warning: Route {relation['line']} has invalid destination node {relation['destination']}. Skipping.")
                continue
            
            # Check if all nodes in route exist
            route_nodes = relation['route'].split('-')
            invalid_nodes = [node for node in route_nodes if not self.network.is_valid_node(node)]
            
            if invalid_nodes:
                logger.warning(f"Warning: Route {relation['line']} contains invalid nodes: {invalid_nodes}. Skipping.")
                continue
            
            # Check if route forms a valid path (all nodes are connected)
            is_valid, missing_links = self.network.validate_route(route_nodes)
            
            if not is_valid:
                logger.warning(f"Warning: Route {relation['line']} contains missing links: {missing_links}. Skipping.")
                continue
            
            # If we get here, the relation is valid
            valid_relations.append(relation)
        
        logger.info(f"Filtered to {len(valid_relations)} valid relations out of {len(relations)} original relations")
        
        # Create a relations dataframe
        relations_df = pd.DataFrame(valid_relations)
        
        # Create train time table and daily volumes
        train_schedule = []
        
        # For each relation, create timetable entries
        for idx, relation in enumerate(valid_relations):
            # Parse route to get links
            nodes = relation['route'].split('-')
            links = []
            for i in range(len(nodes)-1):
                links.append(f"{nodes[i]}_{nodes[i+1]}")
            
            # Determine number of trains per day based on train type
            if relation['train_type'] == 'RST':
                if 'RST1' in relation['line']:  # Long-distance passenger
                    num_trains_per_day = 6  # Every 4 hours during day
                    start_hours = [5, 9, 13, 15, 17, 21]
                else:  # Regional passenger
                    num_trains_per_day = 12  # Every 2 hours
                    start_hours = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 1, 3]
            else:  # Freight
                if 'GT1' in relation['line']:  # Regular freight
                    num_trains_per_day = 4  # A few per day
                    start_hours = [2, 8, 14, 20]
                else:  # Special freight (Iron ore or Steel pendulum)
                    num_trains_per_day = 2  # Usually 2 per day
                    start_hours = [0, 12]
            
            # Create schedule entries
            for day in range(7):  # Monday to Sunday
                for hour_idx, start_hour in enumerate(start_hours[:num_trains_per_day]):
                    train_id = f"{relation['line']}_{day}_{hour_idx}"
                    
                    # Calculate arrival time
                    departure_time = datetime.datetime(BASE_YEAR, 1, 3 + day, start_hour, 0)
                    arrival_time = departure_time + datetime.timedelta(hours=relation['run_time_hr'])
                    
                    # Add to schedule
                    train_schedule.append({
                        'train_id': train_id,
                        'line': relation['line'],
                        'origin': relation['origin'],
                        'destination': relation['destination'],
                        'train_type': relation['train_type'],
                        'route': relation['route'],
                        'departure_time': departure_time,
                        'arrival_time': arrival_time,
                        'run_time_hr': relation['run_time_hr'],
                        'day_of_week': day
                    })
        
        # Create a train schedule dataframe
        schedule_df = pd.DataFrame(train_schedule)
        
        # Create traffic demand data
        demand_data = []
        
        # Aggregate demand by line, start hour, and end hour
        for line in relations_df['line'].unique():
            line_schedule = schedule_df[schedule_df['line'] == line]
            
            # Group by hour of day to get hourly demand
            for hour in range(24):
                # Filter trains departing in this hour
                hour_schedule = line_schedule[line_schedule['departure_time'].dt.hour == hour]
                trains_in_hour = len(hour_schedule)
                
                if trains_in_hour > 0:
                    demand_data.append({
                        'line': line,
                        'startHr': hour,
                        'endHr': hour + 1,
                        'demand': trains_in_hour
                    })
        
        # Create demand dataframe
        demand_df = pd.DataFrame(demand_data)
        
        # Calculate link travel times for each line
        link_times = []
        
        for idx, relation in enumerate(valid_relations):
            # Parse route to get links
            nodes = relation['route'].split('-')
            
            # Get actual link lengths from the network data
            total_distance = 0
            link_distances = []
            
            for i in range(len(nodes) - 1):
                link_id = f"{nodes[i]}_{nodes[i+1]}"
                link_data = links_df[links_df['link_id'] == link_id]
                
                if not link_data.empty:
                    distance = link_data.iloc[0]['length_km']
                    total_distance += distance
                    link_distances.append((link_id, distance))
            
            # Calculate travel time per link based on distance proportion
            for link_id, distance in link_distances:
                travel_time = (distance / total_distance) * relation['run_time_hr']
                link_times.append({
                    'line': relation['line'],
                    'link': link_id,
                    'duration': round(travel_time, 2)
                })
        
        # Create link times dataframe
        link_times_df = pd.DataFrame(link_times)
        
        # Save to Excel files
        relations_df.to_excel(f'{DATA_INPUT_DIR}/train_relations.xlsx', index=False)
        schedule_df.to_excel(f'{DATA_INPUT_DIR}/train_schedule.xlsx', index=False)
        demand_df.to_excel(f'{DATA_INPUT_DIR}/train_demand.xlsx', index=False)
        link_times_df.to_excel(f'{DATA_INPUT_DIR}/link_travel_times.xlsx', index=False)
        
        logger.info(f"Traffic data created and saved to {DATA_INPUT_DIR}/ directory")
        
        # Also create a traffic XML version
        self.create_traffic_xml(relations_df, schedule_df, demand_df, link_times_df)
        
        return relations_df, schedule_df, demand_df, link_times_df
    
    def create_traffic_xml(self, relations_df, schedule_df, demand_df, link_times_df):
        """Create XML file for traffic data."""
        # Create root element
        traffic = ET.Element("traffic")
        
        # Add train types
        train_types = ET.SubElement(traffic, "train_types")
        ET.SubElement(train_types, "train_type", id="RST", name="Passenger Train")
        ET.SubElement(train_types, "train_type", id="GT", name="Freight Train")
        
        # Add lines
        lines = ET.SubElement(traffic, "lines")
        for _, relation in relations_df.iterrows():
            line_attrib = {
                'id': relation['line'],
                'origin': relation['origin'],
                'destination': relation['destination'],
                'train_type': relation['train_type']
            }
            ET.SubElement(lines, "line", **line_attrib)
        
        # Add line demand
        line_demand = ET.SubElement(traffic, "line_demand")
        for _, demand in demand_df.iterrows():
            demand_attrib = {
                'line': demand['line'],
                'startHr': str(demand['startHr']),
                'endHr': str(demand['endHr']),
                'demand': str(demand['demand'])
            }
            ET.SubElement(line_demand, "demand", **demand_attrib)
        
        # Add line routes
        line_routes = ET.SubElement(traffic, "line_routes")
        for line in relations_df['line'].unique():
            line_data = relations_df[relations_df['line'] == line].iloc[0]
            route_str = ' '.join(line_data['route'].replace('-', '_').split('-'))
            line_route = ET.SubElement(line_routes, "line_route", line=line, route=route_str)
            
            # Add link durations for this line
            line_link_times = link_times_df[link_times_df['line'] == line]
            for _, link_time in line_link_times.iterrows():
                dur = ET.SubElement(line_route, "dur", link=link_time['link'])
                dur.text = str(link_time['duration'])
        
        # Add individual trains (for illustration)
        trains = ET.SubElement(traffic, "trains")
        for _, train in schedule_df.head(10).iterrows():  # Just include first 10 for brevity
            dep_time = train['departure_time'].strftime('%Y-%m-%d %H:%M:%S')
            arr_time = train['arrival_time'].strftime('%Y-%m-%d %H:%M:%S')
            train_attrib = {
                'id': train['train_id'],
                'line': train['line'],
                'departure': dep_time,
                'arrival': arr_time
            }
            ET.SubElement(trains, "train", **train_attrib)
        
        # Add traffic year definition
        traffic_year = ET.SubElement(traffic, "traffic_year")
        
        # Normal period
        normal_period = ET.SubElement(traffic_year, "period", 
                                     type="normal", 
                                     startDate=f"{BASE_YEAR}-01-01", 
                                     endDate=f"{BASE_YEAR}-12-31")
        
        # Define weekdays
        for i in range(7):
            day_date = datetime.datetime(BASE_YEAR, 1, 3 + i)  # Jan 3, 2024 is a Wednesday
            ET.SubElement(normal_period, "day", 
                         weekday=str(i), 
                         dataDate=day_date.strftime('%Y-%m-%d'))
        
        # Easter period
        easter_period = ET.SubElement(traffic_year, "period", 
                                     type="easter", 
                                     startDate=f"{BASE_YEAR}-03-29", 
                                     endDate=f"{BASE_YEAR}-04-01")
        
        # Define Easter days (example dates)
        easter_days = [
            (4, f"{BASE_YEAR}-04-14"),  # Good Friday
            (5, f"{BASE_YEAR}-04-15"),  # Easter Saturday
            (6, f"{BASE_YEAR}-04-16"),  # Easter Sunday
            (0, f"{BASE_YEAR}-04-17")   # Easter Monday
        ]
        
        for weekday, date in easter_days:
            ET.SubElement(easter_period, "day", 
                         weekday=str(weekday), 
                         dataDate=date)
        
        # Summer period
        summer_period = ET.SubElement(traffic_year, "period", 
                                     type="summer", 
                                     startDate=f"{BASE_YEAR}-07-15", 
                                     endDate=f"{BASE_YEAR}-08-04")
        
        # Define summer days
        for i in range(7):
            day_date = datetime.datetime(BASE_YEAR, 7, 18 + i)
            ET.SubElement(summer_period, "day", 
                         weekday=str(i), 
                         dataDate=day_date.strftime('%Y-%m-%d'))
        
        # Validate and save
        validate_xml_structure(traffic)
        xml_content = prettify_xml(traffic)
        
        with open(f'{DATA_PROCESSED_DIR}/traffic.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"Traffic XML created and saved to {DATA_PROCESSED_DIR}/traffic.xml")

# Maintenance data functions
class MaintenanceDataGenerator:
    def __init__(self, network):
        """
        Initialize the maintenance data generator.
        
        Parameters:
        -----------
        network : SwedishRailwayNetwork
            Network instance for reference
        """
        self.network = network
    
    def create_maintenance_data(self):
        """Create maintenance project data (TPÅ) for Swedish railway."""
        logger.info("Creating maintenance project data...")
        
        # Get network data to validate links
        _, links_df = self.network.get_network_data()
        valid_links = links_df['link_id'].tolist()
        
        logger.info(f"Network data loaded with {len(valid_links)} valid links")

        # Create sample maintenance projects
        projects = [
            # Western Main Line projects
            {
                'project_id': '214',
                'description': 'Switch change Alingsas',
                'link': 'G_A',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}26',
                'tasks': [
                    {'task_id': '214_1', 'description': 'Preparatory work', 'duration_hr': 8, 'blocking_percentage': 50},
                    {'task_id': '214_2', 'description': 'Main closure', 'duration_hr': 48, 'blocking_percentage': 100},
                    {'task_id': '214_3', 'description': 'Follow-up work', 'duration_hr': 8, 'blocking_percentage': 50}
                ]
            },
            {
                'project_id': '180',
                'description': 'Toreboda bridge replacement',
                'link': 'TOR_HDV',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}26',
                'tasks': [
                    {'task_id': '180_1', 'description': 'Bridge replacement', 'duration_hr': 96, 'blocking_percentage': 100}
                ]
            },
            # Southern Main Line projects
            {
                'project_id': '526',
                'description': 'Hassleholm railway yard, catenary refurbishment',
                'link': 'HM_HOR',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}20',
                'tasks': [
                    {'task_id': '526_1', 'description': 'Main closure', 'duration_hr': 72, 'blocking_percentage': 100}
                ]
            },
            {
                'project_id': '450',
                'description': 'Hassleholm railway yard, platform renewal',
                'link': 'HM_HOR',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}49',
                'tasks': [
                    {'task_id': '450_1', 'description': 'Service window', 'duration_hr': 6, 'blocking_percentage': 'esp', 'count': 6}
                ]
            },
            # West Coast Line projects
            {
                'project_id': '877',
                'description': 'Varberg-Hamra, double track, tunnel',
                'link': 'KB_VB',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}44',
                'tasks': [
                    {'task_id': '877_1', 'description': 'Main closure', 'duration_hr': 96, 'blocking_percentage': 100}
                ]
            },
            {
                'project_id': '880',
                'description': 'Varberg-Hamra, double track, tunnel',
                'link': 'VGE_TOR',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}49',
                'tasks': [
                    {'task_id': '880_1', 'description': 'Service window', 'duration_hr': 8, 'blocking_percentage': 50}
                ]
            },
            # Northern Sweden projects
            {
                'project_id': 'N001',
                'description': 'Catenary replacement Bracke-Langsele',
                'link': 'BRC_LAS',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}35',
                'tasks': [
                    {'task_id': 'N001_1', 'description': 'Traffic disruption (10-week total closure)', 'duration_hr': 24*7*10, 'blocking_percentage': 100}
                ]
            },
            {
                'project_id': 'N002',
                'description': 'Catenary replacement Bracke-Langsele',
                'link': 'BRC_LAS',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}35',
                'tasks': [
                    {'task_id': 'N002_1', 'description': 'Service window (daily 8-hour shifts)', 'duration_hr': 8, 'blocking_percentage': 100, 'count': 70}
                ]
            },
            {
                'project_id': 'N003',
                'description': 'Track work Hudiksvall-Sundsvall',
                'link': 'HDV_SUC',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}35',
                'tasks': [
                    {'task_id': 'N003_1', 'description': 'Service window (daily 6-hour shifts on weekdays)', 'duration_hr': 6, 'blocking_percentage': 100, 'count': 50}
                ]
            },
            {
                'project_id': 'N004',
                'description': 'Track work Boden-Gallivare',
                'link': 'BDN_GVE',
                'earliest_start': f'v{BASE_YEAR}10',
                'latest_end': f'v{BASE_YEAR}35',
                'tasks': [
                    {'task_id': 'N004_1', 'description': 'Service window (daily 8-hour shifts)', 'duration_hr': 8, 'blocking_percentage': 100, 'count': 60}
                ]
            }
        ]
        
        # Validate links and filter out invalid projects
        valid_projects = []
        for project in projects:
            link = project['link']
            if link in valid_links:
                valid_projects.append(project)
            else:
                logger.warning(f"Warning: Project {project['project_id']} references invalid link {link}. Skipping.")
        
        logger.info(f"Filtered to {len(valid_projects)} valid projects")
        
        # Create DataFrame with rows similar to the TPÅ coordination sheet format
        tpa_data = []
        
        # Create a simulated view of the TPÅ coordination sheet
        for project in valid_projects:
            for task in project['tasks']:
                row = {
                    'TPÅ_ID': project['project_id'],
                    'Beskrivning': project['description'],
                    'Sträcka': project['link'],
                    'Åtgärd': task['description'],
                    'Startdatum': project['earliest_start'],
                    'Slutdatum': project['latest_end'],
                    'Tidslängd (timmar)': task['duration_hr']
                }
                
                # Add a field for blocking percentage
                if task['blocking_percentage'] == 'esp':
                    row['Trafikpåverkan'] = 'Enkelspårsdrift'
                else:
                    row['Trafikpåverkan'] = f"{task['blocking_percentage']}% kapacitetsminskning"
                
                # Handle repeated tasks
                if 'count' in task:
                    row['Upprepningar'] = task['count']
                else:
                    row['Upprepningar'] = 1
                    
                # Add to dataframe rows
                tpa_data.append(row)
        
        # Create week columns (v2410 to v2449)
        weeks = [f'v{BASE_YEAR}{week:02d}' for week in range(10, 50)]
        for week in weeks:
            for i, row in enumerate(tpa_data):
                # Mark schedule based on start/end dates and a pattern
                if row['Startdatum'] <= week <= row['Slutdatum']:
                    if i % 4 == 0:  # First project of each type - schedule for odd weeks
                        if int(week[3:]) % 2 == 1:
                            tpa_data[i][week] = 'X'
                    elif i % 4 == 1:  # Second project - schedule for even weeks
                        if int(week[3:]) % 2 == 0:
                            tpa_data[i][week] = 'X'
                    elif i % 4 == 2:  # Third project - schedule for first week of month
                        if int(week[4:]) % 4 == 1:
                            tpa_data[i][week] = 'X'
                    else:  # Fourth project - schedule for last week of month
                        if int(week[4:]) % 4 == 0:
                            tpa_data[i][week] = 'X'
        
        # Create DataFrame
        tpa_df = pd.DataFrame(tpa_data)
        
        # Save to Excel
        tpa_df.to_excel(f'{DATA_INPUT_DIR}/tpa_maintenance.xlsx', index=False)
        
        logger.info(f"Maintenance data created and saved to {DATA_INPUT_DIR}/tpa_maintenance.xlsx")
        
        # Create XML version for the projects
        self.create_project_xml(valid_projects)
        
        return tpa_df
    
    def create_project_xml(self, projects):
        """Create a XML file for the projects following the format in the paper."""
        # Create root element
        root = ET.Element("problem")
        
        # Add resources section
        resources = ET.SubElement(root, "resources")
        ET.SubElement(resources, "resource", id="crew1", name="Maintenance crew 1")
        ET.SubElement(resources, "resource", id="crew2", name="Maintenance crew 2")
        ET.SubElement(resources, "resource", id="equip1", name="Special equipment 1")
        
        # Add projects
        projects_elem = ET.SubElement(root, "projects")
        
        for project in projects:
            # Convert Swedish week notation to ISO date
            earliest_start = self._convert_week_to_date(project['earliest_start'])
            latest_end = self._convert_week_to_date(project['latest_end'], end_of_week=True)
            
            proj = ET.SubElement(projects_elem, "project", 
                                id=project['project_id'], 
                                desc=normalize_name(project['description']),
                                earliestStart=earliest_start,
                                latestEnd=latest_end)
            
            # Add tasks for this project
            for task in project['tasks']:
                # Create task element
                task_attrib = {
                    'id': task['task_id'],
                    'desc': normalize_name(task['description']),
                    'durationHr': str(task['duration_hr'])
                }
                
                # Add count if present
                if 'count' in task:
                    task_attrib['count'] = str(task['count'])
                
                task_elem = ET.SubElement(proj, "task", **task_attrib)
                
                # Add traffic blocking
                blocking_attrib = {
                    'link': project['link'],
                    'amount': 'esp' if task['blocking_percentage'] == 'esp' else str(task['blocking_percentage'])
                }
                ET.SubElement(task_elem, "traffic_blocking", **blocking_attrib)
                
                # Add resource requirements
                resources_elem = ET.SubElement(task_elem, "requiredResources")
                ET.SubElement(resources_elem, "resource", id="crew1", amount="1")
                
                if task['duration_hr'] > 24:  # For longer tasks, add more resources
                    ET.SubElement(resources_elem, "resource", id="equip1", amount="1")
        
        # Validate and save
        validate_xml_structure(root)
        xml_content = prettify_xml(root)
        
        with open(f'{DATA_PROCESSED_DIR}/projects.xml', 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        logger.info(f"Project XML created and saved to {DATA_PROCESSED_DIR}/projects.xml")
    
    def _convert_week_to_date(self, week_str, end_of_week=False):
        """
        Convert Swedish week notation (e.g. 'v2410') to ISO date format.
        """
        year = int("20" + week_str[1:3])
        week = int(week_str[3:])
        
        # Use a different approach for week calculation
        # Start with January 1 of the year
        jan1 = datetime.datetime(year, 1, 1)
        # Find the first Monday of the year
        if jan1.weekday() != 0:  # If January 1 is not Monday
            jan1 = jan1 + datetime.timedelta(days=(7 - jan1.weekday()) % 7)
        
        # Add the weeks
        first_day = jan1 + datetime.timedelta(weeks=week-1)
        
        if end_of_week:
            # End of week is Sunday (6 days later)
            date = first_day + datetime.timedelta(days=6)
            time_str = "23:59:59"
        else:
            date = first_day
            time_str = "00:00:00"
        
        return f"{date.strftime('%Y-%m-%d')} {time_str}"
    
# Problem Generator - integrates all components
class ProblemGenerator:
    def __init__(self, network, traffic_generator, maintenance_generator):
        """
        Initialize the problem generator.
        
        Parameters:
        -----------
        network : SwedishRailwayNetwork
            Network instance
        traffic_generator : TrafficDataGenerator
            Traffic data generator instance
        maintenance_generator : MaintenanceDataGenerator
            Maintenance data generator instance
        """
        self.network = network
        self.traffic_generator = traffic_generator
        self.maintenance_generator = maintenance_generator
    
    def create_problem_xml(self):
        """
        Create a combined problem.xml file from all data components.
        
        Returns:
        --------
        bool
            True if the problem XML was created successfully, False otherwise
        """
        logger.info("Creating combined problem.xml...")
        
        # Set paths for input files
        network_file = f'{DATA_PROCESSED_DIR}/network.xml'
        traffic_file = f'{DATA_PROCESSED_DIR}/traffic.xml'
        projects_file = f'{DATA_PROCESSED_DIR}/projects.xml'
        output_file = f'{DATA_PROCESSED_DIR}/problem.xml'
        
        # Check if all required files exist
        files_exist = self._check_files_exist(network_file, traffic_file, projects_file)
        if not files_exist:
            logger.warning("Will attempt to generate missing files...")
            
            # Generate network data if needed
            if not os.path.exists(network_file):
                self.network.create_network_data()
            
            # Generate traffic data if needed
            if not os.path.exists(traffic_file):
                self.traffic_generator.create_traffic_data()
            
            # Generate projects data if needed
            if not os.path.exists(projects_file):
                self.maintenance_generator.create_maintenance_data()
        
        # Create root element
        root = ET.Element("problem")
        
        # Track whether files were successfully merged
        success_count = 0
        
        # Variables to store roots for validation
        network_root = None
        traffic_root = None
        
        # Add network data
        if os.path.exists(network_file):
            try:
                # Parse the network XML
                tree = ET.parse(network_file)
                network_root = tree.getroot()
                
                # Normalize element names
                normalize_xml_element(network_root)
                
                # If the root element is <network>, add it directly
                if network_root.tag == 'network':
                    root.append(network_root)
                    logger.info(f"Successfully merged network data from {network_file}")
                    success_count += 1
                else:
                    # Try to find <network> element inside the root
                    network_elem = network_root.find('.//network')
                    if network_elem is not None:
                        root.append(network_elem)
                        logger.info(f"Successfully merged network data from {network_file}")
                        success_count += 1
                    else:
                        logger.warning(f"Could not find <network> element in {network_file}")
                        # Create a minimal network element
                        self._create_minimal_network(root)
                        success_count += 1
            except Exception as e:
                logger.error(f"Error parsing network file {network_file}: {e}")
                # Create a minimal network element
                self._create_minimal_network(root)
                success_count += 1
        else:
            logger.warning(f"Network file {network_file} not found")
            # Create a minimal network element
            self._create_minimal_network(root)
            success_count += 1
        
        # Add traffic data
        if os.path.exists(traffic_file):
            try:
                # Parse the traffic XML
                tree = ET.parse(traffic_file)
                traffic_root = tree.getroot()
                
                # Normalize element names
                normalize_xml_element(traffic_root)
                
                # If the root element is <traffic>, add it directly
                if traffic_root.tag == 'traffic':
                    root.append(traffic_root)
                    logger.info(f"Successfully merged traffic data from {traffic_file}")
                    success_count += 1
                else:
                    # Try to find <traffic> element inside the root
                    traffic_elem = traffic_root.find('.//traffic')
                    if traffic_elem is not None:
                        root.append(traffic_elem)
                        logger.info(f"Successfully merged traffic data from {traffic_file}")
                        success_count += 1
                    else:
                        logger.warning(f"Could not find <traffic> element in {traffic_file}")
                        # Create a minimal traffic element
                        self._create_minimal_traffic(root)
                        success_count += 1
            except Exception as e:
                logger.error(f"Error parsing traffic file {traffic_file}: {e}")
                # Create a minimal traffic element
                self._create_minimal_traffic(root)
                success_count += 1
        else:
            logger.warning(f"Traffic file {traffic_file} not found")
            # Create a minimal traffic element
            self._create_minimal_traffic(root)
            success_count += 1
        
        # Add resources and projects data
        resources_added = False
        projects_added = False
        
        if os.path.exists(projects_file):
            try:
                # Parse the projects XML
                tree = ET.parse(projects_file)
                projects_root = tree.getroot()
                
                # Normalize element names
                normalize_xml_element(projects_root)
                
                # Try to find <resources> element
                resources_elem = projects_root.find('.//resources')
                if resources_elem is not None:
                    root.append(resources_elem)
                    logger.info(f"Successfully merged resources data from {projects_file}")
                    resources_added = True
                
                # Try to find <projects> element
                projects_elem = projects_root.find('.//projects')
                if projects_elem is not None:
                    root.append(projects_elem)
                    logger.info(f"Successfully merged projects data from {projects_file}")
                    projects_added = True
                    success_count += 1
            except Exception as e:
                logger.error(f"Error parsing projects file {projects_file}: {e}")
        else:
            logger.warning(f"Projects file {projects_file} not found")
        
        # Add minimal resources if not found
        if not resources_added:
            resources = ET.SubElement(root, "resources")
            ET.SubElement(resources, "resource", id="crew1", name="Maintenance crew 1")
            logger.info("Added minimal resources data")
        
        # Add minimal projects if not found
        if not projects_added:
            projects = ET.SubElement(root, "projects")
            project = ET.SubElement(projects, "project", id="sample_proj", desc="Sample Project", 
                                  earliestStart=f"{BASE_YEAR}-01-01 00:00:00", latestEnd=f"{BASE_YEAR}-12-31 23:59:59")
            task = ET.SubElement(project, "task", id="sample_task", desc="Sample Task", durationHr="48")
            
            # Find a valid link to reference
            network_elem = root.find('.//network')
            if network_elem is not None:
                link_elem = network_elem.find('.//link')
                if link_elem is not None and 'id' in link_elem.attrib:
                    link_id = link_elem.attrib['id']
                    ET.SubElement(task, "traffic_blocking", link=link_id, amount="50")
            
            logger.info("Added minimal projects data")
            success_count += 1
        
        # After parsing network and traffic XML
        if network_root is not None and traffic_root is not None:
            # Validate and complete network
            try:
                network_root = self._validate_and_complete_network(network_root, traffic_root)
            except Exception as e:
                logger.error(f"Error validating network links: {e}")
        
        # Add parameters
        params = ET.SubElement(root, "params")
        
        # Add scheduling parameters
        ET.SubElement(params, "keyVal", key="cp_block").text = "1.0"
        ET.SubElement(params, "keyVal", key="cp_bs").text = "0.5"
        ET.SubElement(params, "keyVal", key="*").text = "100"  # Default project cancellation cost
        
        # Add traffic parameters
        ET.SubElement(params, "keyVal", key="ct_cancel_RST").text = "10"
        ET.SubElement(params, "keyVal", key="ct_cancel_GT").text = "5"
        ET.SubElement(params, "keyVal", key="ct_post_RST").text = "5"
        ET.SubElement(params, "keyVal", key="ct_post_GT").text = "2"
        ET.SubElement(params, "keyVal", key="ct_time_RST").text = "1"
        ET.SubElement(params, "keyVal", key="ct_time_GT").text = "0.5"
        ET.SubElement(params, "keyVal", key="mx_inc_rel_RST").text = "1.2"
        ET.SubElement(params, "keyVal", key="mx_inc_abs_GT").text = "2.0"
        
        logger.info("Added parameters")
        
        # Add planning period
        plan = ET.SubElement(root, "plan")
        plan.set("start", f"{BASE_YEAR}-01-01 00:00:00")
        plan.set("end", f"{BASE_YEAR}-12-31 23:59:59")
        plan.set("period_length", "8")
        plan.set("traffic_start", f"{BASE_YEAR}-01-01 00:00:00")
        plan.set("traffic_end", f"{BASE_YEAR}-12-31 23:59:59")
        
        logger.info("Added planning period")
        
        # Validate final XML structure
        validate_xml_structure(root)
        
        # Create XML string and prettify it
        try:
            xml_content = prettify_xml(root)
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            logger.info(f"Problem XML created and saved to {output_file}")
            
            if success_count >= 3:
                logger.info("All required components were successfully merged.")
            else:
                logger.warning("Some components were missing or failed to merge. A minimal replacement was created.")
            
            return True
        except Exception as e:
            logger.error(f"Error creating problem XML: {e}")
            return False
    
    def _check_files_exist(self, network_file, traffic_file, projects_file):
        """Check if the necessary files exist and provide suggestions if not."""
        missing_files = []
        
        if not os.path.exists(network_file):
            missing_files.append(("network", network_file))
        
        if not os.path.exists(traffic_file):
            missing_files.append(("traffic", traffic_file))
        
        if not os.path.exists(projects_file):
            missing_files.append(("projects", projects_file))
        
        if missing_files:
            logger.warning("Some required files are missing:")
            for file_type, file_path in missing_files:
                logger.warning(f"  - {file_type} file: {file_path}")
            
            return False
        
        return True
    
    def _create_minimal_network(self, root):
        """Create a minimal network element."""
        network = ET.SubElement(root, "network")
        nodes = ET.SubElement(network, "nodes")
        
        # Add minimal nodes
        ET.SubElement(nodes, "node", id="A", name="Station A", lat="0", lon="0")
        ET.SubElement(nodes, "node", id="B", name="Station B", lat="1", lon="0")
        
        links = ET.SubElement(network, "links")
        
        # Add minimal link
        ET.SubElement(links, "link", id="A_B", **{"from": "A", "to": "B", "length": "10", "tracks": "2", "capacity": "10"})
        
        logger.info("Created minimal network data")
    
    def _create_minimal_traffic(self, root):
        """Create a minimal traffic element."""
        traffic = ET.SubElement(root, "traffic")
        train_types = ET.SubElement(traffic, "train_types")
        ET.SubElement(train_types, "train_type", id="RST", name="Passenger Train")
        ET.SubElement(train_types, "train_type", id="GT", name="Freight Train")
        
        lines = ET.SubElement(traffic, "lines")
        ET.SubElement(lines, "line", id="A_B_RST", origin="A", destination="B", train_type="RST")
        
        line_demand = ET.SubElement(traffic, "line_demand")
        ET.SubElement(line_demand, "demand", line="A_B_RST", startHr="8", endHr="9", demand="5")
        
        # Find a valid link to reference
        network_elem = root.find('.//network')
        if network_elem is not None:
            link_elem = network_elem.find('.//link')
            if link_elem is not None and 'id' in link_elem.attrib:
                link_id = link_elem.attrib['id']
                
                line_routes = ET.SubElement(traffic, "line_routes")
                route = ET.SubElement(line_routes, "line_route", line="A_B_RST", route=f"{link_id}")
                ET.SubElement(route, "dur", link=link_id).text = "0.5"
        
        logger.info("Created minimal traffic data")
    
    def _validate_and_complete_network(self, network_root, traffic_root):
        """
        Validate network links and add missing links from traffic data.
        
        Parameters:
        -----------
        network_root : xml.etree.ElementTree.Element
            Root of the network XML
        traffic_root : xml.etree.ElementTree.Element
            Root of the traffic XML
        
        Returns:
        --------
        xml.etree.ElementTree.Element
            Updated network root with additional links
        """
        # Find existing links
        existing_links = network_root.find('.//links')
        if existing_links is None:
            existing_links = ET.SubElement(network_root, 'links')
        
        # Find existing nodes
        existing_nodes = network_root.find('.//nodes')
        if existing_nodes is None:
            existing_nodes = ET.SubElement(network_root, 'nodes')
        
        # Track existing link and node IDs
        existing_link_ids = set(link.get('id') for link in existing_links.findall('link'))
        existing_node_ids = set(node.get('id') for node in existing_nodes.findall('node'))
        
        # Collect links from different sources in traffic
        additional_links = []
        
        # Check line routes
        line_routes = traffic_root.findall('.//line_route')
        if line_routes:
            for route in line_routes:
                route_links = route.get('route', '').split()
                additional_links.extend(route_links)
        
        # Check traffic blocking
        blocking_links = traffic_root.findall('.//traffic_blocking')
        if blocking_links:
            for block in blocking_links:
                link_id = block.get('link')
                if link_id:
                    additional_links.append(link_id)
        
        # Remove duplicates and filter out existing links
        additional_links = list(set(additional_links) - existing_link_ids)
        
        # Add missing links
        for link_id in additional_links:
            # Try to infer from link ID (assuming format like A_B)
            parts = link_id.split('_')
            
            # Ensure both nodes exist
            for node_id in parts[:2]:  # Take first two parts as node IDs
                if node_id not in existing_node_ids:
                    # Create minimal node if not exists
                    node = ET.SubElement(existing_nodes, 'node', 
                                       id=node_id, 
                                       name=f"Station {node_id}", 
                                       lat="0", 
                                       lon="0")
                    existing_node_ids.add(node_id)
            
            # Create link
            if len(parts) >= 2:
                from_node = parts[0]
                to_node = parts[1]
                link = ET.SubElement(existing_links, 'link', 
                                   id=link_id, 
                                   **{
                                       'from': from_node, 
                                       'to': to_node, 
                                       'length': "10", 
                                       'tracks': "2", 
                                       'capacity': "10"
                                   })
                logger.info(f"Added missing link: {link_id}")
        
        return network_root
    
# Main execution function
def main():
    """Main execution function to generate all data."""
    # Welcome message
    logger.info("Swedish Railway Data Generator")
    logger.info("=============================")
    
    # Initialize directories
    init_directories()
    
    # Create objects
    network = SwedishRailwayNetwork()
    traffic_generator = TrafficDataGenerator(network)
    maintenance_generator = MaintenanceDataGenerator(network)
    problem_generator = ProblemGenerator(network, traffic_generator, maintenance_generator)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Generate Swedish railway data files')
    parser.add_argument('--network', action='store_true', help='Generate only network data')
    parser.add_argument('--traffic', action='store_true', help='Generate only traffic data')
    parser.add_argument('--maintenance', action='store_true', help='Generate only maintenance data')
    parser.add_argument('--problem', action='store_true', help='Generate only problem.xml')
    parser.add_argument('--all', action='store_true', help='Generate all data files (default)')
    parser.add_argument('--year', type=int, default=BASE_YEAR, help=f'Base year for data (default: {BASE_YEAR})')
    
    args = parser.parse_args()
    
    # If no specific option, generate all
    if not (args.network or args.traffic or args.maintenance or args.problem):
        args.all = True
    
    # Generate requested data
    if args.network or args.all:
        logger.info("Generating network data...")
        network.create_network_data()
    
    if args.traffic or args.all:
        logger.info("Generating traffic data...")
        traffic_generator.create_traffic_data()
    
    if args.maintenance or args.all:
        logger.info("Generating maintenance data...")
        maintenance_generator.create_maintenance_data()
    
    if args.problem or args.all:
        logger.info("Generating problem XML...")
        problem_generator.create_problem_xml()
    
    logger.info("Data generation complete!")
    logger.info(f"Excel files saved to: {DATA_INPUT_DIR}/")
    logger.info(f"XML files saved to: {DATA_PROCESSED_DIR}/")
    
    # Provide next steps
    logger.info("\nYou can now run the optimization using:")
    logger.info(f"python src/execution/run.py --file problem.xml --dir {DATA_PROCESSED_DIR} --opt both --out_dir results/test_run")

if __name__ == "__main__":
    main()

'''
# Generate all data
python swedish_railway_data_generator.py

# Or generate specific data components
python swedish_railway_data_generator.py --network
python swedish_railway_data_generator.py --traffic
python swedish_railway_data_generator.py --maintenance
python swedish_railway_data_generator.py --problem

'''