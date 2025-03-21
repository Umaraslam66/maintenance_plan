# network_data.py
import pandas as pd
import numpy as np
import os
import xml.etree.ElementTree as ET
import openpyxl

# Global variables to store the network data
_stations_data = None
_links_data = None

def get_network_data():
    """
    Get network data - either load existing data or create new data if none exists.
    
    Returns:
    --------
    tuple: (stations_df, links_df) - DataFrames containing stations and links data
    """
    global _stations_data, _links_data
    
    # If we already have the data in memory, return it
    if _stations_data is not None and _links_data is not None:
        return _stations_data, _links_data
    
    # Check if the data files exist and load them
    if os.path.exists('data/input/stations.xlsx') and os.path.exists('data/input/links.xlsx'):
        try:
            stations_df = pd.read_excel('data/input/stations.xlsx')
            links_df = pd.read_excel('data/input/links.xlsx')
            print("Loaded existing network data from files")
            _stations_data, _links_data = stations_df, links_df
            return stations_df, links_df
        except Exception as e:
            print(f"Error loading existing network data: {e}")
            print("Will create new network data")
    
    # Create new data
    return create_network_data()

def is_valid_link(link_id):
    """
    Check if a link ID exists in the network data.
    
    Parameters:
    -----------
    link_id: str
        Link ID to check
    
    Returns:
    --------
    bool: True if the link exists, False otherwise
    """
    # Ensure data is loaded
    _, links_df = get_network_data()
    return link_id in links_df['link_id'].values

def is_valid_node(node_id):
    """
    Check if a node ID exists in the network data.
    
    Parameters:
    -----------
    node_id: str
        Node ID to check
    
    Returns:
    --------
    bool: True if the node exists, False otherwise
    """
    # Ensure data is loaded
    stations_df, _ = get_network_data()
    return node_id in stations_df['node_id'].values

def get_all_nodes():
    """
    Get all node IDs in the network.
    
    Returns:
    --------
    list: List of all node IDs
    """
    stations_df, _ = get_network_data()
    return stations_df['node_id'].tolist()

def get_all_links():
    """
    Get all link IDs in the network.
    
    Returns:
    --------
    list: List of all link IDs
    """
    _, links_df = get_network_data()
    return links_df['link_id'].tolist()

def create_network_data():
    """Create network data for Swedish railway infrastructure"""
    global _stations_data, _links_data
    
    print("Creating network data for Swedish railway infrastructure...")
    
    # Define major Swedish railway stations
    stations = [
        {'node_id': 'G', 'station_name': 'Gothenburg', 'lat': 57.7089, 'lon': 11.9746, 'merge_group': 'G'},
        {'node_id': 'A', 'station_name': 'Alingsås', 'lat': 57.9295, 'lon': 12.5337, 'merge_group': None},
        {'node_id': 'SK', 'station_name': 'Skövde', 'lat': 58.3890, 'lon': 13.8456, 'merge_group': None},
        {'node_id': 'HB', 'station_name': 'Hallsberg', 'lat': 59.0664, 'lon': 15.1098, 'merge_group': 'HB'},
        {'node_id': 'NR', 'station_name': 'Norrköping', 'lat': 58.5977, 'lon': 16.1826, 'merge_group': None},
        {'node_id': 'LI', 'station_name': 'Linköping', 'lat': 58.4108, 'lon': 15.6213, 'merge_group': None},
        {'node_id': 'S', 'station_name': 'Stockholm', 'lat': 59.3293, 'lon': 18.0686, 'merge_group': 'S'},
        {'node_id': 'NK', 'station_name': 'Nässjö', 'lat': 57.6526, 'lon': 14.6946, 'merge_group': None},
        {'node_id': 'AV', 'station_name': 'Alvesta', 'lat': 56.8990, 'lon': 14.5560, 'merge_group': None},
        {'node_id': 'HM', 'station_name': 'Hässleholm', 'lat': 56.1589, 'lon': 13.7668, 'merge_group': None},
        {'node_id': 'LU', 'station_name': 'Lund', 'lat': 55.7047, 'lon': 13.1910, 'merge_group': 'LU'},
        {'node_id': 'M', 'station_name': 'Malmö', 'lat': 55.6050, 'lon': 13.0038, 'merge_group': 'M'},
        {'node_id': 'VB', 'station_name': 'Varberg', 'lat': 57.1055, 'lon': 12.2502, 'merge_group': None},
        {'node_id': 'KB', 'station_name': 'Kungsbacka', 'lat': 57.4874, 'lon': 12.0798, 'merge_group': None},
        {'node_id': 'BS', 'station_name': 'Borås', 'lat': 57.7210, 'lon': 12.9401, 'merge_group': None},
        {'node_id': 'ÄN', 'station_name': 'Älvängen', 'lat': 58.0116, 'lon': 12.1147, 'merge_group': None},
        {'node_id': 'E', 'station_name': 'Eslöv', 'lat': 55.8391, 'lon': 13.3035, 'merge_group': None},
        {'node_id': 'HÖ', 'station_name': 'Höör', 'lat': 55.9374, 'lon': 13.5426, 'merge_group': None},
        {'node_id': 'GDÖ', 'station_name': 'Degerfors', 'lat': 59.2335, 'lon': 14.4280, 'merge_group': None},
        {'node_id': 'T', 'station_name': 'Töreboda', 'lat': 58.7062, 'lon': 14.1229, 'merge_group': None},
        # Northern Sweden stations (important for the Norrland case study)
        {'node_id': 'HD', 'station_name': 'Hudiksvall', 'lat': 61.7279, 'lon': 17.1044, 'merge_group': None},
        {'node_id': 'SU', 'station_name': 'Sundsvall', 'lat': 62.3908, 'lon': 17.3069, 'merge_group': None},
        {'node_id': 'BÄ', 'station_name': 'Bräcke', 'lat': 62.7508, 'lon': 15.4195, 'merge_group': None},
        {'node_id': 'LSL', 'station_name': 'Långsele', 'lat': 63.1745, 'lon': 17.1063, 'merge_group': None},
        {'node_id': 'UÅ', 'station_name': 'Umeå', 'lat': 63.8284, 'lon': 20.2597, 'merge_group': None},
        {'node_id': 'VN', 'station_name': 'Vännäs', 'lat': 63.9062, 'lon': 19.7503, 'merge_group': None},
        {'node_id': 'BD', 'station_name': 'Boden', 'lat': 65.8256, 'lon': 21.6906, 'merge_group': None},
        {'node_id': 'LY', 'station_name': 'Luleå', 'lat': 65.5842, 'lon': 22.1547, 'merge_group': None},
        {'node_id': 'GV', 'station_name': 'Gällivare', 'lat': 67.1367, 'lon': 20.6599, 'merge_group': None},
        {'node_id': 'KA', 'station_name': 'Kiruna', 'lat': 67.8558, 'lon': 20.2253, 'merge_group': None},
        # Additional important stations
        {'node_id': 'K', 'station_name': 'Karlstad', 'lat': 59.3793, 'lon': 13.5036, 'merge_group': None},
        {'node_id': 'KIL', 'station_name': 'Kil', 'lat': 59.5038, 'lon': 13.3196, 'merge_group': None},
        {'node_id': 'TEO', 'station_name': 'Teckomatorp', 'lat': 55.8704, 'lon': 13.0784, 'merge_group': None},
        {'node_id': 'VRÖ', 'station_name': 'Veinge', 'lat': 56.4833, 'lon': 13.0333, 'merge_group': None},
        {'node_id': 'HPBG', 'station_name': 'Helsingborg', 'lat': 56.0465, 'lon': 12.6945, 'merge_group': None},
        {'node_id': 'D', 'station_name': 'Ängelholm', 'lat': 56.2428, 'lon': 12.8605, 'merge_group': None}
    ]
    
    # Define links between stations (railway segments)
    links = [
        # Western Main Line
        {'link_id': 'G_A', 'from_node': 'G', 'to_node': 'A', 'length_km': 46, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'A_SK', 'from_node': 'A', 'to_node': 'SK', 'length_km': 81, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'SK_HB', 'from_node': 'SK', 'to_node': 'HB', 'length_km': 73, 'num_tracks': 2, 'default_capacity': 10},
        
        # Southern Main Line
        {'link_id': 'HB_NK', 'from_node': 'HB', 'to_node': 'NK', 'length_km': 172, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'NK_AV', 'from_node': 'NK', 'to_node': 'AV', 'length_km': 77, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'AV_HM', 'from_node': 'AV', 'to_node': 'HM', 'length_km': 82, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HM_HÖ', 'from_node': 'HM', 'to_node': 'HÖ', 'length_km': 32, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HÖ_E', 'from_node': 'HÖ', 'to_node': 'E', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'E_LU', 'from_node': 'E', 'to_node': 'LU', 'length_km': 24, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'LU_M', 'from_node': 'LU', 'to_node': 'M', 'length_km': 20, 'num_tracks': 2, 'default_capacity': 10},
        
        # West Coast Line
        {'link_id': 'G_ÄN', 'from_node': 'G', 'to_node': 'ÄN', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'G_KB', 'from_node': 'G', 'to_node': 'KB', 'length_km': 28, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'KB_VB', 'from_node': 'KB', 'to_node': 'VB', 'length_km': 47, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'VB_VRÖ', 'from_node': 'VB', 'to_node': 'VRÖ', 'length_km': 70, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'VRÖ_HPBG', 'from_node': 'VRÖ', 'to_node': 'HPBG', 'length_km': 40, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HPBG_D', 'from_node': 'HPBG', 'to_node': 'D', 'length_km': 35, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'D_HM', 'from_node': 'D', 'to_node': 'HM', 'length_km': 60, 'num_tracks': 2, 'default_capacity': 10},
        
        # Additional connections
        {'link_id': 'VRÖ_TEO', 'from_node': 'VRÖ', 'to_node': 'TEO', 'length_km': 60, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'TEO_HD', 'from_node': 'TEO', 'to_node': 'HD', 'length_km': 40, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'G_BS', 'from_node': 'G', 'to_node': 'BS', 'length_km': 64, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BS_NK', 'from_node': 'BS', 'to_node': 'NK', 'length_km': 132, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'GDÖ_SK', 'from_node': 'GDÖ', 'to_node': 'SK', 'length_km': 85, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'HB_GDÖ', 'from_node': 'HB', 'to_node': 'GDÖ', 'length_km': 45, 'num_tracks': 1, 'default_capacity': 5},
        
        # Northern Sweden links
        {'link_id': 'HD_SU', 'from_node': 'HD', 'to_node': 'SU', 'length_km': 86, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'SU_BÄ', 'from_node': 'SU', 'to_node': 'BÄ', 'length_km': 100, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BÄ_LSL', 'from_node': 'BÄ', 'to_node': 'LSL', 'length_km': 120, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'LSL_VN', 'from_node': 'LSL', 'to_node': 'VN', 'length_km': 153, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'VN_UÅ', 'from_node': 'VN', 'to_node': 'UÅ', 'length_km': 32, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'UÅ_BD', 'from_node': 'UÅ', 'to_node': 'BD', 'length_km': 210, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BD_LY', 'from_node': 'BD', 'to_node': 'LY', 'length_km': 38, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BD_GV', 'from_node': 'BD', 'to_node': 'GV', 'length_km': 180, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'GV_KA', 'from_node': 'GV', 'to_node': 'KA', 'length_km': 120, 'num_tracks': 1, 'default_capacity': 5},
        
        # Add reverse direction links for ease of use
        {'link_id': 'A_G', 'from_node': 'A', 'to_node': 'G', 'length_km': 46, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'SK_A', 'from_node': 'SK', 'to_node': 'A', 'length_km': 81, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HB_SK', 'from_node': 'HB', 'to_node': 'SK', 'length_km': 73, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'NK_HB', 'from_node': 'NK', 'to_node': 'HB', 'length_km': 172, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'AV_NK', 'from_node': 'AV', 'to_node': 'NK', 'length_km': 77, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HM_AV', 'from_node': 'HM', 'to_node': 'AV', 'length_km': 82, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HÖ_HM', 'from_node': 'HÖ', 'to_node': 'HM', 'length_km': 32, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'E_HÖ', 'from_node': 'E', 'to_node': 'HÖ', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'LU_E', 'from_node': 'LU', 'to_node': 'E', 'length_km': 24, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'M_LU', 'from_node': 'M', 'to_node': 'LU', 'length_km': 20, 'num_tracks': 2, 'default_capacity': 10}
    ]
    
    # Add additional links for missing nodes in relationships
    # Make sure S has connections to LI and NR
    links.extend([
        {'link_id': 'S_LI', 'from_node': 'S', 'to_node': 'LI', 'length_km': 200, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'LI_S', 'from_node': 'LI', 'to_node': 'S', 'length_km': 200, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'LI_NR', 'from_node': 'LI', 'to_node': 'NR', 'length_km': 50, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'NR_LI', 'from_node': 'NR', 'to_node': 'LI', 'length_km': 50, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'NR_HB', 'from_node': 'NR', 'to_node': 'HB', 'length_km': 100, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HB_NR', 'from_node': 'HB', 'to_node': 'NR', 'length_km': 100, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'SU_HM', 'from_node': 'SU', 'to_node': 'HM', 'length_km': 180, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'HM_SU', 'from_node': 'HM', 'to_node': 'SU', 'length_km': 180, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BÄ_SU', 'from_node': 'BÄ', 'to_node': 'SU', 'length_km': 100, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'GV_BD', 'from_node': 'GV', 'to_node': 'BD', 'length_km': 180, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'KA_GV', 'from_node': 'KA', 'to_node': 'GV', 'length_km': 120, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'UÅ_VN', 'from_node': 'UÅ', 'to_node': 'VN', 'length_km': 32, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'VN_LSL', 'from_node': 'VN', 'to_node': 'LSL', 'length_km': 153, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'LSL_BÄ', 'from_node': 'LSL', 'to_node': 'BÄ', 'length_km': 120, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BD_UÅ', 'from_node': 'BD', 'to_node': 'UÅ', 'length_km': 210, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'LY_BD', 'from_node': 'LY', 'to_node': 'BD', 'length_km': 38, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'HM_D', 'from_node': 'HM', 'to_node': 'D', 'length_km': 60, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'D_HPBG', 'from_node': 'D', 'to_node': 'HPBG', 'length_km': 35, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'HPBG_VRÖ', 'from_node': 'HPBG', 'to_node': 'VRÖ', 'length_km': 40, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'VRÖ_VB', 'from_node': 'VRÖ', 'to_node': 'VB', 'length_km': 70, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'VB_KB', 'from_node': 'VB', 'to_node': 'KB', 'length_km': 47, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'KB_G', 'from_node': 'KB', 'to_node': 'G', 'length_km': 28, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'ÄN_G', 'from_node': 'ÄN', 'to_node': 'G', 'length_km': 30, 'num_tracks': 2, 'default_capacity': 10},
        {'link_id': 'TEO_VRÖ', 'from_node': 'TEO', 'to_node': 'VRÖ', 'length_km': 60, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'HD_TEO', 'from_node': 'HD', 'to_node': 'TEO', 'length_km': 40, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'BS_G', 'from_node': 'BS', 'to_node': 'G', 'length_km': 64, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'NK_BS', 'from_node': 'NK', 'to_node': 'BS', 'length_km': 132, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'SK_GDÖ', 'from_node': 'SK', 'to_node': 'GDÖ', 'length_km': 85, 'num_tracks': 1, 'default_capacity': 5},
        {'link_id': 'GDÖ_HB', 'from_node': 'GDÖ', 'to_node': 'HB', 'length_km': 45, 'num_tracks': 1, 'default_capacity': 5},
    ])
    
    # Create DataFrames
    stations_df = pd.DataFrame(stations)
    links_df = pd.DataFrame(links)
    
    # Create output directory if it doesn't exist
    os.makedirs('data/input', exist_ok=True)
    os.makedirs('data/processed', exist_ok=True)
    
    # Save to Excel files
    stations_df.to_excel('data/input/stations.xlsx', index=False)
    links_df.to_excel('data/input/links.xlsx', index=False)
    
    print(f"Network data created and saved to data/input/stations.xlsx and data/input/links.xlsx")
    
    # Store in global variables
    _stations_data = stations_df
    _links_data = links_df
    
    # Also create a network XML version based on the format described in the paper
    create_network_xml(stations, links)
    
    return stations_df, links_df

def create_network_xml(stations, links):
    """Create a XML file for the network following the format in the paper"""
    
    # Create XML content
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<network>\n'
    
    # Add nodes
    xml_content += '  <nodes>\n'
    for station in stations:
        xml_content += f'    <node id="{station["node_id"]}" name="{station["station_name"]}" lat="{station["lat"]}" lon="{station["lon"]}"'
        if station["merge_group"]:
            xml_content += f' merge_group="{station["merge_group"]}"'
        xml_content += '/>\n'
    xml_content += '  </nodes>\n'
    
    # Add links
    xml_content += '  <links>\n'
    for link in links:
        xml_content += f'    <link id="{link["link_id"]}" from="{link["from_node"]}" to="{link["to_node"]}" length="{link["length_km"]}" tracks="{link["num_tracks"]}" capacity="{link["default_capacity"]}"/>\n'
    xml_content += '  </links>\n'
    
    xml_content += '</network>'
    
    # Save XML file
    with open('data/processed/network.xml', 'w') as f:
        f.write(xml_content)
    
    print(f"Network XML created and saved to data/processed/network.xml")

def validate_route(route_nodes):
    """
    Validate that a sequence of nodes forms a valid route (each node is connected to the next)
    
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
    _, links_df = get_network_data()
    
    missing_links = []
    
    for i in range(len(route_nodes) - 1):
        from_node = route_nodes[i]
        to_node = route_nodes[i + 1]
        
        # Check if a link exists between these nodes
        link_id = f"{from_node}_{to_node}"
        if link_id not in links_df['link_id'].values:
            missing_links.append(link_id)
    
    return len(missing_links) == 0, missing_links

if __name__ == "__main__":
    create_network_data()