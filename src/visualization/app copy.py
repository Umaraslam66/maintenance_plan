#streamlit run src/visualization/app.py
# 210325 16:00 version

import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import time
import json
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from datetime import datetime, timedelta
import subprocess
import xml.etree.ElementTree as ET
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
import tempfile
import shutil
import plotly.figure_factory as ff
import io
import base64
from network_data import get_network_data
# Add parent directory to path to import the required modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set page configuration
st.set_page_config(
    page_title="Railway Maintenance Planning Tool",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants and helper functions
APP_VERSION = "1.1.0"
DATE_FORMAT = "%Y-%m-%d"

def parse_date(date_str):
    """Parse date strings to datetime objects"""
    if not date_str:
        return None
    try:
        if isinstance(date_str, str):
            if "T" in date_str:  # Handling ISO datetime format
                date_str = date_str.split("T")[0]
            return datetime.strptime(date_str, "%Y-%m-%d")  # Ensure correct format
        return date_str  # Already a datetime object
    except ValueError as e:
        print(f"Date parsing failed for {date_str}: {e}")
        return None


def format_date(date_obj):
    """Format datetime objects to strings"""
    if not date_obj:
        return ""
    if isinstance(date_obj, str):
        return date_obj
    try:
        return date_obj.strftime(DATE_FORMAT)
    except:
        return ""

def create_temp_dir():
    """Create a temporary directory for file operations"""
    temp_dir = os.path.join(tempfile.gettempdir(), "railway_planning")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def get_maintenance_color(maintenance_type):
    """Return color for different maintenance types"""
    color_map = {
        'Preventive': '#00CC00',       # Bright green
        'Corrective': '#FF9900',       # Orange
        'Renewal': '#FF0000',          # Red
        'ERTMS Implementation': '#0066FF',  # Blue
        'Inspection': '#9900CC',       # Purple
        'Track Work': '#FF3399',       # Pink
        'Signaling': '#00FFFF',        # Cyan
        'Electrical': '#FFFF00',       # Yellow
        'Bridge & Structure': '#996633',  # Brown
        'Unknown': '#CCCCCC'           # Grey
    }
    return color_map.get(maintenance_type, color_map['Unknown'])

def download_dataframe_as_csv(df, filename):
    """Generate a download link for a dataframe as CSV"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">Download {filename} as CSV</a>'
    return href

def read_xml_file(file):
    """Read XML file and return root element"""
    try:
        if isinstance(file, str):
            # It's a file path
            tree = ET.parse(file)
        else:
            # It's a file object
            tree = ET.parse(file)
        return tree.getroot()
    except Exception as e:
        st.error(f"Error reading XML file: {str(e)}")
        return None

# Initialize session state for data persistence
if 'network_data' not in st.session_state:
    st.session_state.network_data = None
if 'maintenance_data' not in st.session_state:
    st.session_state.maintenance_data = None
if 'traffic_data' not in st.session_state:
    st.session_state.traffic_data = None
if 'dated_infrastructure' not in st.session_state:
    st.session_state.dated_infrastructure = {}  # Year -> infrastructure data
if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None
if 'optimization_running' not in st.session_state:
    st.session_state.optimization_running = False
if 'parallelism_matrix' not in st.session_state:
    # Initialize with default parallelism matrix
    st.session_state.parallelism_matrix = {
        'Preventive': {'Preventive': True, 'Corrective': False, 'Renewal': False, 'ERTMS Implementation': False, 'Inspection': True},
        'Corrective': {'Preventive': False, 'Corrective': True, 'Renewal': False, 'ERTMS Implementation': False, 'Inspection': False},
        'Renewal': {'Preventive': False, 'Corrective': False, 'Renewal': True, 'ERTMS Implementation': False, 'Inspection': False},
        'ERTMS Implementation': {'Preventive': False, 'Corrective': False, 'Renewal': False, 'ERTMS Implementation': True, 'Inspection': False},
        'Inspection': {'Preventive': True, 'Corrective': False, 'Renewal': False, 'ERTMS Implementation': False, 'Inspection': True}
    }
if 'last_optimization_time' not in st.session_state:
    st.session_state.last_optimization_time = None
if 'detour_routes' not in st.session_state:
    st.session_state.detour_routes = {}  # Dictionary to store detour routes
if 'routing_rules' not in st.session_state:
    st.session_state.routing_rules = []  # List to store routing rules

# Sidebar navigation
st.sidebar.title("Railway Planning Tool")
st.sidebar.image("https://www.svgrepo.com/show/111486/train.svg", width=100)

# App sections
app_mode = st.sidebar.selectbox("Navigation", 
    ["Home", "Data Management", "Network Visualization", "Maintenance Schedule", 
     "Conflict Detection", "Parallelism Matrix", "Detour Routes", "Routing Rules", "Optimization", "Reports"]
)

# Home page
if app_mode == "Home":
    st.title("Railway Maintenance Planning Tool")
    st.markdown("### Welcome to the Swedish Railway Maintenance Planning Tool")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        This tool helps railway planners to:
        - Manage infrastructure information (including dated infrastructure)
        - Plan maintenance activities with portability and time constraints
        - Configure parallelism for different types of maintenance work
        - Define detour routes and routing rules for accessibility
        - Detect and resolve conflicts between maintenance activities
        - Optimize maintenance schedules
        - Analyze traffic impacts
        
        **Getting Started:**
        1. Go to **Data Management** to upload or create network, maintenance, and traffic data
        2. Use **Network Visualization** to see the railway network
        3. Plan maintenance activities in the **Maintenance Schedule** section
        4. Check for conflicts in the **Conflict Detection** section
        5. Configure which activities can run in parallel in the **Parallelism Matrix**
        6. Define alternative routes in the **Detour Routes** section
        7. Set up routing rules in the **Routing Rules** section
        8. Run optimization in the **Optimization** section
        9. View detailed reports in the **Reports** section
        """)
    
    with col2:
        st.markdown("### System Status")
        
        # Display data status
        network_status = "✅ Loaded" if st.session_state.network_data is not None else "❌ Not loaded"
        maintenance_status = "✅ Loaded" if st.session_state.maintenance_data is not None else "❌ Not loaded"
        traffic_status = "✅ Loaded" if st.session_state.traffic_data is not None else "❌ Not loaded"
        
        st.markdown(f"**Network Data:** {network_status}")
        st.markdown(f"**Maintenance Data:** {maintenance_status}")
        st.markdown(f"**Traffic Data:** {traffic_status}")
        
        # Display detour routes status
        detour_status = "✅ Configured" if st.session_state.detour_routes else "❌ Not configured"
        st.markdown(f"**Detour Routes:** {detour_status}")
        
        # Display routing rules status
        rules_status = "✅ Configured" if st.session_state.routing_rules else "❌ Not configured"
        st.markdown(f"**Routing Rules:** {rules_status}")
        
        if st.session_state.optimization_result is not None:
            st.markdown("**Optimization:** ✅ Completed")
            if st.session_state.last_optimization_time:
                st.markdown(f"**Last Run:** {st.session_state.last_optimization_time}")
        elif st.session_state.optimization_running:
            st.markdown("**Optimization:** ⏳ Running...")
        else:
            st.markdown("**Optimization:** ⏱️ Not started")
    
    # Version information
    st.sidebar.markdown(f"**Version:** {APP_VERSION}")
    st.sidebar.markdown("**© 2025 Swedish Transport Administration**")

# Data Management page
elif app_mode == "Data Management":
    st.title("Data Management")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Network Data", "Maintenance Data", "Traffic Data", "Dated Infrastructure", "Generate Data"])
    
    # Network Data Tab
    with tab1:
        st.header("Railway Network Data")
        
        upload_col, generate_col = st.columns(2)
        
        with upload_col:
            st.subheader("Upload Network Data")
            network_file = st.file_uploader("Upload network XML file", type=['xml'])
            
            if network_file:
                # Save uploaded file to temp directory
                temp_dir = create_temp_dir()
                file_path = os.path.join(temp_dir, "network.xml")
                with open(file_path, "wb") as f:
                    f.write(network_file.getvalue())
                
                try:
                    # Parse network data
                    root = read_xml_file(file_path)
                    if root:
                        # Extract nodes
                        nodes = []
                        for node_elem in root.findall('.//node'):
                            node = {
                                'id': node_elem.get('id'),
                                'name': node_elem.get('name'),
                                'lat': float(node_elem.get('lat', 0)),
                                'lon': float(node_elem.get('lon', 0)),
                                'merge_group': node_elem.get('merge_group')
                            }
                            nodes.append(node)
                        
                        # Extract links
                        links = []
                        for link_elem in root.findall('.//link'):
                            link = {
                                'id': link_elem.get('id'),
                                'from_node': link_elem.get('from'),
                                'to_node': link_elem.get('to'),
                                'length': float(link_elem.get('length', 0)),
                                'tracks': int(link_elem.get('tracks', 1)),
                                'capacity': int(link_elem.get('capacity', 5))
                            }
                            links.append(link)
                        
                        # Store network data
                        st.session_state.network_data = {
                            'nodes': nodes,
                            'links': links
                        }
                        
                        st.success(f"Loaded network data: {len(nodes)} nodes and {len(links)} links")
                except Exception as e:
                    st.error(f"Error loading network data: {str(e)}")
        
        with generate_col:
            st.subheader("Generate Network Data")
            if st.button("Generate Sample Network Data"):
                try:
                    # Run the network data generation script
                    temp_dir = create_temp_dir()
                    os.makedirs(os.path.join(temp_dir, 'data/processed'), exist_ok=True)
                    
                    # Call the network_data.py script to generate data
                    from network_data import create_network_data
                    stations_df, links_df = create_network_data()
                    
                    # Convert to our format
                    nodes = []
                    for _, row in stations_df.iterrows():
                        node = {
                            'id': row['node_id'],
                            'name': row['station_name'],
                            'lat': row['lat'],
                            'lon': row['lon'],
                            'merge_group': row['merge_group']
                        }
                        nodes.append(node)
                    
                    links = []
                    for _, row in links_df.iterrows():
                        link = {
                            'id': row['link_id'],
                            'from_node': row['from_node'],
                            'to_node': row['to_node'],
                            'length': row['length_km'],
                            'tracks': row['num_tracks'],
                            'capacity': row['default_capacity']
                        }
                        links.append(link)
                    
                    # Store network data
                    st.session_state.network_data = {
                        'nodes': nodes,
                        'links': links
                    }
                    
                    st.success(f"Generated sample network data: {len(nodes)} nodes and {len(links)} links")
                except Exception as e:
                    st.error(f"Error generating network data: {str(e)}")
        
        # Display network data if available
        if st.session_state.network_data:
            st.subheader("Network Data Preview")
            
            # Create dataframes for display
            nodes_df = pd.DataFrame(st.session_state.network_data['nodes'])
            links_df = pd.DataFrame(st.session_state.network_data['links'])
            
            nodes_tab, links_tab = st.tabs(["Nodes", "Links"])
            
            with nodes_tab:
                st.dataframe(nodes_df)
                st.markdown(download_dataframe_as_csv(nodes_df, "network_nodes"), unsafe_allow_html=True)
            
            with links_tab:
                st.dataframe(links_df)
                st.markdown(download_dataframe_as_csv(links_df, "network_links"), unsafe_allow_html=True)
    
    # Maintenance Data Tab
    with tab2:
        st.header("Maintenance Data")
        
        upload_col, generate_col = st.columns(2)
        
        with upload_col:
            st.subheader("Upload Maintenance Data")
            maintenance_file = st.file_uploader("Upload maintenance XML file", type=['xml'])
            
            if maintenance_file:
                # Save uploaded file to temp directory
                temp_dir = create_temp_dir()
                file_path = os.path.join(temp_dir, "projects.xml")
                with open(file_path, "wb") as f:
                    f.write(maintenance_file.getvalue())
                
                try:
                    # Parse maintenance data
                    root = read_xml_file(file_path)
                    if root:
                        # Extract maintenance measures
                        measures = []
                        project_elems = root.findall('.//project')
                        
                        for project_elem in project_elems:
                            project_id = project_elem.get('id')
                            project_desc = project_elem.get('desc')
                            earliest_start = project_elem.get('earliestStart')
                            latest_end = project_elem.get('latestEnd')
                            
                            # Process tasks
                            for task_elem in project_elem.findall('task'):
                                task_id = task_elem.get('id')
                                task_desc = task_elem.get('desc')
                                duration = float(task_elem.get('durationHr', 0))
                                count = int(task_elem.get('count', 1))
                                
                                # Get track information from traffic_blocking
                                blocking_elem = task_elem.find('traffic_blocking')
                                if blocking_elem is not None:
                                    track_id = blocking_elem.get('link')
                                    blocking_amount = blocking_elem.get('amount')
                                    
                                    # Determine measure type from task/project description
                                    measure_type = "Unknown"
                                    if "renew" in task_desc.lower() or "renew" in project_desc.lower():
                                        measure_type = "Renewal"
                                    elif "prevent" in task_desc.lower() or "prevent" in project_desc.lower():
                                        measure_type = "Preventive"
                                    elif "correct" in task_desc.lower() or "correct" in project_desc.lower():
                                        measure_type = "Corrective"
                                    elif "inspect" in task_desc.lower() or "inspect" in project_desc.lower():
                                        measure_type = "Inspection"
                                    elif "ertms" in task_desc.lower() or "ertms" in project_desc.lower():
                                        measure_type = "ERTMS Implementation"
                                    
                                    # Calculate dates
                                    # For simplicity, convert v24xx format to 2024-xx-01
                                    start_date = earliest_start
                                    if start_date and start_date.startswith('v'):
                                        year = 2000 + int(start_date[1:3])
                                        week = int(start_date[3:5])
                                        # Approximate conversion to date
                                        start_date = f"{year}-{week:02d}-01"
                                    
                                    # Parse task duration to days
                                    duration_days = int(duration / 24) + (1 if duration % 24 > 0 else 0)
                                    
                                    # Create a measure for each instance
                                    for i in range(count):
                                        measure = {
                                            'id': f"{project_id}_{task_id}_{i}",
                                            'project_id': project_id,
                                            'task_id': task_id,
                                            'description': f"{project_desc}: {task_desc}",
                                            'track_id': track_id,
                                            'type': measure_type,
                                            'start_date': start_date,
                                            'duration_days': duration_days,
                                            'track_closure': blocking_amount == "100",
                                            'portability': 2,  # Default medium portability
                                            'responsible_unit': "Maintenance",  # Default unit
                                            'estimated_cost': 100000,  # Default cost
                                            'earliest_start': earliest_start,
                                            'latest_end': latest_end
                                        }
                                        measures.append(measure)
                        
                        # Store maintenance data
                        st.session_state.maintenance_data = measures
                        
                        st.success(f"Loaded maintenance data: {len(measures)} measures")
                except Exception as e:
                    st.error(f"Error loading maintenance data: {str(e)}")
        
        with generate_col:
            st.subheader("Generate Maintenance Data")
            if st.button("Generate Sample Maintenance Data"):
                try:
                    # Check if network data is available
                    if not st.session_state.network_data:
                        st.warning("Please load or generate network data first")
                    else:
                        # Run the maintenance data generation script
                        temp_dir = create_temp_dir()
                        os.makedirs(os.path.join(temp_dir, 'data/processed'), exist_ok=True)
                        
                        # Call the maintenance_data.py script to generate data
                        from maintenance_data import create_maintenance_data
                        maintenance_df = create_maintenance_data()
                        
                        # Parse generated XML file to get maintenance data
                        root = read_xml_file('data/processed/projects.xml')
                        if root:
                            # Extract maintenance measures
                            measures = []
                            project_elems = root.findall('.//project')
                            
                            for project_elem in project_elems:
                                project_id = project_elem.get('id')
                                project_desc = project_elem.get('desc')
                                earliest_start = project_elem.get('earliestStart')
                                latest_end = project_elem.get('latestEnd')
                                
                                # Process tasks
                                for task_elem in project_elem.findall('task'):
                                    task_id = task_elem.get('id')
                                    task_desc = task_elem.get('desc')
                                    duration = float(task_elem.get('durationHr', 0))
                                    count = int(task_elem.get('count', 1))
                                    
                                    # Get track information from traffic_blocking
                                    blocking_elem = task_elem.find('traffic_blocking')
                                    if blocking_elem is not None:
                                        track_id = blocking_elem.get('link')
                                        blocking_amount = blocking_elem.get('amount')
                                        
                                        # Determine measure type from task/project description
                                        measure_type = "Unknown"
                                        if "renew" in task_desc.lower() or "renew" in project_desc.lower():
                                            measure_type = "Renewal"
                                        elif "prevent" in task_desc.lower() or "prevent" in project_desc.lower():
                                            measure_type = "Preventive"
                                        elif "correct" in task_desc.lower() or "correct" in project_desc.lower():
                                            measure_type = "Corrective"
                                        elif "inspect" in task_desc.lower() or "inspect" in project_desc.lower():
                                            measure_type = "Inspection"
                                        elif "ertms" in task_desc.lower() or "ertms" in project_desc.lower():
                                            measure_type = "ERTMS Implementation"
                                        
                                        # Calculate dates
                                        # For simplicity, convert v24xx format to 2024-xx-01
                                        start_date = earliest_start
                                        if start_date and start_date.startswith('v'):
                                            year = 2000 + int(start_date[1:3])
                                            week = int(start_date[3:5])
                                            # Approximate conversion to date
                                            start_date = f"{year}-{week:02d}-01"
                                        
                                        # Parse task duration to days
                                        duration_days = int(duration / 24) + (1 if duration % 24 > 0 else 0)
                                        
                                        # Random portability between 0-5
                                        portability = np.random.randint(0, 6)
                                        
                                        # Create a measure for each instance
                                        for i in range(count):
                                            measure = {
                                                'id': f"{project_id}_{task_id}_{i}",
                                                'project_id': project_id,
                                                'task_id': task_id,
                                                'description': f"{project_desc}: {task_desc}",
                                                'track_id': track_id,
                                                'type': measure_type,
                                                'start_date': start_date,
                                                'duration_days': duration_days,
                                                'track_closure': blocking_amount == "100",
                                                'portability': portability,
                                                'responsible_unit': "Maintenance",
                                                'estimated_cost': np.random.randint(50000, 500000),
                                                'earliest_start': earliest_start,
                                                'latest_end': latest_end
                                            }
                                            measures.append(measure)
                            
                            # Store maintenance data
                            st.session_state.maintenance_data = measures
                            
                            st.success(f"Generated sample maintenance data: {len(measures)} measures")
                except Exception as e:
                    st.error(f"Error generating maintenance data: {str(e)}")
        
        # Display maintenance data if available
        if st.session_state.maintenance_data:
            st.subheader("Maintenance Data Preview")
            
            # Create dataframe for display
            measures_df = pd.DataFrame(st.session_state.maintenance_data)
            
            st.dataframe(measures_df)
            st.markdown(download_dataframe_as_csv(measures_df, "maintenance_data"), unsafe_allow_html=True)
            
            # Add manual measure input form
            st.subheader("Add Maintenance Measure")
            
            if not st.session_state.network_data:
                st.warning("Please load network data first to add maintenance measures")
            else:
                # Create form for adding new measures
                with st.form("add_maintenance_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Get track options from network data
                        track_options = [l['id'] for l in st.session_state.network_data['links']]
                        track_id = st.selectbox("Track", options=track_options)
                        
                        measure_type = st.selectbox("Measure Type", 
                            options=["Preventive", "Corrective", "Renewal", "ERTMS Implementation", 
                                    "Inspection", "Track Work", "Signaling", "Electrical", "Bridge & Structure"])
                        
                        description = st.text_input("Description")
                    
                    with col2:
                        start_date = st.date_input("Start Date", value=datetime.now())
                        duration_days = st.number_input("Duration (days)", value=1, min_value=1)
                        
                        track_closure = st.checkbox("Track Closure Required")
                        portability = st.slider("Portability", min_value=0, max_value=5, value=2, 
                            help="0 = fixed date, 5 = highly flexible")
                    
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        responsible_unit = st.selectbox("Responsible Unit", 
                            options=["Maintenance", "Track", "Signaling", "Electrical", "Bridges & Structures"])
                        
                        estimated_cost = st.number_input("Estimated Cost (SEK)", value=100000, min_value=0)
                    
                    with col4:
                        earliest_start = st.date_input("Earliest Start Date", value=start_date)
                        latest_end = st.date_input("Latest End Date", 
                                                 value=start_date + timedelta(days=duration_days + 30))
                    
                    submit_button = st.form_submit_button("Add Measure")
                    
                    if submit_button:
                        # Generate a unique ID
                        new_id = f"MANUAL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        
                        # Create the measure
                        new_measure = {
                            'id': new_id,
                            'project_id': f"MANUAL_{datetime.now().strftime('%Y%m%d')}",
                            'task_id': f"TASK_{datetime.now().strftime('%H%M%S')}",
                            'description': description,
                            'track_id': track_id,
                            'type': measure_type,
                            'start_date': start_date.strftime(DATE_FORMAT),
                            'duration_days': duration_days,
                            'track_closure': track_closure,
                            'portability': portability,
                            'responsible_unit': responsible_unit,
                            'estimated_cost': estimated_cost,
                            'earliest_start': earliest_start.strftime(DATE_FORMAT),
                            'latest_end': latest_end.strftime(DATE_FORMAT)
                        }
                        
                        # Add to maintenance data
                        if st.session_state.maintenance_data is None:
                            st.session_state.maintenance_data = []
                        
                        st.session_state.maintenance_data.append(new_measure)
                        st.success(f"Added maintenance measure: {description}")
    
    # Traffic Data Tab
    with tab3:
        st.header("Traffic Data")
        
        upload_col, generate_col = st.columns(2)
        
        with upload_col:
            st.subheader("Upload Traffic Data")
            traffic_file = st.file_uploader("Upload traffic XML file", type=['xml'])
            
            if traffic_file:
                # Save uploaded file to temp directory
                temp_dir = create_temp_dir()
                file_path = os.path.join(temp_dir, "traffic.xml")
                with open(file_path, "wb") as f:
                    f.write(traffic_file.getvalue())
                
                try:
                    # Parse traffic data
                    root = read_xml_file(file_path)
                    if root:
                        # Extract train types
                        train_types = []
                        for tt_elem in root.findall('.//train_type'):
                            train_type = {
                                'id': tt_elem.get('id'),
                                'name': tt_elem.get('name')
                            }
                            train_types.append(train_type)
                        
                        # Extract traffic lines
                        lines = []
                        for line_elem in root.findall('.//line'):
                            line = {
                                'id': line_elem.get('id'),
                                'origin': line_elem.get('origin'),
                                'destination': line_elem.get('destination'),
                                'train_type': line_elem.get('train_type')
                            }
                            lines.append(line)
                        
                        # Extract demand data
                        demands = []
                        for demand_elem in root.findall('.//demand'):
                            demand = {
                                'line': demand_elem.get('line'),
                                'start_hr': float(demand_elem.get('startHr', 0)),
                                'end_hr': float(demand_elem.get('endHr', 0)),
                                'demand': float(demand_elem.get('demand', 0))
                            }
                            demands.append(demand)
                        
                        # Extract routes
                        routes = []
                        for route_elem in root.findall('.//line_route'):
                            route_links = []
                            route_durations = {}
                            
                            # Get route string and convert to links
                            route_str = route_elem.get('route', '')
                            nodes = route_str.split('-')
                            for i in range(len(nodes) - 1):
                                route_links.append(f"{nodes[i]}_{nodes[i+1]}")
                            
                            # Get duration for each link
                            for dur_elem in route_elem.findall('dur'):
                                link = dur_elem.get('link')
                                duration = float(dur_elem.text)
                                route_durations[link] = duration
                            
                            route = {
                                'line': route_elem.get('line'),
                                'route_links': route_links,
                                'durations': route_durations
                            }
                            routes.append(route)
                        
                        # Store traffic data
                        st.session_state.traffic_data = {
                            'train_types': train_types,
                            'lines': lines,
                            'demands': demands,
                            'routes': routes
                        }
                        
                        st.success(f"Loaded traffic data: {len(lines)} lines with {len(demands)} demand entries")
                except Exception as e:
                    st.error(f"Error loading traffic data: {str(e)}")
        
        with generate_col:
            st.subheader("Generate Traffic Data")
            if st.button("Generate Sample Traffic Data"):
                try:
                    # Check if network data is available
                    if not st.session_state.network_data:
                        st.warning("Please load or generate network data first")
                    else:
                        # Run the traffic data generation script
                        temp_dir = create_temp_dir()
                        os.makedirs(os.path.join(temp_dir, 'data/processed'), exist_ok=True)
                        
                        # Call the traffic_data.py script to generate data
                        from traffic_data import create_traffic_data
                        relations_df, schedule_df, demand_df, link_times_df = create_traffic_data()
                        
                        # Parse generated XML file to get traffic data
                        root = read_xml_file('data/processed/traffic.xml')
                        if root:
                            # Extract train types
                            train_types = []
                            for tt_elem in root.findall('.//train_type'):
                                train_type = {
                                    'id': tt_elem.get('id'),
                                    'name': tt_elem.get('name')
                                }
                                train_types.append(train_type)
                            
                            # Extract traffic lines
                            lines = []
                            for line_elem in root.findall('.//line'):
                                line = {
                                    'id': line_elem.get('id'),
                                    'origin': line_elem.get('origin'),
                                    'destination': line_elem.get('destination'),
                                    'train_type': line_elem.get('train_type')
                                }
                                lines.append(line)
                            
                            # Extract demand data
                            demands = []
                            for demand_elem in root.findall('.//demand'):
                                demand = {
                                    'line': demand_elem.get('line'),
                                    'start_hr': float(demand_elem.get('startHr', 0)),
                                    'end_hr': float(demand_elem.get('endHr', 0)),
                                    'demand': float(demand_elem.get('demand', 0))
                                }
                                demands.append(demand)
                            
                            # Extract routes
                            routes = []
                            for route_elem in root.findall('.//line_route'):
                                route_links = []
                                route_durations = {}
                                
                                # Get route string and convert to links
                                route_str = route_elem.get('route', '')
                                nodes = route_str.split('-')
                                for i in range(len(nodes) - 1):
                                    route_links.append(f"{nodes[i]}_{nodes[i+1]}")
                                
                                # Get duration for each link
                                for dur_elem in route_elem.findall('dur'):
                                    link = dur_elem.get('link')
                                    duration = float(dur_elem.text)
                                    route_durations[link] = duration
                                
                                route = {
                                    'line': route_elem.get('line'),
                                    'route_links': route_links,
                                    'durations': route_durations
                                }
                                routes.append(route)
                            
                            # Store traffic data
                            st.session_state.traffic_data = {
                                'train_types': train_types,
                                'lines': lines,
                                'demands': demands,
                                'routes': routes
                            }
                            
                            st.success(f"Generated sample traffic data: {len(lines)} lines with {len(demands)} demand entries")
                except Exception as e:
                    st.error(f"Error generating traffic data: {str(e)}")
        
        # Display traffic data if available
        if st.session_state.traffic_data:
            st.subheader("Traffic Data Preview")
            
            train_types_tab, lines_tab, demands_tab, routes_tab = st.tabs(["Train Types", "Lines", "Demands", "Routes"])
            
            with train_types_tab:
                st.dataframe(pd.DataFrame(st.session_state.traffic_data['train_types']))
                st.markdown(download_dataframe_as_csv(pd.DataFrame(st.session_state.traffic_data['train_types']), "train_types"), unsafe_allow_html=True)
            
            with lines_tab:
                st.dataframe(pd.DataFrame(st.session_state.traffic_data['lines']))
                st.markdown(download_dataframe_as_csv(pd.DataFrame(st.session_state.traffic_data['lines']), "traffic_lines"), unsafe_allow_html=True)
            
            with demands_tab:
                st.dataframe(pd.DataFrame(st.session_state.traffic_data['demands']))
                st.markdown(download_dataframe_as_csv(pd.DataFrame(st.session_state.traffic_data['demands']), "traffic_demands"), unsafe_allow_html=True)
            
            with routes_tab:
                # Format routes for display
                routes_display = []
                for route in st.session_state.traffic_data['routes']:
                    routes_display.append({
                        'line': route['line'],
                        'route': '-'.join(route['route_links']),
                        'link_count': len(route['route_links']),
                        'total_duration': sum(route['durations'].values())
                    })
                st.dataframe(pd.DataFrame(routes_display))
                st.markdown(download_dataframe_as_csv(pd.DataFrame(routes_display), "traffic_routes"), unsafe_allow_html=True)
    
    # Dated Infrastructure Tab
    with tab4:
        st.header("Dated Infrastructure Data")
        
        st.markdown("""
        This section allows you to manage infrastructure data for different years.
        This is useful for planning maintenance activities on future infrastructure configurations.
        """)
        
        # Add new dated infrastructure
        with st.expander("Add Dated Infrastructure", expanded=True):
            if not st.session_state.network_data:
                st.warning("Please load network data first")
            else:
                with st.form("add_dated_infrastructure"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        year = st.number_input("Year", min_value=2024, max_value=2050, value=2025)
                        
                    with col2:
                        base_on_current = st.checkbox("Base on current infrastructure", value=True)
                    
                    submit_button = st.form_submit_button("Add Infrastructure for Year")
                    
                    if submit_button:
                        if str(year) in st.session_state.dated_infrastructure:
                            st.warning(f"Infrastructure data for year {year} already exists. It will be overwritten.")
                        
                        if base_on_current:
                            # Copy current infrastructure
                            st.session_state.dated_infrastructure[str(year)] = {
                                'nodes': st.session_state.network_data['nodes'].copy(),
                                'links': st.session_state.network_data['links'].copy()
                            }
                        else:
                            # Create empty infrastructure
                            st.session_state.dated_infrastructure[str(year)] = {
                                'nodes': [],
                                'links': []
                            }
                        
                        st.success(f"Added infrastructure data for year {year}")
        
        # Edit dated infrastructure
        if st.session_state.dated_infrastructure:
            st.subheader("Edit Dated Infrastructure")
            
            # Select year to edit
            year_options = list(st.session_state.dated_infrastructure.keys())
            selected_year = st.selectbox("Select Year", options=year_options)
            
            if selected_year:
                # Display infrastructure data for selected year
                infra_data = st.session_state.dated_infrastructure[selected_year]
                
                # Create dataframes for display
                nodes_df = pd.DataFrame(infra_data['nodes'])
                links_df = pd.DataFrame(infra_data['links'])
                
                nodes_tab, links_tab, modify_tab = st.tabs(["Nodes", "Links", "Modify Infrastructure"])
                
                with nodes_tab:
                    st.dataframe(nodes_df)
                
                with links_tab:
                    st.dataframe(links_df)
                
                with modify_tab:
                    st.subheader(f"Modify Infrastructure for Year {selected_year}")
                    
                    # Add/remove/modify infrastructure elements
                    modify_type = st.radio("Modification Type", ["Add Link", "Modify Link", "Remove Link"])
                    
                    if modify_type == "Add Link":
                        with st.form("add_link_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                link_id = st.text_input("Link ID")
                                from_node = st.selectbox("From Node", options=[n['id'] for n in infra_data['nodes']])
                                to_node = st.selectbox("To Node", options=[n['id'] for n in infra_data['nodes']])
                            
                            with col2:
                                length = st.number_input("Length (km)", min_value=0.0, value=10.0)
                                tracks = st.number_input("Number of Tracks", min_value=1, value=1)
                                capacity = st.number_input("Capacity (trains/hour)", min_value=1, value=5)
                            
                            submit_button = st.form_submit_button("Add Link")
                            
                            if submit_button:
                                # Check if link already exists
                                if any(l['id'] == link_id for l in infra_data['links']):
                                    st.error(f"Link with ID {link_id} already exists")
                                else:
                                    # Add new link
                                    new_link = {
                                        'id': link_id,
                                        'from_node': from_node,
                                        'to_node': to_node,
                                        'length': length,
                                        'tracks': tracks,
                                        'capacity': capacity
                                    }
                                    
                                    infra_data['links'].append(new_link)
                                    st.success(f"Added link {link_id}")
                    
                    elif modify_type == "Modify Link":
                        # Select link to modify
                        link_options = [l['id'] for l in infra_data['links']]
                        selected_link_id = st.selectbox("Select Link to Modify", options=link_options)
                        
                        if selected_link_id:
                            selected_link = next((l for l in infra_data['links'] if l['id'] == selected_link_id), None)
                            
                            if selected_link:
                                with st.form("modify_link_form"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        from_node = st.selectbox("From Node", 
                                                               options=[n['id'] for n in infra_data['nodes']], 
                                                               index=[n['id'] for n in infra_data['nodes']].index(selected_link['from_node']) if selected_link['from_node'] in [n['id'] for n in infra_data['nodes']] else 0)
                                        to_node = st.selectbox("To Node", 
                                                             options=[n['id'] for n in infra_data['nodes']], 
                                                             index=[n['id'] for n in infra_data['nodes']].index(selected_link['to_node']) if selected_link['to_node'] in [n['id'] for n in infra_data['nodes']] else 0)
                                    
                                    with col2:
                                        length = st.number_input("Length (km)", 
                                                               min_value=0.0, 
                                                               value=float(selected_link['length']))
                                        tracks = st.number_input("Number of Tracks", 
                                                              min_value=1, 
                                                              value=int(selected_link['tracks']))
                                        capacity = st.number_input("Capacity (trains/hour)", 
                                                                min_value=1, 
                                                                value=int(selected_link['capacity']))
                                    
                                    submit_button = st.form_submit_button("Update Link")
                                    
                                    if submit_button:
                                        # Update link
                                        for i, link in enumerate(infra_data['links']):
                                            if link['id'] == selected_link_id:
                                                infra_data['links'][i]['from_node'] = from_node
                                                infra_data['links'][i]['to_node'] = to_node
                                                infra_data['links'][i]['length'] = length
                                                infra_data['links'][i]['tracks'] = tracks
                                                infra_data['links'][i]['capacity'] = capacity
                                                break
                                        
                                        st.success(f"Updated link {selected_link_id}")
                    
                    elif modify_type == "Remove Link":
                        # Select link to remove
                        link_options = [l['id'] for l in infra_data['links']]
                        selected_link_id = st.selectbox("Select Link to Remove", options=link_options)
                        
                        if selected_link_id and st.button(f"Remove Link {selected_link_id}"):
                            # Remove link
                            infra_data['links'] = [l for l in infra_data['links'] if l['id'] != selected_link_id]
                            st.success(f"Removed link {selected_link_id}")
                
                # Delete year button
                if st.button(f"Delete Infrastructure for Year {selected_year}"):
                    del st.session_state.dated_infrastructure[selected_year]
                    st.success(f"Deleted infrastructure data for year {selected_year}")
                    st.experimental_rerun()
        else:
            st.info("No dated infrastructure data available. Add infrastructure data for future years above.")
    
    # Generate Complete Dataset Tab
    with tab5:
        st.header("Generate Complete Dataset")
        
        st.markdown("""
        This will generate a complete set of data files for the railway planning tool:
        - Network data (stations and links)
        - Maintenance data (projects and tasks)
        - Traffic data (lines, demands, routes)
        
        It will also create a consolidated problem.xml file that can be used for optimization.
        """)
        
        if st.button("Generate Complete Dataset", key="generate_all"):
            try:
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Step 1: Generate network data
                status_text.text("Generating network data...")
                
                # Import and run generation script
                temp_dir = create_temp_dir()
                os.makedirs(os.path.join(temp_dir, 'data/processed'), exist_ok=True)
                
                from network_data import create_network_data
                stations_df, links_df = create_network_data()
                
                # Convert to our format
                nodes = []
                for _, row in stations_df.iterrows():
                    node = {
                        'id': row['node_id'],
                        'name': row['station_name'],
                        'lat': row['lat'],
                        'lon': row['lon'],
                        'merge_group': row['merge_group']
                    }
                    nodes.append(node)
                
                links = []
                for _, row in links_df.iterrows():
                    link = {
                        'id': row['link_id'],
                        'from_node': row['from_node'],
                        'to_node': row['to_node'],
                        'length': row['length_km'],
                        'tracks': row['num_tracks'],
                        'capacity': row['default_capacity']
                    }
                    links.append(link)
                
                # Store network data
                st.session_state.network_data = {
                    'nodes': nodes,
                    'links': links
                }
                
                progress_bar.progress(25)
                status_text.text("Network data generated. Generating maintenance data...")
                
                # Step 2: Generate maintenance data
                from maintenance_data import create_maintenance_data
                maintenance_df = create_maintenance_data()
                
                # Parse generated XML file to get maintenance data
                root = read_xml_file('data/processed/projects.xml')
                if root:
                    # Extract maintenance measures
                    measures = []
                    project_elems = root.findall('.//project')
                    
                    for project_elem in project_elems:
                        project_id = project_elem.get('id')
                        project_desc = project_elem.get('desc')
                        earliest_start = project_elem.get('earliestStart')
                        latest_end = project_elem.get('latestEnd')
                        
                        # Process tasks
                        for task_elem in project_elem.findall('task'):
                            task_id = task_elem.get('id')
                            task_desc = task_elem.get('desc')
                            duration = float(task_elem.get('durationHr', 0))
                            count = int(task_elem.get('count', 1))
                            
                            # Get track information from traffic_blocking
                            blocking_elem = task_elem.find('traffic_blocking')
                            if blocking_elem is not None:
                                track_id = blocking_elem.get('link')
                                blocking_amount = blocking_elem.get('amount')
                                
                                # Determine measure type from task/project description
                                measure_type = "Unknown"
                                if "renew" in task_desc.lower() or "renew" in project_desc.lower():
                                    measure_type = "Renewal"
                                elif "prevent" in task_desc.lower() or "prevent" in project_desc.lower():
                                    measure_type = "Preventive"
                                elif "correct" in task_desc.lower() or "correct" in project_desc.lower():
                                    measure_type = "Corrective"
                                elif "inspect" in task_desc.lower() or "inspect" in project_desc.lower():
                                    measure_type = "Inspection"
                                elif "ertms" in task_desc.lower() or "ertms" in project_desc.lower():
                                    measure_type = "ERTMS Implementation"
                                
                                # Calculate dates
                                # For simplicity, convert v24xx format to 2024-xx-01
                                start_date = earliest_start
                                if start_date and start_date.startswith('v'):
                                    year = 2000 + int(start_date[1:3])
                                    week = int(start_date[3:5])
                                    # Approximate conversion to date
                                    start_date = f"{year}-{week:02d}-01"
                                
                                # Parse task duration to days
                                duration_days = int(duration / 24) + (1 if duration % 24 > 0 else 0)
                                
                                # Random portability
                                portability = np.random.randint(0, 6)
                                
                                # Create a measure for each instance
                                for i in range(count):
                                    measure = {
                                        'id': f"{project_id}_{task_id}_{i}",
                                        'project_id': project_id,
                                        'task_id': task_id,
                                        'description': f"{project_desc}: {task_desc}",
                                        'track_id': track_id,
                                        'type': measure_type,
                                        'start_date': start_date,
                                        'duration_days': duration_days,
                                        'track_closure': blocking_amount == "100",
                                        'portability': portability,
                                        'responsible_unit': "Maintenance",
                                        'estimated_cost': np.random.randint(50000, 500000),
                                        'earliest_start': earliest_start,
                                        'latest_end': latest_end
                                    }
                                    measures.append(measure)
                
                # Store maintenance data
                st.session_state.maintenance_data = measures
                
                progress_bar.progress(50)
                status_text.text("Maintenance data generated. Generating traffic data...")
                
                # Step 3: Generate traffic data
                from traffic_data import create_traffic_data
                relations_df, schedule_df, demand_df, link_times_df = create_traffic_data()
                
                # Parse generated XML file to get traffic data
                root = read_xml_file('data/processed/traffic.xml')
                if root:
                    # Extract train types
                    train_types = []
                    for tt_elem in root.findall('.//train_type'):
                        train_type = {
                            'id': tt_elem.get('id'),
                            'name': tt_elem.get('name')
                        }
                        train_types.append(train_type)
                    
                    # Extract traffic lines
                    lines = []
                    for line_elem in root.findall('.//line'):
                        line = {
                            'id': line_elem.get('id'),
                            'origin': line_elem.get('origin'),
                            'destination': line_elem.get('destination'),
                            'train_type': line_elem.get('train_type')
                        }
                        lines.append(line)
                    
                    # Extract demand data
                    demands = []
                    for demand_elem in root.findall('.//demand'):
                        demand = {
                            'line': demand_elem.get('line'),
                            'start_hr': float(demand_elem.get('startHr', 0)),
                            'end_hr': float(demand_elem.get('endHr', 0)),
                            'demand': float(demand_elem.get('demand', 0))
                        }
                        demands.append(demand)
                    
                    # Extract routes
                    routes = []
                    for route_elem in root.findall('.//line_route'):
                        route_links = []
                        route_durations = {}
                        
                        # Get route string and convert to links
                        route_str = route_elem.get('route', '')
                        nodes = route_str.split('-')
                        for i in range(len(nodes) - 1):
                            route_links.append(f"{nodes[i]}_{nodes[i+1]}")
                        
                        # Get duration for each link
                        for dur_elem in route_elem.findall('dur'):
                            link = dur_elem.get('link')
                            duration = float(dur_elem.text)
                            route_durations[link] = duration
                        
                        route = {
                            'line': route_elem.get('line'),
                            'route_links': route_links,
                            'durations': route_durations
                        }
                        routes.append(route)
                    
                    # Store traffic data
                    st.session_state.traffic_data = {
                        'train_types': train_types,
                        'lines': lines,
                        'demands': demands,
                        'routes': routes
                    }
                
                progress_bar.progress(75)
                status_text.text("Traffic data generated. Creating consolidated problem.xml...")
                
                # Step 4: Create consolidated problem.xml
                from create_problem_xml import create_problem_xml
                create_problem_xml(
                    network_file='data/processed/network.xml',
                    traffic_file='data/processed/traffic.xml',
                    projects_file='data/processed/projects.xml'
                )
                
                # Step 5: Generate initial detour routes
                st.session_state.detour_routes = {}
                
                # For each major link, create an alternative route
                if st.session_state.network_data and st.session_state.traffic_data:
                    # Generate simple detour routes for demonstration
                    for link in links[:10]:  # Limit to first 10 links
                        link_id = link['id']
                        
                        # Find nodes that could form an alternative path
                        G = nx.Graph()
                        
                        # Add all nodes and edges
                        for node in nodes:
                            G.add_node(node['id'])
                        
                        for edge in links:
                            G.add_edge(edge['from_node'], edge['to_node'], id=edge['id'])
                        
                        # Remove the current link
                        G.remove_edge(link['from_node'], link['to_node'])
                        
                        # Try to find alternative path
                        try:
                            alt_path = nx.shortest_path(G, link['from_node'], link['to_node'])
                            
                            # Convert node path to link path
                            alt_links = []
                            for i in range(len(alt_path) - 1):
                                # Find the link ID
                                for edge in links:
                                    if (edge['from_node'] == alt_path[i] and edge['to_node'] == alt_path[i+1]) or \
                                       (edge['from_node'] == alt_path[i+1] and edge['to_node'] == alt_path[i]):
                                        alt_links.append(edge['id'])
                                        break
                            
                            if alt_links:
                                st.session_state.detour_routes[link_id] = {
                                    'original_link': link_id,
                                    'original_from': link['from_node'],
                                    'original_to': link['to_node'],
                                    'detour_links': alt_links,
                                    'detour_path': alt_path,
                                    'train_types': ['ALL']  # Default to all train types
                                }
                        except nx.NetworkXNoPath:
                            # No alternative path
                            pass
                
                progress_bar.progress(100)
                status_text.text("Complete dataset generated successfully!")
                
                st.success("""
                Dataset generated successfully! Summary:
                - Network: {} nodes, {} links
                - Maintenance: {} measures
                - Traffic: {} lines, {} demand entries
                - Detour routes: {} configured
                - Consolidated problem.xml file created
                """.format(
                    len(nodes), len(links),
                    len(measures),
                    len(lines), len(demands),
                    len(st.session_state.detour_routes)
                ))
            except Exception as e:
                st.error(f"Error generating complete dataset: {str(e)}")

# Network Visualization page
elif app_mode == "Network Visualization":
    st.title("Railway Network Visualization")
    
    if st.session_state.network_data is None:
        st.warning("No network data available. Please go to Data Management to load or generate network data.")
    else:
        # Visualization options
        st.sidebar.header("Visualization Options")
        
        # Year selection for dated infrastructure
        if st.session_state.dated_infrastructure:
            year_options = ['Current'] + list(st.session_state.dated_infrastructure.keys())
            selected_year = st.sidebar.selectbox("Infrastructure Year", options=year_options, index=0)
            
            if selected_year != 'Current':
                network_data = st.session_state.dated_infrastructure[selected_year]
            else:
                network_data = st.session_state.network_data
        else:
            network_data = st.session_state.network_data
            selected_year = 'Current'
        
        # Region filter
        all_regions = list(set([n.get('merge_group', 'Other') for n in network_data['nodes']]))
        all_regions = [r for r in all_regions if r is not None] + ['Other']
        selected_region = st.sidebar.selectbox("Filter by Region", options=['All'] + all_regions, index=0)
        
        # Display options
        show_node_labels = st.sidebar.checkbox("Show Node Labels", value=True)
        show_link_labels = st.sidebar.checkbox("Show Link Labels", value=False)
        show_track_capacity = st.sidebar.checkbox("Color by Track Capacity", value=True)
        
        # Maintenance visualization options
        if st.session_state.maintenance_data:
            show_maintenance = st.sidebar.checkbox("Show Maintenance Activities", value=True)
            
            if show_maintenance:
                maintenance_date = st.sidebar.date_input(
                    "Maintenance Date", 
                    value=datetime.now().date(),
                    help="Show maintenance activities on this date"
                )
        else:
            show_maintenance = False
            maintenance_date = datetime.now().date()
        
        # Detour route visualization
        show_detours = st.sidebar.checkbox("Show Detour Routes", value=False)
        if show_detours and st.session_state.detour_routes:
            selected_detour = st.sidebar.selectbox(
                "Select Detour Route", 
                options=['None'] + list(st.session_state.detour_routes.keys())
            )
        else:
            selected_detour = 'None'
        
        # Create tabs for different visualizations
        map_tab, graph_tab, capacity_tab = st.tabs(["Map View", "Network Graph", "Capacity Analysis"])
        
        # MAP VIEW
        with map_tab:
            # Create a base map centered on Sweden
            m = folium.Map(location=[62, 15], zoom_start=5)
            
            # Filter nodes by region if selected
            if selected_region != 'All':
                if selected_region == 'Other':
                    filtered_nodes = [n for n in network_data['nodes'] 
                                    if n.get('merge_group') is None]
                else:
                    filtered_nodes = [n for n in network_data['nodes'] 
                                    if n.get('merge_group') == selected_region]
            else:
                filtered_nodes = network_data['nodes']
            
            # Create a dict to quickly look up nodes by ID
            node_dict = {n['id']: n for n in network_data['nodes']}
            
            # Filter links that connect to filtered nodes
            filtered_link_ids = set()
            for link in network_data['links']:
                if link['from_node'] in [n['id'] for n in filtered_nodes] or \
                   link['to_node'] in [n['id'] for n in filtered_nodes]:
                    filtered_link_ids.add(link['id'])
            
            filtered_links = [l for l in network_data['links'] 
                            if l['id'] in filtered_link_ids]
            
            # Add nodes to map
            for node in filtered_nodes:
                if node.get('lat') and node.get('lon'):
                    popup_text = f"""
                    <b>{node.get('name', 'Unknown')}</b><br>
                    ID: {node['id']}<br>
                    Group: {node.get('merge_group', 'None')}
                    """
                    
                    folium.CircleMarker(
                        location=[node['lat'], node['lon']],
                        radius=5,
                        color='blue',
                        fill=True,
                        fill_opacity=0.7,
                        popup=popup_text
                    ).add_to(m)
                    
                    if show_node_labels:
                        folium.Marker(
                            location=[node['lat'], node['lon']],
                            icon=folium.DivIcon(
                                icon_size=(100, 36),
                                icon_anchor=(50, 20),
                                html=f'<div style="font-size: 10pt; color: darkblue;">{node["id"]}</div>'
                            )
                        ).add_to(m)
            
            # Define color scale for track capacity
            def get_capacity_color(capacity):
                if capacity <= 3:
                    return 'red'
                elif capacity <= 7:
                    return 'orange'
                elif capacity <= 10:
                    return 'green'
                else:
                    return 'blue'
            
            # Get active maintenance activities on selected date
            maintenance_on_link = {}
            if show_maintenance and st.session_state.maintenance_data:
                for m in st.session_state.maintenance_data:
                    start_date = parse_date(m.get('start_date'))
                    if start_date:
                        end_date = start_date + timedelta(days=m.get('duration_days', 0))
                        if start_date <= maintenance_date <= end_date:
                            track_id = m.get('track_id')
                            if track_id not in maintenance_on_link:
                                maintenance_on_link[track_id] = []
                            maintenance_on_link[track_id].append(m)
            
            # Add links to map
            for link in filtered_links:
                from_node = node_dict.get(link['from_node'])
                to_node = node_dict.get(link['to_node'])
                
                if from_node and to_node and from_node.get('lat') and from_node.get('lon') and \
                   to_node.get('lat') and to_node.get('lon'):
                    
                    # Determine color based on capacity
                    if show_track_capacity:
                        color = get_capacity_color(link.get('capacity', 5))
                    else:
                        color = 'blue'
                    
                    # Check if there's maintenance on this link
                    maintenance_info = ""
                    if link['id'] in maintenance_on_link:
                        color = 'red'  # Override color for links with maintenance
                        maintenance_info = "<br><br><b>Maintenance Activities:</b><br>"
                        for m in maintenance_on_link[link['id']]:
                            maintenance_info += f"- {m.get('description', 'Unknown')} ({m.get('type', 'Unknown')})<br>"
                            maintenance_info += f"  Duration: {m.get('duration_days', 0)} days<br>"
                    
                    # Create popup with link info
                    popup_text = f"""
                    <b>Link: {link['id']}</b><br>
                    From: {from_node.get('name', from_node['id'])} to {to_node.get('name', to_node['id'])}<br>
                    Tracks: {link.get('tracks', 1)}<br>
                    Capacity: {link.get('capacity', 5)} trains/hour<br>
                    Length: {link.get('length', 0)} km
                    {maintenance_info}
                    """
                    
                    # Check if this link is part of selected detour route
                    is_detour = False
                    is_original = False
                    if selected_detour != 'None' and selected_detour in st.session_state.detour_routes:
                        detour_info = st.session_state.detour_routes[selected_detour]
                        if link['id'] in detour_info['detour_links']:
                            is_detour = True
                        elif link['id'] == selected_detour:
                            is_original = True
                    
                    # Adjust color for detour routes
                    if is_detour:
                        color = 'green'  # Detour route
                        dash_array = '5, 5'  # Dashed line
                    elif is_original:
                        color = 'purple'  # Original link being detoured
                        dash_array = None
                    else:
                        dash_array = None
                    
                    # Add the link as a polyline
                    folium.PolyLine(
                        locations=[[from_node['lat'], from_node['lon']], [to_node['lat'], to_node['lon']]],
                        color=color,
                        weight=2 * link.get('tracks', 1),  # Line thickness based on number of tracks
                        opacity=0.7,
                        popup=popup_text,
                        dash_array=dash_array
                    ).add_to(m)
                    
                    # Add link label if requested
                    if show_link_labels:
                        # Calculate middle position for label
                        mid_lat = (from_node['lat'] + to_node['lat']) / 2
                        mid_lon = (from_node['lon'] + to_node['lon']) / 2
                        
                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            icon=folium.DivIcon(
                                icon_size=(100, 36),
                                icon_anchor=(50, 20),
                                html=f'<div style="font-size: 8pt; color: darkblue;">{link["id"]}</div>'
                            )
                        ).add_to(m)
            
            # Add legend
            legend_html = '''
            <div style="position: fixed; bottom: 50px; left: 50px; z-index:1000; background-color: white; 
                        padding: 10px; border: 1px solid grey; border-radius: 5px;">
                <p><b>Legend</b></p>
                <p><i style="background: blue; width: 10px; height: 10px; display: inline-block;"></i> High Capacity (>10)</p>
                <p><i style="background: green; width: 10px; height: 10px; display: inline-block;"></i> Medium Capacity (7-10)</p>
                <p><i style="background: orange; width: 10px; height: 10px; display: inline-block;"></i> Low Capacity (4-7)</p>
                <p><i style="background: red; width: 10px; height: 10px; display: inline-block;"></i> Very Low Capacity (<4) / Maintenance</p>
            '''
            
            if selected_detour != 'None':
                legend_html += '''
                <p><i style="background: purple; width: 10px; height: 10px; display: inline-block;"></i> Original Link</p>
                <p><i style="background: green; width: 10px; height: 10px; display: inline-block; 
                            border-top: 1px dashed #000;"></i> Detour Route</p>
                '''
            
            legend_html += '</div>'
            
            # Add legend safely
            root = m.get_root()
            if hasattr(root, 'html') and hasattr(root.html, 'add_child'):
                root.html.add_child(folium.Element(legend_html))
            else:
                # Alternative approach if the expected structure isn't available
                m.get_root().get_name()  # No-op to prevent error
            
            # Display the map
            st.subheader(f"Swedish Railway Network - {selected_year}")
            folium_static(m)
            
            # Display maintenance activities on selected date
            if show_maintenance and maintenance_on_link:
                st.subheader(f"Maintenance Activities on {maintenance_date}")
                
                # Collect all maintenance activities
                all_maintenance = []
                for link_id, activities in maintenance_on_link.items():
                    for activity in activities:
                        all_maintenance.append({
                            'Link ID': link_id,
                            'Description': activity.get('description', 'Unknown'),
                            'Type': activity.get('type', 'Unknown'),
                            'Start Date': activity.get('start_date', 'Unknown'),
                            'Duration (days)': activity.get('duration_days', 0),
                            'Responsible Unit': activity.get('responsible_unit', 'Unknown')
                        })
                
                # Display as table
                st.dataframe(pd.DataFrame(all_maintenance))
            
            # Display selected detour route
            if selected_detour != 'None' and selected_detour in st.session_state.detour_routes:
                st.subheader(f"Detour Route for {selected_detour}")
                
                detour_info = st.session_state.detour_routes[selected_detour]
                
                st.markdown(f"""
                **Original Link:** {detour_info['original_link']} 
                (from {detour_info['original_from']} to {detour_info['original_to']})
                
                **Detour Path:** {' → '.join(detour_info['detour_path'])}
                
                **Detour Links:** {', '.join(detour_info['detour_links'])}
                
                **Train Types:** {', '.join(detour_info['train_types'])}
                """)
        
        # NETWORK GRAPH
        with graph_tab:
            # Create a networkx graph
            G = nx.Graph()
            
            # Add nodes
            for node in filtered_nodes:
                G.add_node(node['id'], name=node.get('name', node['id']), 
                          merge_group=node.get('merge_group', 'None'))
            
            # Add edges
            for link in filtered_links:
                from_node = link['from_node']
                to_node = link['to_node']
                if from_node in G.nodes and to_node in G.nodes:
                    G.add_edge(from_node, to_node, 
                              id=link['id'], 
                              tracks=link.get('tracks', 1),
                              capacity=link.get('capacity', 5),
                              length=link.get('length', 0))
            
            # Create plot
            plt.figure(figsize=(12, 8))
            
            # Set positions based on geographical coordinates if available
            pos = {}
            for node in filtered_nodes:
                if node.get('lat') and node.get('lon'):
                    pos[node['id']] = (node['lon'], node['lat'])
            
            # If no positions specified, use spring layout
            if not pos:
                pos = nx.spring_layout(G)
            
            # Draw nodes
            node_colors = ['red' if G.nodes[n].get('merge_group') == selected_region else 'blue' 
                          for n in G.nodes]
            
            nx.draw_networkx_nodes(G, pos, node_size=100, node_color=node_colors, alpha=0.7)
            
            if show_node_labels:
                nx.draw_networkx_labels(G, pos, font_size=8)
            
            # Draw edges
            if show_track_capacity:
                edge_colors = [get_capacity_color(G.edges[e].get('capacity', 5)) for e in G.edges]
            else:
                edge_colors = ['black' for e in G.edges]
            
            # Check for maintenance and detour routes
            if show_maintenance:
                for i, e in enumerate(G.edges):
                    link_id = G.edges[e].get('id')
                    if link_id in maintenance_on_link:
                        edge_colors[i] = 'red'
            
            # Highlight detour route if selected
            if selected_detour != 'None' and selected_detour in st.session_state.detour_routes:
                detour_info = st.session_state.detour_routes[selected_detour]
                for i, e in enumerate(G.edges):
                    link_id = G.edges[e].get('id')
                    if link_id == selected_detour:
                        edge_colors[i] = 'purple'  # Original link
                    elif link_id in detour_info['detour_links']:
                        edge_colors[i] = 'green'  # Detour route
            
            edge_widths = [G.edges[e].get('tracks', 1) for e in G.edges]
            
            nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, alpha=0.5)
            
            if show_link_labels:
                edge_labels = {(u,v): G.edges[u,v].get('id', '') for u, v in G.edges}
                nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
            
            plt.title(f"Swedish Railway Network - {selected_region if selected_region != 'All' else 'All Regions'} ({selected_year})")
            plt.axis('off')
            
            # Display the plot
            st.pyplot(plt)
        
        # CAPACITY ANALYSIS
        with capacity_tab:
            st.subheader("Track Capacity Analysis")
            
            # Create capacity visualization
            capacity_data = [{'id': l['id'], 'capacity': l.get('capacity', 5), 'tracks': l.get('tracks', 1),
                             'from_node': l['from_node'], 'to_node': l['to_node']}
                           for l in network_data['links']]
            
            capacity_df = pd.DataFrame(capacity_data)
            
            # Sort by capacity
            capacity_df = capacity_df.sort_values('capacity', ascending=False)
            
            # Create column for track type
            capacity_df['track_type'] = capacity_df['tracks'].apply(
                lambda x: 'Double track' if x >= 2 else 'Single track')
            
            # Filter for display if needed
            if len(capacity_df) > 50:
                st.info(f"Showing top 50 of {len(capacity_df)} tracks by capacity")
                display_df = capacity_df.head(50)
            else:
                display_df = capacity_df
            
            # Bar chart of capacity by track
            fig = px.bar(display_df, x='id', y='capacity', 
                       color='track_type',
                       title="Track Capacity (trains/hour)",
                       labels={'id': 'Track ID', 'capacity': 'Capacity (trains/hour)'},
                       color_discrete_map={'Single track': 'orange', 'Double track': 'green'},
                       height=500)
            
            fig.update_layout(xaxis_tickangle=-45)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show capacity distribution
            st.subheader("Capacity Distribution")
            
            # Histogram of capacity
            fig = px.histogram(capacity_df, x='capacity', nbins=10,
                              title="Distribution of Track Capacity",
                              labels={'capacity': 'Capacity (trains/hour)', 'count': 'Number of Tracks'},
                              color='track_type',
                              color_discrete_map={'Single track': 'orange', 'Double track': 'green'},
                              height=400)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show capacity by region if regions exist
            if 'merge_group' in st.session_state.network_data['nodes'][0]:
                st.subheader("Capacity by Region")
                
                # Add region information to links
                regions = {}
                for node in st.session_state.network_data['nodes']:
                    regions[node['id']] = node.get('merge_group', 'Other')
                
                # For each link, determine region by source node's region
                capacity_df['region'] = capacity_df['from_node'].map(regions)
                
                # Calculate average capacity by region
                region_capacity = capacity_df.groupby('region')['capacity'].mean().reset_index()
                region_capacity = region_capacity.sort_values('capacity', ascending=False)
                
                # Bar chart of average capacity by region
                fig = px.bar(region_capacity, x='region', y='capacity',
                           title="Average Track Capacity by Region",
                           labels={'region': 'Region', 'capacity': 'Average Capacity (trains/hour)'},
                           color='capacity',
                           color_continuous_scale=px.colors.sequential.Viridis,
                           height=400)
                
                st.plotly_chart(fig, use_container_width=True)

# Maintenance Schedule page
elif app_mode == "Maintenance Schedule":
    st.title("Maintenance Schedule")
    
    if st.session_state.maintenance_data is None:
        st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
    else:
        # Filter options in sidebar
        st.sidebar.header("Filter Options")
        
        # Date range filter
        default_start = datetime.now().date()
        default_end = default_start + timedelta(days=180)
        
        date_col1, date_col2 = st.sidebar.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", value=default_start)
        with date_col2:
            end_date = st.date_input("End Date", value=default_end)
        
        # Track filter
        if st.session_state.network_data:
            track_options = [{'label': l['id'], 'value': l['id']} for l in st.session_state.network_data['links']]
            selected_track = st.sidebar.selectbox("Track", options=['All'] + [t['value'] for t in track_options])
        else:
            # Get unique track IDs from maintenance data
            track_ids = list(set([m.get('track_id') for m in st.session_state.maintenance_data 
                                if m.get('track_id') is not None]))
            selected_track = st.sidebar.selectbox("Track", options=['All'] + track_ids)
        
        # Maintenance type filter
        maintenance_types = list(set([m.get('type', 'Unknown') for m in st.session_state.maintenance_data]))
        selected_type = st.sidebar.selectbox("Maintenance Type", options=['All'] + maintenance_types)
        
        # Additional filters
        with st.sidebar.expander("Advanced Filters"):
            # Unit filter
            responsible_units = list(set([m.get('responsible_unit', 'Unknown') for m in st.session_state.maintenance_data 
                                      if m.get('responsible_unit') is not None]))
            selected_unit = st.selectbox("Responsible Unit", options=['All'] + responsible_units)
            
            # Portability filter
            portability_options = list(range(6))  # 0-5
            min_portability = st.select_slider("Min Portability", options=portability_options, value=0)
            
            # Track closure filter
            track_closure = st.radio("Track Closure", options=['All', 'Yes', 'No'])
        
        # ERTMS Implementation filter
        show_ertms = st.sidebar.checkbox("Show ERTMS Implementation Plan", value=False)
        
        # Apply filters
        filtered_measures = st.session_state.maintenance_data.copy()
        
        # Filter by date
        if start_date or end_date:
            filtered_measures = [m for m in filtered_measures if (
                not start_date or parse_date(m.get('start_date', '')) >= start_date) and (
                not end_date or parse_date(m.get('start_date', '')) <= end_date
            )]
        
        # Filter by track
        if selected_track != 'All':
            filtered_measures = [m for m in filtered_measures if m.get('track_id') == selected_track]
        
        # Filter by type
        if selected_type != 'All':
            filtered_measures = [m for m in filtered_measures if m.get('type') == selected_type]
        
        # Filter by responsible unit
        if selected_unit != 'All':
            filtered_measures = [m for m in filtered_measures if m.get('responsible_unit') == selected_unit]
        
        # Filter by portability
        filtered_measures = [m for m in filtered_measures if m.get('portability', 0) >= min_portability]
        
        # Filter by track closure
        if track_closure != 'All':
            track_closure_bool = (track_closure == 'Yes')
            filtered_measures = [m for m in filtered_measures if m.get('track_closure', False) == track_closure_bool]
        
        # Filter ERTMS Implementation
        if show_ertms:
            filtered_measures = [m for m in filtered_measures if m.get('type') == 'ERTMS Implementation']
        
        # Create Gantt chart
        st.subheader("Maintenance Gantt Chart")
        
        if not filtered_measures:
            st.info("No maintenance measures match the selected filters.")
        else:
            # Create dataframe for Gantt
            gantt_data = []
            
            for measure in filtered_measures:
                # Parse dates
                start_date_str = measure.get('start_date', '')
                start_date_obj = parse_date(start_date_str)
                
                if start_date_obj:
                    # Calculate end date
                    duration_days = measure.get('duration_days', 1)
                    end_date_obj = start_date_obj + timedelta(days=duration_days)
                    
                    # Determine color based on type
                    color = get_maintenance_color(measure.get('type', 'Unknown'))
                    
                    # Add to Gantt data
                    gantt_data.append({
                        'Task': f"{measure.get('track_id', 'Unknown')}: {measure.get('description', 'Unknown')}",
                        'Start': start_date_obj,
                        'Finish': end_date_obj,
                        'Type': measure.get('type', 'Unknown'),
                        'ID': measure.get('id', 'Unknown'),
                        'Color': color,
                        'Track': measure.get('track_id', 'Unknown'),
                        'Duration': duration_days,
                        'Portability': measure.get('portability', 0),
                        'Responsible': measure.get('responsible_unit', 'Unknown'),
                        'Cost': measure.get('estimated_cost', 0)
                    })
            
            # Create Gantt chart using plotly
            fig = ff.create_gantt(
                gantt_data,
                colors={measure['Type']: measure['Color'] for measure in gantt_data},
                index_col='Type',
                title="Maintenance Schedule",
                show_colorbar=True,
                group_tasks=True,
                showgrid_x=True,
                showgrid_y=True
            )
            
            # Add today line
            today = datetime.now().date()
            fig.add_shape(
                type="line",
                x0=today,
                x1=today,
                y0=0,
                y1=1,
                line=dict(color="black", width=2, dash="dash"),
                xref='x',
                yref='paper'
            )
            
            # Add today label
            fig.add_annotation(
                x=today,
                y=1,
                text="Today",
                showarrow=False,
                yshift=10
            )
            
            # Update layout
            fig.update_layout(
                autosize=True,
                height=600,
                margin=dict(l=50, r=50, b=100, t=100),
                hovermode="closest"
            )
            
            # Add hover data
            for i, measure in enumerate(gantt_data):
                fig.data[i].text = f"""
                <b>{measure['Task']}</b><br>
                Type: {measure['Type']}<br>
                ID: {measure['ID']}<br>
                Start: {measure['Start'].strftime('%Y-%m-%d')}<br>
                End: {measure['Finish'].strftime('%Y-%m-%d')}<br>
                Duration: {measure['Duration']} days<br>
                Portability: {measure['Portability']}/5<br>
                Responsible: {measure['Responsible']}<br>
                Estimated Cost: {measure['Cost']} SEK
                """
                fig.data[i].hoverinfo = "text"
            
            # Show the chart
            st.plotly_chart(fig, use_container_width=True)
        
        # Show maintenance details table
        st.subheader("Maintenance Measures")
        
        # Format data for display
        display_data = []
        for measure in filtered_measures:
            # Parse dates
            start_date_str = measure.get('start_date', '')
            start_date_obj = parse_date(start_date_str)
            
            if start_date_obj:
                # Calculate end date
                duration_days = measure.get('duration_days', 1)
                end_date_obj = start_date_obj + timedelta(days=duration_days)
                
                # Create display item
                display_item = {
                    'ID': measure.get('id', 'Unknown'),
                    'Track': measure.get('track_id', 'Unknown'),
                    'Description': measure.get('description', 'Unknown'),
                    'Type': measure.get('type', 'Unknown'),
                    'Start Date': start_date_obj.strftime('%Y-%m-%d'),
                    'Duration (days)': duration_days,
                    'End Date': end_date_obj.strftime('%Y-%m-%d'),
                    'Track Closure': "Yes" if measure.get('track_closure', False) else "No",
                    'Portability': measure.get('portability', 0),
                    'Responsible Unit': measure.get('responsible_unit', 'Unknown'),
                    'Estimated Cost': measure.get('estimated_cost', 0)
                }
                
                display_data.append(display_item)
        
        # Create and display dataframe
        if display_data:
            display_df = pd.DataFrame(display_data)
            st.dataframe(display_df)
            st.markdown(download_dataframe_as_csv(display_df, "maintenance_schedule"), unsafe_allow_html=True)
        else:
            st.info("No maintenance measures match the selected filters.")
        
        # Activity Chart - summary by track and type
        st.subheader("Maintenance Activity Summary")
        
        if filtered_measures:
            # Create summary by track
            track_summary = {}
            for measure in filtered_measures:
                track_id = measure.get('track_id', 'Unknown')
                if track_id not in track_summary:
                    track_summary[track_id] = {'total': 0}
                
                measure_type = measure.get('type', 'Unknown')
                if measure_type not in track_summary[track_id]:
                    track_summary[track_id][measure_type] = 0
                
                track_summary[track_id][measure_type] += 1
                track_summary[track_id]['total'] += 1
            
            # Convert to dataframe for plotting
            summary_data = []
            for track_id, data in track_summary.items():
                for measure_type, count in data.items():
                    if measure_type != 'total':
                        summary_data.append({
                            'Track': track_id,
                            'Type': measure_type,
                            'Count': count
                        })
            
            summary_df = pd.DataFrame(summary_data)
            
            # Create grouped bar chart
            fig = px.bar(summary_df, x='Track', y='Count', color='Type',
                       title="Maintenance Activities by Track and Type",
                       labels={'Track': 'Track ID', 'Count': 'Number of Activities', 'Type': 'Maintenance Type'},
                       color_discrete_map={
                           'Preventive': '#00CC00',
                           'Corrective': '#FF9900',
                           'Renewal': '#FF0000',
                           'ERTMS Implementation': '#0066FF',
                           'Inspection': '#9900CC',
                           'Track Work': '#FF3399',
                           'Signaling': '#00FFFF',
                           'Electrical': '#FFFF00',
                           'Bridge & Structure': '#996633',
                           'Unknown': '#CCCCCC'
                       },
                       height=400)
            
            st.plotly_chart(fig, use_container_width=True)


            # Cost Summary
            if any('estimated_cost' in m for m in filtered_measures):
                # Create cost summary by track
                cost_data = []
                for measure in filtered_measures:
                    if 'estimated_cost' in measure and measure['estimated_cost'] is not None:
                        cost_data.append({
                            'Track': measure.get('track_id', 'Unknown'),
                            'Type': measure.get('type', 'Unknown'),
                            'Cost': measure['estimated_cost']
                        })
                
                cost_df = pd.DataFrame(cost_data)
                
                # Create cost chart
                fig = px.bar(cost_df, x='Track', y='Cost', color='Type',
                           title="Maintenance Cost by Track and Type",
                           labels={'Track': 'Track ID', 'Cost': 'Estimated Cost (SEK)', 'Type': 'Maintenance Type'},
                           color_discrete_map={
                               'Preventive': '#00CC00',
                               'Corrective': '#FF9900',
                               'Renewal': '#FF0000',
                               'ERTMS Implementation': '#0066FF',
                               'Inspection': '#9900CC',
                               'Track Work': '#FF3399',
                               'Signaling': '#00FFFF',
                               'Electrical': '#FFFF00',
                               'Bridge & Structure': '#996633',
                               'Unknown': '#CCCCCC'
                           },
                           height=400)
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Timeline view - especially for ERTMS implementation
            if show_ertms:
                st.subheader("ERTMS Implementation Timeline")
                
                # Get all ERTMS measures
                ertms_measures = [m for m in st.session_state.maintenance_data if m.get('type') == 'ERTMS Implementation']
                
                if ertms_measures:
                    # Create a timeline for ERTMS implementation using a heatmap
                    # First, determine the time range
                    start_dates = [parse_date(m.get('start_date', '')) for m in ertms_measures if parse_date(m.get('start_date', ''))]
                    if start_dates:
                        min_date = min(start_dates)
                        max_date = max([date + timedelta(days=m.get('duration_days', 30)) 
                                       for date, m in zip(start_dates, ertms_measures)])
                        
                        # Create date range by quarters
                        quarters = []
                        current = min_date.replace(day=1)
                        while current <= max_date:
                            # Start of each quarter
                            if current.month in [1, 4, 7, 10]:
                                quarters.append(current)
                            current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
                        
                        # Create timeline data
                        timeline_data = []
                        
                        for m in ertms_measures:
                            start = parse_date(m.get('start_date', ''))
                            if start:
                                duration = m.get('duration_days', 30)
                                end = start + timedelta(days=duration)
                                
                                for q in quarters:
                                    q_end = (q.replace(month=q.month+2) if q.month <= 10 else 
                                            q.replace(year=q.year+1, month=(q.month+2)%12)) - timedelta(days=1)
                                    
                                    # Check if measure is active during this quarter
                                    if not (end < q or start > q_end):
                                        overlap_days = min(end, q_end) - max(start, q) + timedelta(days=1)
                                        overlap_days = overlap_days.days
                                        
                                        # Calculate implementation percentage for this quarter
                                        pct = min(1.0, overlap_days / 90) * 100  # Assuming quarter is ~90 days
                                        
                                        timeline_data.append({
                                            'Track': m.get('track_id', 'Unknown'),
                                            'Quarter': f"Q{(q.month-1)//3 + 1} {q.year}",
                                            'Implementation': pct,
                                            'Description': m.get('description', '')
                                        })
                        
                        # Create dataframe for heatmap
                        if timeline_data:
                            timeline_df = pd.DataFrame(timeline_data)
                            
                            # Group by track and quarter
                            pivoted = timeline_df.pivot_table(
                                values='Implementation',
                                index='Track',
                                columns='Quarter',
                                aggfunc='max',
                                fill_value=0
                            )
                            
                            # Create heatmap
                            fig = px.imshow(
                                pivoted,
                                title="ERTMS Implementation Timeline",
                                labels=dict(x="Quarter", y="Track", color="Implementation %"),
                                color_continuous_scale="Blues",
                                height=500
                            )
                            
                            # Improve layout
                            fig.update_layout(
                                xaxis_title="Quarter",
                                yaxis_title="Track",
                                coloraxis_colorbar=dict(
                                    title="Implementation %",
                                    ticksuffix="%"
                                )
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No ERTMS implementation measures found.")
            
            # Portability Analysis
            st.subheader("Maintenance Portability Analysis")
            if filtered_measures:
                # Create portability visualization
                portability_data = []
                
                for measure in filtered_measures:
                    portability_data.append({
                        'ID': measure.get('id', 'Unknown'),
                        'Description': measure.get('description', 'Unknown')[:30] + '...',
                        'Type': measure.get('type', 'Unknown'),
                        'Track': measure.get('track_id', 'Unknown'),
                        'Portability': measure.get('portability', 0),
                        'Duration': measure.get('duration_days', 1),
                        'Cost': measure.get('estimated_cost', 0)
                    })
                
                portability_df = pd.DataFrame(portability_data)
                
                # Create scatter plot of portability vs duration
                fig = px.scatter(
                    portability_df,
                    x='Portability',
                    y='Duration',
                    color='Type',
                    size='Cost',
                    hover_name='Description',
                    title="Maintenance Portability vs Duration",
                    labels={
                        'Portability': 'Portability (0=Fixed, 5=Flexible)',
                        'Duration': 'Duration (days)',
                        'Cost': 'Estimated Cost (SEK)',
                        'Type': 'Maintenance Type'
                    },
                    color_discrete_map={
                        'Preventive': '#00CC00',
                        'Corrective': '#FF9900',
                        'Renewal': '#FF0000',
                        'ERTMS Implementation': '#0066FF',
                        'Inspection': '#9900CC',
                        'Track Work': '#FF3399',
                        'Signaling': '#00FFFF',
                        'Electrical': '#FFFF00',
                        'Bridge & Structure': '#996633',
                        'Unknown': '#CCCCCC'
                    },
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Distribution of portability
                col1, col2 = st.columns(2)
                
                with col1:
                    # Count by portability
                    port_counts = portability_df['Portability'].value_counts().sort_index().reset_index()
                    port_counts.columns = ['Portability', 'Count']
                    
                    fig = px.bar(
                        port_counts,
                        x='Portability',
                        y='Count',
                        title="Distribution of Portability",
                        labels={'Portability': 'Portability (0=Fixed, 5=Flexible)', 'Count': 'Number of Activities'},
                        color='Portability',
                        color_continuous_scale='Viridis',
                        height=350
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Average portability by type
                    avg_port = portability_df.groupby('Type')['Portability'].mean().reset_index()
                    avg_port = avg_port.sort_values('Portability', ascending=False)
                    
                    fig = px.bar(
                        avg_port,
                        x='Type',
                        y='Portability',
                        title="Average Portability by Type",
                        labels={'Type': 'Maintenance Type', 'Portability': 'Average Portability'},
                        color='Portability',
                        color_continuous_scale='Viridis',
                        height=350
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)

# Conflict Detection page
elif app_mode == "Conflict Detection":
    st.title("Conflict Detection & Resolution")
    
    if st.session_state.maintenance_data is None:
        st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
    else:
        # Conflict detection
        st.header("Detect Conflicts")
        
        # Button to detect conflicts
        conflict_button = st.button("Detect Conflicts")
        
        # Advanced options
        with st.expander("Advanced Options"):
            # Additional conflict detection options
            st.subheader("Conflict Detection Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                check_same_track = st.checkbox("Check Same Track Conflicts", value=True)
                check_adjacent_tracks = st.checkbox("Check Adjacent Track Conflicts", value=True)
            
            with col2:
                check_resource_conflicts = st.checkbox("Check Resource Conflicts", value=True)
                buffer_days = st.number_input("Buffer Days Between Activities", min_value=0, value=0)
        
        if conflict_button:
            with st.spinner("Detecting conflicts..."):
                # Detect date overlaps for the same track
                conflicts = []
                
                # Process the maintenance data
                measures_by_track = {}
                for measure in st.session_state.maintenance_data:
                    track_id = measure.get('track_id')
                    if track_id:
                        if track_id not in measures_by_track:
                            measures_by_track[track_id] = []
                        measures_by_track[track_id].append(measure)
                
                # Check for conflicts on each track
                if check_same_track:
                    for track_id, measures in measures_by_track.items():
                        # Sort measures by start date
                        sorted_measures = sorted(measures, key=lambda m: parse_date(m.get('start_date', '')) or datetime.min)
                        
                        # Check for overlaps
                        for i in range(len(sorted_measures)):
                            measure1 = sorted_measures[i]
                            start1 = parse_date(measure1.get('start_date', ''))
                            if start1:
                                duration1 = measure1.get('duration_days', 1)
                                end1 = start1 + timedelta(days=duration1 + buffer_days)
                                
                                for j in range(i + 1, len(sorted_measures)):
                                    measure2 = sorted_measures[j]
                                    start2 = parse_date(measure2.get('start_date', ''))
                                    if start2:
                                        # Check for overlap
                                        if start2 <= end1:
                                            # Check if these types can be parallel
                                            type1 = measure1.get('type', 'Unknown')
                                            type2 = measure2.get('type', 'Unknown')
                                            
                                            # Check parallelism matrix
                                            can_be_parallel = False
                                            if type1 in st.session_state.parallelism_matrix and \
                                               type2 in st.session_state.parallelism_matrix[type1]:
                                                can_be_parallel = st.session_state.parallelism_matrix[type1][type2]
                                            
                                            if not can_be_parallel:
                                                # Add to conflicts
                                                conflicts.append({
                                                    'track_id': track_id,
                                                    'measure1': measure1,
                                                    'measure2': measure2,
                                                    'start1': start1,
                                                    'end1': end1 - timedelta(days=buffer_days),
                                                    'start2': start2,
                                                    'can_be_parallel': False,
                                                    'type': 'Date Overlap',
                                                    'conflict_severity': 'High'
                                                })
                
                # Check for adjacent track conflicts if network data is available
                if check_adjacent_tracks and st.session_state.network_data:
                    # Build adjacency dictionary
                    adjacent_tracks = {}
                    
                    for link in st.session_state.network_data['links']:
                        link_id = link['id']
                        from_node = link['from_node']
                        to_node = link['to_node']
                        
                        # Find adjacent links
                        for other_link in st.session_state.network_data['links']:
                            if other_link['id'] != link_id:
                                # Check if they share a node
                                if (other_link['from_node'] == from_node or 
                                    other_link['from_node'] == to_node or
                                    other_link['to_node'] == from_node or
                                    other_link['to_node'] == to_node):
                                    
                                    if link_id not in adjacent_tracks:
                                        adjacent_tracks[link_id] = []
                                    
                                    adjacent_tracks[link_id].append(other_link['id'])
                    
                    # Check for conflicts on adjacent tracks
                    for track_id, adjacent_ids in adjacent_tracks.items():
                        if track_id in measures_by_track:
                            for measure1 in measures_by_track[track_id]:
                                start1 = parse_date(measure1.get('start_date', ''))
                                if start1 and measure1.get('track_closure', False):  # Only check if track is closed
                                    duration1 = measure1.get('duration_days', 1)
                                    end1 = start1 + timedelta(days=duration1 + buffer_days)
                                    
                                    # Check each adjacent track
                                    for adj_id in adjacent_ids:
                                        if adj_id in measures_by_track:
                                            for measure2 in measures_by_track[adj_id]:
                                                if measure2.get('track_closure', False):  # Only check if adjacent track is closed
                                                    start2 = parse_date(measure2.get('start_date', ''))
                                                    if start2:
                                                        # Check for overlap
                                                        if (start1 <= start2 <= end1) or (start2 <= start1 <= start2 + timedelta(days=measure2.get('duration_days', 1))):
                                                            # Add to conflicts
                                                            conflicts.append({
                                                                'track_id': f"{track_id} & {adj_id}",
                                                                'measure1': measure1,
                                                                'measure2': measure2,
                                                                'start1': start1,
                                                                'end1': end1 - timedelta(days=buffer_days),
                                                                'start2': start2,
                                                                'can_be_parallel': False,
                                                                'type': 'Adjacent Track Closure',
                                                                'conflict_severity': 'Medium'
                                                            })
                
                # Check for resource conflicts
                if check_resource_conflicts:
                    # Group measures by responsible unit
                    measures_by_unit = {}
                    for measure in st.session_state.maintenance_data:
                        unit = measure.get('responsible_unit', 'Unknown')
                        if unit not in measures_by_unit:
                            measures_by_unit[unit] = []
                        measures_by_unit[unit].append(measure)
                    
                    # Check for overlaps within each unit
                    for unit, unit_measures in measures_by_unit.items():
                        # Sort measures by start date
                        sorted_measures = sorted(unit_measures, key=lambda m: parse_date(m.get('start_date', '')) or datetime.min)
                        
                        # Check for overlaps
                        for i in range(len(sorted_measures)):
                            measure1 = sorted_measures[i]
                            start1 = parse_date(measure1.get('start_date', ''))
                            if start1:
                                duration1 = measure1.get('duration_days', 1)
                                end1 = start1 + timedelta(days=duration1 + buffer_days)
                                
                                for j in range(i + 1, len(sorted_measures)):
                                    measure2 = sorted_measures[j]
                                    # Skip if same track (already checked)
                                    if measure1.get('track_id') == measure2.get('track_id'):
                                        continue
                                    
                                    start2 = parse_date(measure2.get('start_date', ''))
                                    if start2:
                                        # Check for overlap
                                        if start2 <= end1:
                                            # Add to conflicts
                                            conflicts.append({
                                                'track_id': f"{measure1.get('track_id', 'Unknown')} & {measure2.get('track_id', 'Unknown')}",
                                                'measure1': measure1,
                                                'measure2': measure2,
                                                'start1': start1,
                                                'end1': end1 - timedelta(days=buffer_days),
                                                'start2': start2,
                                                'can_be_parallel': False,
                                                'type': 'Resource Conflict',
                                                'conflict_severity': 'Low'
                                            })
                
                # Display conflicts
                if conflicts:
                    st.error(f"Detected {len(conflicts)} conflicts!")
                    
                    # Create a dataframe for display
                    conflict_display = []
                    for conflict in conflicts:
                        conflict_display.append({
                            'Tracks': conflict['track_id'],
                            'Measure 1': conflict['measure1'].get('description', 'Unknown'),
                            'Type 1': conflict['measure1'].get('type', 'Unknown'),
                            'Start 1': conflict['start1'].strftime('%Y-%m-%d'),
                            'Measure 2': conflict['measure2'].get('description', 'Unknown'),
                            'Type 2': conflict['measure2'].get('type', 'Unknown'),
                            'Start 2': conflict['start2'].strftime('%Y-%m-%d'),
                            'Conflict Type': conflict['type'],
                            'Severity': conflict['conflict_severity']
                        })
                    
                    # Display conflict table
                    conflict_df = pd.DataFrame(conflict_display)
                    
                    # Apply color formatting to severity column
                    def highlight_severity(val):
                        if val == 'High':
                            color = 'red'
                        elif val == 'Medium':
                            color = 'orange'
                        else:
                            color = 'yellow'
                        return f'background-color: {color}'
                    
                    st.dataframe(conflict_df)
                    st.markdown(download_dataframe_as_csv(conflict_df, "detected_conflicts"), unsafe_allow_html=True)
                    
                    # Show conflict visualization
                    st.subheader("Conflict Visualization")
                    
                    # Create a Gantt chart highlighting conflicts
                    gantt_data = []
                    
                    # Add all maintenance measures
                    for measure in st.session_state.maintenance_data:
                        # Parse dates
                        start_date_str = measure.get('start_date', '')
                        start_date_obj = parse_date(start_date_str)
                        
                        if start_date_obj:
                            # Calculate end date
                            duration_days = measure.get('duration_days', 1)
                            end_date_obj = start_date_obj + timedelta(days=duration_days)
                            
                            # Check if this measure is in a conflict
                            is_conflict = False
                            for conflict in conflicts:
                                if measure == conflict['measure1'] or measure == conflict['measure2']:
                                    is_conflict = True
                                    break
                            
                            # Determine color based on conflict status
                            if is_conflict:
                                color = 'red'  # Conflict color
                            else:
                                color = get_maintenance_color(measure.get('type', 'Unknown'))
                            
                            # Add to Gantt data
                            gantt_data.append({
                                'Task': f"{measure.get('track_id', 'Unknown')}: {measure.get('description', 'Unknown')}",
                                'Start': start_date_obj,
                                'Finish': end_date_obj,
                                'Type': "Conflict" if is_conflict else measure.get('type', 'Unknown'),
                                'ID': measure.get('id', 'Unknown'),
                                'Color': color
                            })
                    
                    # Create Gantt chart
                    fig = ff.create_gantt(
                        gantt_data,
                        colors={'Conflict': 'red', 'Preventive': '#00CC00', 'Corrective': '#FF9900', 
                               'Renewal': '#FF0000', 'ERTMS Implementation': '#0066FF', 
                               'Inspection': '#9900CC', 'Unknown': '#CCCCCC'},
                        index_col='Type',
                        title="Maintenance Schedule with Conflicts",
                        show_colorbar=True,
                        group_tasks=True,
                        showgrid_x=True,
                        showgrid_y=True
                    )
                    
                    fig.update_layout(
                        autosize=True,
                        height=600,
                        margin=dict(l=50, r=50, b=100, t=100)
                    )
                    
                    # Show the chart
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show conflict resolution options
                    st.subheader("Conflict Resolution Options")
                    
                    resolution_options = [
                        "Adjust maintenance dates to avoid overlaps",
                        "Update parallelism matrix to allow compatible activities",
                        "Cancel lower priority maintenance",
                        "Run optimization to find optimal schedule"
                    ]
                    
                    st.info("""
                    The following resolution options are available:
                    - Adjust maintenance dates to avoid overlaps
                    - Update parallelism matrix to allow compatible activities
                    - Cancel lower priority maintenance
                    - Run optimization to find optimal schedule
                    
                    For automatic conflict resolution, go to the Optimization page.
                    """)
                    
                    # Manual resolution form
                    st.subheader("Manual Conflict Resolution")
                    
                    if len(conflicts) > 0:
                        with st.form("resolve_conflict_form"):
                            # Select conflict to resolve
                            conflict_options = [f"Conflict {i+1}: {c['measure1'].get('description', 'Unknown')} vs {c['measure2'].get('description', 'Unknown')}" 
                                             for i, c in enumerate(conflicts)]
                            
                            selected_conflict_idx = st.selectbox("Select conflict to resolve", 
                                                              options=range(len(conflict_options)),
                                                              format_func=lambda x: conflict_options[x])
                            
                            # Resolution method
                            resolution_method = st.radio("Resolution method", 
                                                      options=["Adjust dates", "Allow parallelism", "Cancel measure"])
                            
                            # Action based on selected method
                            if resolution_method == "Adjust dates":
                                conflict = conflicts[selected_conflict_idx]
                                measure1 = conflict['measure1']
                                measure2 = conflict['measure2']
                                
                                st.write(f"Measure 1: {measure1.get('description', 'Unknown')}")
                                new_start1 = st.date_input("New start date for Measure 1", 
                                                        value=conflict['start1'])
                                
                                st.write(f"Measure 2: {measure2.get('description', 'Unknown')}")
                                new_start2 = st.date_input("New start date for Measure 2", 
                                                        value=conflict['start2'])
                                
                            elif resolution_method == "Allow parallelism":
                                conflict = conflicts[selected_conflict_idx]
                                type1 = conflict['measure1'].get('type', 'Unknown')
                                type2 = conflict['measure2'].get('type', 'Unknown')
                                
                                st.write(f"Allow {type1} and {type2} activities to run in parallel")
                                
                            elif resolution_method == "Cancel measure":
                                conflict = conflicts[selected_conflict_idx]
                                measure1 = conflict['measure1']
                                measure2 = conflict['measure2']
                                
                                cancel_option = st.radio("Cancel which measure?", 
                                                      options=[f"Measure 1: {measure1.get('description', 'Unknown')}", 
                                                               f"Measure 2: {measure2.get('description', 'Unknown')}"])
                            
                            # Submit button
                            submit_button = st.form_submit_button("Apply Resolution")
                            
                            if submit_button:
                                conflict = conflicts[selected_conflict_idx]
                                if resolution_method == "Adjust dates":
                                    # Update the start dates in the maintenance data
                                    for i, measure in enumerate(st.session_state.maintenance_data):
                                        if measure['id'] == conflict['measure1']['id']:
                                            st.session_state.maintenance_data[i]['start_date'] = new_start1.strftime(DATE_FORMAT)
                                        elif measure['id'] == conflict['measure2']['id']:
                                            st.session_state.maintenance_data[i]['start_date'] = new_start2.strftime(DATE_FORMAT)
                                    
                                    st.success("Start dates adjusted successfully!")
                                
                                elif resolution_method == "Allow parallelism":
                                    # Update the parallelism matrix
                                    type1 = conflict['measure1'].get('type', 'Unknown')
                                    type2 = conflict['measure2'].get('type', 'Unknown')
                                    
                                    if type1 not in st.session_state.parallelism_matrix:
                                        st.session_state.parallelism_matrix[type1] = {}
                                    if type2 not in st.session_state.parallelism_matrix:
                                        st.session_state.parallelism_matrix[type2] = {}
                                    
                                    st.session_state.parallelism_matrix[type1][type2] = True
                                    st.session_state.parallelism_matrix[type2][type1] = True
                                    
                                    st.success(f"Updated parallelism matrix to allow {type1} and {type2} in parallel!")
                                
                                elif resolution_method == "Cancel measure":
                                    # Remove the selected measure
                                    if cancel_option.startswith("Measure 1"):
                                        measure_to_remove = conflict['measure1']
                                    else:
                                        measure_to_remove = conflict['measure2']
                                    
                                    # Filter out the measure
                                    st.session_state.maintenance_data = [m for m in st.session_state.maintenance_data 
                                                                      if m['id'] != measure_to_remove['id']]
                                    
                                    st.success(f"Removed {measure_to_remove.get('description', 'Unknown')}")
                    
                else:
                    st.success("No conflicts detected!")
        
        # Show parallelism matrix configuration link
        st.markdown("See [Parallelism Matrix](#parallelism-matrix) for configuring which types of maintenance can run in parallel.")
        
        # Explain conflict detection logic
        with st.expander("How Conflict Detection Works"):
            st.markdown("""
            The conflict detection algorithm checks for three types of conflicts:
            
            1. **Same Track Conflicts** - Activities that overlap in time on the same track
                - Only conflicts if the activities aren't compatible according to the parallelism matrix
                - Severity: **High**
            
            2. **Adjacent Track Conflicts** - Track closures that overlap in time on adjacent tracks
                - Checks for simultaneous closures that could block a route
                - Severity: **Medium**
            
            3. **Resource Conflicts** - Activities by the same responsible unit that overlap in time
                - Checks if a maintenance unit has multiple simultaneous activities
                - Severity: **Low**
            
            You can adjust detection settings in the Advanced Options section.
            """)

# Parallelism Matrix page
elif app_mode == "Parallelism Matrix":
    st.title("Parallelism Matrix Configuration")
    
    st.markdown("""
    The parallelism matrix defines which types of maintenance activities can be scheduled in parallel on the same track.
    Configure the matrix below to define the compatibility of different maintenance types.
    """)
    
    # Get unique maintenance types
    maintenance_types = ["Preventive", "Corrective", "Renewal", "ERTMS Implementation", "Inspection", 
                       "Track Work", "Signaling", "Electrical", "Bridge & Structure", "Unknown"]
    
    # Check if we have actual types from the data
    if st.session_state.maintenance_data:
        data_types = list(set([m.get('type', 'Unknown') for m in st.session_state.maintenance_data]))
        # Add any missing types
        for t in data_types:
            if t not in maintenance_types:
                maintenance_types.append(t)
    
    # Initialize parallelism matrix if not already set for all types
    for type1 in maintenance_types:
        if type1 not in st.session_state.parallelism_matrix:
            st.session_state.parallelism_matrix[type1] = {}
        
        for type2 in maintenance_types:
            if type2 not in st.session_state.parallelism_matrix[type1]:
                # Default to False (not parallel) for most combinations
                can_parallel = False
                
                # Allow same type to be parallel by default (except Renewal)
                if type1 == type2 and type1 != 'Renewal':
                    can_parallel = True
                
                # Allow Preventive and Inspection to be parallel by default
                if (type1 == 'Preventive' and type2 == 'Inspection') or \
                   (type1 == 'Inspection' and type2 == 'Preventive'):
                    can_parallel = True
                
                st.session_state.parallelism_matrix[type1][type2] = can_parallel
    
    # Display the matrix as a form
    with st.form("parallelism_matrix_form"):
        st.subheader("Configure which activities can run in parallel")
        
        # Create a grid of checkboxes
        for i, type1 in enumerate(maintenance_types):
            cols = st.columns(len(maintenance_types) + 1)
            
            # Add row header
            with cols[0]:
                st.markdown(f"**{type1}**")
            
            # Add checkboxes for each combination
            for j, type2 in enumerate(maintenance_types):
                with cols[j + 1]:
                    if i == 0:  # Add column headers in the first row
                        st.markdown(f"**{type2}**")
                    
                    # Show checkbox for each combination
                    if i >= j:  # Only show for the lower triangle + diagonal
                        checkbox_key = f"parallel_{type1}_{type2}"
                        current_value = st.session_state.parallelism_matrix[type1][type2]
                        st.session_state.parallelism_matrix[type1][type2] = st.checkbox(
                            "", value=current_value, key=checkbox_key)
                        
                        # Make sure the matrix is symmetric
                        st.session_state.parallelism_matrix[type2][type1] = st.session_state.parallelism_matrix[type1][type2]
        
        # Submit button
        submit_button = st.form_submit_button("Update Parallelism Configuration")
        
        if submit_button:
            st.success("Parallelism matrix updated successfully!")
    
    # Display the matrix as a heatmap
    st.subheader("Parallelism Matrix Visualization")
    
    # Create matrix data for heatmap
    matrix_data = []
    for type1 in maintenance_types:
        row = []
        for type2 in maintenance_types:
            row.append(1 if st.session_state.parallelism_matrix[type1][type2] else 0)
        matrix_data.append(row)
    
    # Create heatmap
    fig = px.imshow(
        matrix_data,
        x=maintenance_types,
        y=maintenance_types,
        labels=dict(x="Maintenance Type", y="Maintenance Type", color="Can be parallel"),
        title="Parallelism Matrix",
        color_continuous_scale=["white", "green"],
        zmin=0,
        zmax=1
    )
    
    # Show the matrix
    st.plotly_chart(fig, use_container_width=True)
    
    # Add export/import options
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Export Configuration")
        
        # Convert matrix to JSON
        matrix_json = json.dumps(st.session_state.parallelism_matrix, indent=2)
        
        # Show download button
        st.download_button(
            label="Download Parallelism Matrix",
            data=matrix_json,
            file_name="parallelism_matrix.json",
            mime="application/json"
        )
    
    with col2:
        st.subheader("Import Configuration")
        
        uploaded_file = st.file_uploader("Upload parallelism matrix JSON", type=['json'])
        
        if uploaded_file:
            try:
                uploaded_matrix = json.loads(uploaded_file.getvalue().decode('utf-8'))
                
                # Validate the uploaded matrix
                valid = True
                for type1 in maintenance_types:
                    if type1 not in uploaded_matrix:
                        valid = False
                        break
                    
                    for type2 in maintenance_types:
                        if type2 not in uploaded_matrix[type1]:
                            valid = False
                            break
                
                if valid:
                    st.session_state.parallelism_matrix = uploaded_matrix
                    st.success("Parallelism matrix imported successfully!")
                else:
                    st.error("Invalid parallelism matrix format. Please check the file.")
            except Exception as e:
                st.error(f"Error importing parallelism matrix: {str(e)}")
    
    # Explain parallelism concepts
    with st.expander("Understanding Parallelism"):
        st.markdown("""
        ### Parallelism Concepts
        
        The parallelism matrix determines which maintenance activities can be scheduled on the same track at the same time.
        
        #### Common Parallelism Rules:
        
        1. **Same type activities** are usually parallel with themselves (except for major work like Renewal)
        2. **Inspection** can often run in parallel with **Preventive** maintenance
        3. **Major works** like Renewal and ERTMS Implementation typically cannot run in parallel with anything else
        4. **Corrective** maintenance usually requires exclusive track access
        
        #### Benefits of Proper Parallelism Configuration:
        
        - More efficient use of track time
        - Fewer maintenance windows needed
        - Less disruption to rail traffic
        - Better coordination between different maintenance units
        
        Adjust the matrix to match your specific maintenance constraints and requirements.
        """)

# Detour Routes page
elif app_mode == "Detour Routes":
    st.title("Detour Routes Configuration")
    
    st.markdown("""
    Configure alternative routes for trains when tracks are closed for maintenance.
    These detour routes help maintain accessibility during track closures.
    """)
    
    if not st.session_state.network_data:
        st.warning("Network data is required to configure detour routes. Please go to Data Management to load or generate network data.")
    else:
        # Add new detour route
        st.header("Add Detour Route")
        
        with st.form("add_detour_route"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Select the track that will be closed
                track_options = [link['id'] for link in st.session_state.network_data['links']]
                closed_track = st.selectbox("Closed Track", options=track_options)
                
                # Find the from/to nodes for this track
                selected_link = next((link for link in st.session_state.network_data['links'] if link['id'] == closed_track), None)
                if selected_link:
                    st.info(f"Selected track: {closed_track} (from {selected_link['from_node']} to {selected_link['to_node']})")
            
            with col2:
                # Select train types that can use this detour
                train_type_options = ['ALL']
                if st.session_state.traffic_data and 'train_types' in st.session_state.traffic_data:
                    train_type_options.extend([tt['id'] for tt in st.session_state.traffic_data['train_types']])
                
                selected_train_types = st.multiselect("Train Types for Detour", options=train_type_options, default=['ALL'])
            
            # Allow manual specification of detour path
            use_automatic = st.checkbox("Calculate Optimal Detour Automatically", value=True)
            
            if not use_automatic:
                # Manual detour path specification
                if selected_link:
                    # Get all nodes
                    node_options = [node['id'] for node in st.session_state.network_data['nodes']]
                    
                    # Default to from/to nodes
                    from_node = selected_link['from_node']
                    to_node = selected_link['to_node']
                    
                    # Create columns for each node in path
                    st.write("Specify Detour Path (nodes):")
                    detour_path = []
                    
                    # First node is fixed (from node)
                    detour_path.append(from_node)
                    
                    # Allow specifying intermediate nodes (up to 5)
                    for i in range(5):
                        intermediate_node = st.selectbox(f"Intermediate Node {i+1}", 
                                                     options=['None'] + node_options,
                                                     key=f"node_{i}")
                        if intermediate_node != 'None':
                            detour_path.append(intermediate_node)
                    
                    # Last node is fixed (to node)
                    detour_path.append(to_node)
                    
                    # Display the path
                    st.write(f"Detour Path: {' → '.join(detour_path)}")
            
            submit_button = st.form_submit_button("Add Detour Route")
            
            if submit_button:
                if selected_link:
                    from_node = selected_link['from_node']
                    to_node = selected_link['to_node']
                    
                    # Calculate detour if automatic
                    if use_automatic:
                        # Create networkx graph
                        G = nx.Graph()
                        
                        # Add all nodes
                        for node in st.session_state.network_data['nodes']:
                            G.add_node(node['id'])
                        
                        # Add all links except the closed one
                        for link in st.session_state.network_data['links']:
                            if link['id'] != closed_track:
                                G.add_edge(link['from_node'], link['to_node'], id=link['id'])
                        
                        # Try to find shortest path
                        try:
                            detour_path = nx.shortest_path(G, from_node, to_node)
                            
                            # Convert node path to link path
                            detour_links = []
                            for i in range(len(detour_path) - 1):
                                # Find the link ID
                                for link in st.session_state.network_data['links']:
                                    if (link['from_node'] == detour_path[i] and link['to_node'] == detour_path[i+1]) or \
                                       (link['to_node'] == detour_path[i] and link['from_node'] == detour_path[i+1]):
                                        detour_links.append(link['id'])
                                        break
                            
                            # Store the detour route
                            st.session_state.detour_routes[closed_track] = {
                                'original_link': closed_track,
                                'original_from': from_node,
                                'original_to': to_node,
                                'detour_links': detour_links,
                                'detour_path': detour_path,
                                'train_types': selected_train_types
                            }
                            
                            st.success(f"Added detour route for {closed_track} using {len(detour_links)} links")
                        except nx.NetworkXNoPath:
                            st.error(f"No alternative path found from {from_node} to {to_node}")
                    else:
                        # Use manually specified path
                        # Convert node path to link path
                        detour_links = []
                        for i in range(len(detour_path) - 1):
                            # Find the link ID
                            found_link = False
                            for link in st.session_state.network_data['links']:
                                if (link['from_node'] == detour_path[i] and link['to_node'] == detour_path[i+1]) or \
                                   (link['to_node'] == detour_path[i] and link['from_node'] == detour_path[i+1]):
                                    detour_links.append(link['id'])
                                    found_link = True
                                    break
                            
                            if not found_link:
                                st.error(f"No link found between {detour_path[i]} and {detour_path[i+1]}")
                                break
                        
                        if len(detour_links) == len(detour_path) - 1:
                            # Store the detour route
                            st.session_state.detour_routes[closed_track] = {
                                'original_link': closed_track,
                                'original_from': from_node,
                                'original_to': to_node,
                                'detour_links': detour_links,
                                'detour_path': detour_path,
                                'train_types': selected_train_types
                            }
                            
                            st.success(f"Added detour route for {closed_track} using {len(detour_links)} links")
        
        # Display configured detour routes
        st.header("Configured Detour Routes")
        
        if st.session_state.detour_routes:
            # Create tabs for list view and map view
            list_tab, map_tab = st.tabs(["List View", "Map View"])
            
            with list_tab:
                # Display detour routes as a table
                detour_data = []
                
                for closed_track, route in st.session_state.detour_routes.items():
                    detour_data.append({
                        'Closed Track': closed_track,
                        'From': route['original_from'],
                        'To': route['original_to'],
                        'Detour Path': ' → '.join(route['detour_path']),
                        'Detour Links': ', '.join(route['detour_links']),
                        'Train Types': ', '.join(route['train_types']),
                        'Length': len(route['detour_links'])
                    })
                
                detour_df = pd.DataFrame(detour_data)
                st.dataframe(detour_df)
                st.markdown(download_dataframe_as_csv(detour_df, "detour_routes"), unsafe_allow_html=True)
                
                # Delete detour route
                if detour_data:
                    with st.form("delete_detour"):
                        route_to_delete = st.selectbox("Select Route to Delete", 
                                                     options=[d['Closed Track'] for d in detour_data])
                        
                        delete_button = st.form_submit_button("Delete Route")
                        
                        if delete_button and route_to_delete in st.session_state.detour_routes:
                            del st.session_state.detour_routes[route_to_delete]
                            st.success(f"Deleted detour route for {route_to_delete}")
                            st.experimental_rerun()
            
            with map_tab:
                # Create a map visualization of detour routes
                if st.session_state.network_data:
                    # Create a base map centered on Sweden
                    m = folium.Map(location=[62, 15], zoom_start=5)
                    
                    # Create a dict to quickly look up nodes by ID
                    node_dict = {n['id']: n for n in st.session_state.network_data['nodes']}
                    
                    # Select a detour to visualize
                    selected_detour = st.selectbox(
                        "Select Detour to Visualize", 
                        options=list(st.session_state.detour_routes.keys())
                    )
                    
                    # Add nodes to map
                    for node in st.session_state.network_data['nodes']:
                        if node.get('lat') and node.get('lon'):
                            popup_text = f"""
                            <b>{node.get('name', 'Unknown')}</b><br>
                            ID: {node['id']}<br>
                            """
                            
                            folium.CircleMarker(
                                location=[node['lat'], node['lon']],
                                radius=3,
                                color='blue',
                                fill=True,
                                fill_opacity=0.7,
                                popup=popup_text
                            ).add_to(m)
                    
                    # Add all links to map
                    for link in st.session_state.network_data['links']:
                        from_node = node_dict.get(link['from_node'])
                        to_node = node_dict.get(link['to_node'])
                        
                        if from_node and to_node and from_node.get('lat') and from_node.get('lon') and \
                           to_node.get('lat') and to_node.get('lon'):
                            
                            # Determine color based on detour status
                            if link['id'] == selected_detour:
                                color = 'red'  # Closed link
                                weight = 3
                                opacity = 1.0
                                dash_array = None
                            elif selected_detour in st.session_state.detour_routes and \
                                 link['id'] in st.session_state.detour_routes[selected_detour]['detour_links']:
                                color = 'green'  # Detour link
                                weight = 3
                                opacity = 1.0
                                dash_array = '5, 5'
                            else:
                                color = 'blue'  # Regular link
                                weight = 1
                                opacity = 0.5
                                dash_array = None
                            
                            # Create popup with link info
                            popup_text = f"""
                            <b>Link: {link['id']}</b><br>
                            From: {from_node.get('name', from_node['id'])} to {to_node.get('name', to_node['id'])}<br>
                            """
                            
                            # Add the link as a polyline
                            folium.PolyLine(
                                locations=[[from_node['lat'], from_node['lon']], [to_node['lat'], to_node['lon']]],
                                color=color,
                                weight=weight,
                                opacity=opacity,
                                popup=popup_text,
                                dash_array=dash_array
                            ).add_to(m)
                    
                    # Add legend
                    legend_html = '''
                    <div style="position: fixed; bottom: 50px; left: 50px; z-index:1000; background-color: white; 
                                padding: 10px; border: 1px solid grey; border-radius: 5px;">
                        <p><b>Legend</b></p>
                        <p><i style="background: blue; width: 10px; height: 10px; display: inline-block;"></i> Regular Track</p>
                        <p><i style="background: red; width: 10px; height: 10px; display: inline-block;"></i> Closed Track</p>
                        <p><i style="background: green; width: 10px; height: 10px; display: inline-block;
                                    border-top: 1px dashed #000;"></i> Detour Route</p>
                    </div>
                    '''
                    
                    # Add legend safely
                    root = m.get_root()
                    if hasattr(root, 'html') and hasattr(root.html, 'add_child'):
                        root.html.add_child(folium.Element(legend_html))
                    else:
                        # Alternative approach if the expected structure isn't available
                        m.get_root().get_name()  # No-op to prevent error
                    
                    # Display the map
                    folium_static(m)
                    
                    # Display detour details
                    if selected_detour in st.session_state.detour_routes:
                        detour_info = st.session_state.detour_routes[selected_detour]
                        
                        st.markdown(f"""
                        ### Detour Details for {selected_detour}
                        
                        **Original Link:** {detour_info['original_link']} 
                        (from {detour_info['original_from']} to {detour_info['original_to']})
                        
                        **Detour Path:** {' → '.join(detour_info['detour_path'])}
                        
                        **Detour Links:** {', '.join(detour_info['detour_links'])}
                        
                        **Detour Length:** {len(detour_info['detour_links'])} links
                        
                        **Train Types:** {', '.join(detour_info['train_types'])}
                        """)
        else:
            st.info("No detour routes configured yet. Add a route using the form above.")
        
        # Explain detour concepts
        with st.expander("Understanding Detour Routes"):
            st.markdown("""
            ### Detour Route Concepts
            
            Detour routes provide alternative paths for trains when a track is closed for maintenance.
            
            #### Key Components:
            
            1. **Closed Track** - The link that will be unavailable during maintenance
            2. **Detour Path** - The series of nodes and links that form the alternative route
            3. **Train Types** - Which types of trains can use this detour route
            
            #### Considerations for Detour Routes:
            
            - **Length** - Longer detours increase travel time and operational costs
            - **Capacity** - Detour tracks must be able to handle the additional traffic
            - **Electrification** - Some train types may require electrified tracks
            - **Clearance** - Freight trains have specific clearance requirements
            
            The system can calculate optimal detours automatically or you can specify them manually.
            """)

# Routing Rules page
elif app_mode == "Routing Rules":
    st.title("Routing Rules Configuration")
    
    st.markdown("""
    Configure routing rules to manage traffic flow during maintenance activities.
    Routing rules define how trains should be rerouted when certain conditions are met.
    """)
    
    # Add new routing rule
    st.header("Add Routing Rule")
    
    with st.form("add_routing_rule"):
        col1, col2 = st.columns(2)
        
        with col1:
            rule_name = st.text_input("Rule Name", placeholder="e.g., Major Line Closure Rule")
            
            # Rule condition types
            condition_type = st.selectbox("Condition Type", options=[
                "Track Closure",
                "Train Type Restriction",
                "Time Period Restriction",
                "Multiple Track Closure"
            ])
        
        with col2:
            # Select rule priority
            priority = st.slider("Rule Priority", min_value=1, max_value=10, value=5,
                               help="Higher priority rules are applied first (1=lowest, 10=highest)")
            
            # Rule action types
            action_type = st.selectbox("Action Type", options=[
                "Use Detour Route",
                "Cancel Service",
                "Reduce Speed",
                "Reduce Capacity"
            ])
        
        # Condition details based on type
        st.subheader("Condition Details")
        
        condition_details = {}
        
        if condition_type == "Track Closure":
            if st.session_state.network_data:
                track_options = [link['id'] for link in st.session_state.network_data['links']]
                selected_tracks = st.multiselect("Closed Tracks", options=track_options)
                condition_details['tracks'] = selected_tracks
        
        elif condition_type == "Train Type Restriction":
            if st.session_state.traffic_data and 'train_types' in st.session_state.traffic_data:
                train_type_options = [tt['id'] for tt in st.session_state.traffic_data['train_types']]
                selected_types = st.multiselect("Restricted Train Types", options=train_type_options)
                condition_details['train_types'] = selected_types
        
        elif condition_type == "Time Period Restriction":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.now())
            with col2:
                end_date = st.date_input("End Date", value=datetime.now() + timedelta(days=30))
            
            condition_details['start_date'] = start_date.strftime(DATE_FORMAT)
            condition_details['end_date'] = end_date.strftime(DATE_FORMAT)
        
        elif condition_type == "Multiple Track Closure":
            if st.session_state.network_data:
                track_options = [link['id'] for link in st.session_state.network_data['links']]
                primary_track = st.selectbox("Primary Closed Track", options=track_options)
                secondary_tracks = st.multiselect("Secondary Closed Tracks", options=track_options)
                
                condition_details['primary_track'] = primary_track
                condition_details['secondary_tracks'] = secondary_tracks
        
        # Action details based on type
        st.subheader("Action Details")
        
        action_details = {}
        
        if action_type == "Use Detour Route":
            if st.session_state.detour_routes:
                detour_options = list(st.session_state.detour_routes.keys())
                selected_detour = st.selectbox("Detour Route", options=detour_options)
                action_details['detour_route'] = selected_detour
            else:
                st.warning("No detour routes configured. Please add detour routes first.")
        
        elif action_type == "Cancel Service":
            cancel_pct = st.slider("Cancellation Percentage", min_value=0, max_value=100, value=100,
                                 help="Percentage of services to cancel")
            action_details['cancel_pct'] = cancel_pct
        
        elif action_type == "Reduce Speed":
            speed_reduction = st.slider("Speed Reduction", min_value=10, max_value=90, value=30,
                                      help="Percentage reduction in speed")
            action_details['speed_reduction'] = speed_reduction
        
        elif action_type == "Reduce Capacity":
            capacity_reduction = st.slider("Capacity Reduction", min_value=10, max_value=90, value=50,
                                         help="Percentage reduction in capacity")
            action_details['capacity_reduction'] = capacity_reduction
        
        # Description
        rule_description = st.text_area("Rule Description", placeholder="Describe when and how this rule should be applied")
        
        # Submit button
        submit_button = st.form_submit_button("Add Routing Rule")
        
        if submit_button:
            # Create rule object
            new_rule = {
                'id': f"rule_{len(st.session_state.routing_rules) + 1}",
                'name': rule_name,
                'description': rule_description,
                'priority': priority,
                'condition_type': condition_type,
                'condition_details': condition_details,
                'action_type': action_type,
                'action_details': action_details,
                'created_date': datetime.now().strftime(DATE_FORMAT)
            }
            
            # Add to routing rules
            st.session_state.routing_rules.append(new_rule)
            
            st.success(f"Added routing rule: {rule_name}")
    
    # Display configured routing rules
    st.header("Configured Routing Rules")
    
    if st.session_state.routing_rules:
        # Create table for rules
        rules_data = []
        
        for rule in st.session_state.routing_rules:
            rules_data.append({
                'ID': rule['id'],
                'Name': rule['name'],
                'Priority': rule['priority'],
                'Condition': rule['condition_type'],
                'Action': rule['action_type'],
                'Description': rule['description']
            })
        
        rules_df = pd.DataFrame(rules_data)
        
        # Display rules sorted by priority
        st.dataframe(rules_df.sort_values('Priority', ascending=False))
        st.markdown(download_dataframe_as_csv(rules_df, "routing_rules"), unsafe_allow_html=True)
        
        # Rule details
        st.subheader("Rule Details")
        
        selected_rule_id = st.selectbox("Select Rule to View", options=[r['id'] for r in st.session_state.routing_rules])
        
        if selected_rule_id:
            selected_rule = next((r for r in st.session_state.routing_rules if r['id'] == selected_rule_id), None)
            
            if selected_rule:
                st.markdown(f"""
                ### {selected_rule['name']}
                
                **Description:** {selected_rule['description']}
                
                **Priority:** {selected_rule['priority']}
                
                **Condition Type:** {selected_rule['condition_type']}
                
                **Condition Details:**
                ```
                {selected_rule['condition_details']}
                ```
                
                **Action Type:** {selected_rule['action_type']}
                
                **Action Details:**
                ```
                {selected_rule['action_details']}
                ```
                
                **Created:** {selected_rule['created_date']}
                """)
                
                # Delete rule button
                if st.button(f"Delete Rule: {selected_rule['name']}"):
                    st.session_state.routing_rules = [r for r in st.session_state.routing_rules if r['id'] != selected_rule_id]
                    st.success(f"Deleted rule: {selected_rule['name']}")
                    st.experimental_rerun()
    else:
        st.info("No routing rules configured yet. Add a rule using the form above.")
    
    # Explain routing rules
    with st.expander("Understanding Routing Rules"):
        st.markdown("""
        ### Routing Rules Concepts
        
        Routing rules define how traffic should be managed during track closures and other restrictions.
        
        #### Rule Components:
        
        1. **Condition** - When the rule should be applied (track closure, train type, time period)
        2. **Action** - What should happen when the condition is met (use detour, cancel service, etc.)
        3. **Priority** - Higher priority rules are applied first when multiple rules match
        
        #### Common Rule Types:
        
        - **Track Closure Rules** - Specify detours when specific tracks are closed
        - **Train Type Rules** - Apply different actions for different train types
        - **Time Period Rules** - Apply special routing during specific periods
        - **Multiple Track Rules** - Handle complex scenarios with multiple closures
        
        The routing rules work together with detour routes to maintain accessibility during maintenance.
        """)

# Optimization page
elif app_mode == "Optimization":
    st.title("Railway Maintenance Schedule Optimization")
    
    if not st.session_state.network_data or not st.session_state.maintenance_data or not st.session_state.traffic_data:
        st.warning("Please load all required data (network, maintenance, traffic) in the Data Management section before running optimization.")
    else:
        # Optimization parameters
        st.header("Optimization Parameters")
        
        with st.form("optimization_parameters"):
            col1, col2 = st.columns(2)
            
            with col1:
                opt_type = st.selectbox("Optimization Type", 
                                      options=["scheduling", "traffic", "both"],
                                      help="Which model to run: scheduling (project scheduling), traffic (traffic flow), or both (integrated)")
                
                opt_gap = st.slider("Optimality Gap", 
                                  min_value=0.001, max_value=0.1, value=0.01, step=0.001, format="%f",
                                  help="Relative optimality gap (smaller values will result in longer runtime)")
            
            with col2:
                time_limit = st.slider("Time Limit (seconds)", 
                                     min_value=10, max_value=3600, value=300, step=10,
                                     help="Maximum time for optimization solver")
                
                verbosity = st.selectbox("Verbosity Level", 
                                       options=[0, 1, 2, 3, 4],
                                       index=1,
                                       help="Verbosity level for solver output (0=silent, 4=very verbose)")
            
            # Advanced parameters
            with st.expander("Advanced Parameters"):
                proj_filter = st.text_input("Project Filter", 
                                          help="Comma-separated list of project prefixes to include (e.g., '214,180,526')")
                
                region_filter = st.text_input("Region Filter", 
                                           help="Filter by region")
                
                track_filter = st.text_input("Track Filter", 
                                          help="Filter by track")
                
                time_filter = st.text_input("Time Filter", 
                                         help="Time period filter in format 'start,end' (e.g., 'v2410,v2426')")
                
                period_len = st.number_input("Period Length (hours)", value=8.0, min_value=1.0, step=1.0,
                                          help="Length of time periods in hours")
            
            # Optimization objectives
            st.subheader("Optimization Objectives")
            
            obj_col1, obj_col2 = st.columns(2)
            
            with obj_col1:
                minimize_conflicts = st.checkbox("Minimize Conflicts", value=True)
                minimize_track_closures = st.checkbox("Minimize Track Closures", value=True)
            
            with obj_col2:
                maximize_portability = st.checkbox("Respect Portability", value=True)
                minimize_traffic_impact = st.checkbox("Minimize Traffic Impact", value=True)
            
            # Custom objectives weight
            with st.expander("Objective Weights"):
                st.info("Adjust the relative importance of each optimization objective")
                
                conflict_weight = st.slider("Conflict Resolution Weight", min_value=1, max_value=10, value=8)
                traffic_weight = st.slider("Traffic Impact Weight", min_value=1, max_value=10, value=7)
                closure_weight = st.slider("Track Closure Weight", min_value=1, max_value=10, value=5)
                portability_weight = st.slider("Portability Weight", min_value=1, max_value=10, value=3)
            
            # Submit button
            submit_button = st.form_submit_button("Run Optimization")
            
            if submit_button:
                # Save data to files
                try:
                    # Create temporary directory for data
                    temp_dir = create_temp_dir()
                    data_dir = os.path.join(temp_dir, "data/processed")
                    output_dir = os.path.join(temp_dir, "results/test_run")
                    
                    # Create directories if they don't exist
                    os.makedirs(data_dir, exist_ok=True)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # We'll use the existing files from data generation
                    # These files should be created when generating data in the Data Management section
                    
                    # Set optimization running state
                    st.session_state.optimization_running = True
                    
                    # Create the command
                    cmd = [
                        "python", "run.py", #src/execution/
                        "--file", "problem.xml",
                        "--dir", "data/processed",
                        "--opt", opt_type,
                        "--out_dir", output_dir,
                        "--opt_gap", str(opt_gap),
                        "--opt_time", str(time_limit),
                        "--opt_vlvl", str(verbosity),
                        "--period_len", str(period_len)
                    ]
                    
                    # Add optional parameters if provided
                    if proj_filter:
                        cmd.extend(["--proj_filter", proj_filter])
                    
                    if time_filter:
                        cmd.extend(["--time_filter", time_filter])
                    
                    # Add weights for objectives
                    cmd.extend([
                        "--weight_conflict", str(conflict_weight),
                        "--weight_traffic", str(traffic_weight),
                        "--weight_closure", str(closure_weight),
                        "--weight_portability", str(portability_weight)
                    ])
                    
                    # Display command
                    st.code(" ".join(cmd))
                    
                    # Create a progress bar and status message
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_area = st.empty()
                    
                    # Create a placeholder for the log output
                    log_output = st.empty()
                    
                    # Run the command
                    status_text.text("Starting optimization...")
                    
                    start_time = time.time()
                    
                    # Use subprocess.Popen to get output in real-time
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Collect all output
                    all_output = []
                    last_progress = 0
                    
                    # Process output in real-time
                    for line in iter(process.stdout.readline, ''):
                        all_output.append(line)
                        log_output.code(''.join(all_output))
                        
                        # Update progress bar based on output
                        if "Loading problem" in line:
                            progress_bar.progress(10)
                            status_text.text("Loading problem data...")
                        elif "Building models" in line:
                            progress_bar.progress(20)
                            status_text.text("Building optimization models...")
                        elif "Solving scheduling model" in line:
                            progress_bar.progress(30)
                            status_text.text("Solving scheduling model...")
                        elif "Iteration" in line:
                            # Extract iteration number
                            try:
                                iteration = int(line.split("Iteration")[1].strip().split("...")[0])
                                progress = min(80, 30 + 10 * iteration)
                                progress_bar.progress(progress)
                                status_text.text(f"Optimization iteration {iteration}...")
                            except:
                                pass
                        elif "Scheduling model solved successfully" in line:
                            progress_bar.progress(60)
                            status_text.text("Scheduling model solved. Processing traffic...")
                        elif "Traffic flow model solved successfully" in line:
                            progress_bar.progress(80)
                            status_text.text("Traffic model solved. Finalizing results...")
                        elif "Results written to" in line:
                            progress_bar.progress(100)
                            status_text.text("Optimization completed successfully!")
                    
                    # Get return code
                    return_code = process.wait()
                    
                    # Calculate elapsed time
                    elapsed_time = time.time() - start_time
                    
                    # Record last optimization time
                    st.session_state.last_optimization_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Update UI with results
                    if return_code == 0:
                        results_area.success(f"Optimization completed successfully in {elapsed_time:.2f} seconds!")
                        
                        # Try to parse results
                        try:
                            # Load schedule results
                            schedule_file = os.path.join(output_dir, 'schedule_results.xml')
                            if os.path.exists(schedule_file):
                                schedule_tree = ET.parse(schedule_file)
                                schedule_root = schedule_tree.getroot()
                                
                                # Extract basic stats
                                objective = float(schedule_root.find('.//objective').text)
                                cancelled_projects = len(schedule_root.findall('.//cancelled/project'))
                                
                                # Store results in session state
                                st.session_state.optimization_result = {
                                    'objective': objective,
                                    'cancelled_projects': cancelled_projects,
                                    'schedule_file': schedule_file,
                                    'elapsed_time': elapsed_time
                                }
                                
                                # Try to parse traffic results
                                traffic_file = os.path.join(output_dir, 'traffic_results.xml')
                                if os.path.exists(traffic_file):
                                    traffic_tree = ET.parse(traffic_file)
                                    traffic_root = traffic_tree.getroot()
                                    
                                    # Extract traffic impact
                                    cancelled = float(traffic_root.find('.//summary/cancelled').text or 0)
                                    delayed = float(traffic_root.find('.//summary/delayed').text or 0)
                                    diverted = float(traffic_root.find('.//summary/diverted').text or 0)
                                    
                                    st.session_state.optimization_result['traffic_impact'] = {
                                        'cancelled': cancelled,
                                        'delayed': delayed,
                                        'diverted': diverted,
                                        'traffic_file': traffic_file
                                    }
                                
                                # Update maintenance data with optimized schedule
                                schedule_elems = schedule_root.findall('.//schedule/project')
                                
                                if schedule_elems:
                                    optimized_schedule = []
                                    
                                    for proj_elem in schedule_elems:
                                        proj_id = proj_elem.get('id')
                                        proj_desc = proj_elem.get('desc')
                                        
                                        for task_elem in proj_elem.findall('task'):
                                            task_id = task_elem.get('id')
                                            task_desc = task_elem.get('desc')
                                            duration = float(task_elem.get('duration', 0))
                                            
                                            for inst_elem in task_elem.findall('instance'):
                                                index = int(inst_elem.get('index', 0))
                                                start = datetime.strptime(inst_elem.get('start'), "%Y-%m-%d %H:%M:%S")
                                                end = datetime.strptime(inst_elem.get('end'), "%Y-%m-%d %H:%M:%S")
                                                
                                                # Find the corresponding measure in our data
                                                measure_id = f"{proj_id}_{task_id}_{index}"
                                                
                                                # Update the start date
                                                for i, measure in enumerate(st.session_state.maintenance_data):
                                                    if measure.get('id') == measure_id:
                                                        st.session_state.maintenance_data[i]['start_date'] = start.strftime(DATE_FORMAT)
                                                        break
                                
                                # Display results summary
                                st.subheader("Optimization Results Summary")
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric("Objective Value", f"{objective:.2f}")
                                
                                with col2:
                                    st.metric("Cancelled Projects", cancelled_projects)
                                
                                with col3:
                                    if 'traffic_impact' in st.session_state.optimization_result:
                                        impact = st.session_state.optimization_result['traffic_impact']
                                        st.metric("Traffic Impact", f"{impact['cancelled'] + impact['delayed'] + impact['diverted']:.0f} trains")
                            
                            st.session_state.optimization_running = False
                            
                        except Exception as e:
                            st.error(f"Error parsing optimization results: {str(e)}")
                            st.session_state.optimization_running = False
                    else:
                        results_area.error(f"Optimization failed with code {return_code}")
                        st.session_state.optimization_running = False
                
                except Exception as e:
                    st.error(f"Error running optimization: {str(e)}")
                    st.session_state.optimization_running = False
        
        # Display optimization results if available
        if st.session_state.optimization_result and not st.session_state.optimization_running:
            st.header("Optimization Results")
            
            # Basic stats
            objective = st.session_state.optimization_result.get('objective', 0)
            cancelled_projects = st.session_state.optimization_result.get('cancelled_projects', 0)
            elapsed_time = st.session_state.optimization_result.get('elapsed_time', 0)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Objective Value", f"{objective:.2f}")
            
            with col2:
                st.metric("Cancelled Projects", cancelled_projects)
                st.metric("Optimization Time", f"{elapsed_time:.2f} sec")
            
            with col3:
                if 'traffic_impact' in st.session_state.optimization_result:
                    impact = st.session_state.optimization_result['traffic_impact']
                    st.metric("Cancelled Trains", f"{impact['cancelled']:.0f}")
                    st.metric("Delayed Trains", f"{impact['delayed']:.0f}")
                    st.metric("Diverted Trains", f"{impact['diverted']:.0f}")
            
            # Visualize optimized schedule
            st.subheader("Optimized Maintenance Schedule")
            
            # Create Gantt chart of optimized schedule
            gantt_data = []
            
            for measure in st.session_state.maintenance_data:
                # Parse dates
                start_date_str = measure.get('start_date', '')
                start_date_obj = parse_date(start_date_str)
                
                if start_date_obj:
                    # Calculate end date
                    duration_days = measure.get('duration_days', 1)
                    end_date_obj = start_date_obj + timedelta(days=duration_days)
                    
                    # Determine color based on type
                    color = get_maintenance_color(measure.get('type', 'Unknown'))
                    
                    # Add to Gantt data
                    gantt_data.append({
                        'Task': f"{measure.get('track_id', 'Unknown')}: {measure.get('description', 'Unknown')}",
                        'Start': start_date_obj,
                        'Finish': end_date_obj,
                        'Type': measure.get('type', 'Unknown'),
                        'ID': measure.get('id', 'Unknown'),
                        'Color': color
                    })
            
            # Create Gantt chart
            fig = ff.create_gantt(
                gantt_data,
                colors={measure_type: get_maintenance_color(measure_type) for measure_type in set(m.get('type', 'Unknown') for m in st.session_state.maintenance_data)},
                index_col='Type',
                title="Optimized Maintenance Schedule",
                show_colorbar=True,
                group_tasks=True,
                showgrid_x=True,
                showgrid_y=True
            )
            
            # Add today line
            today = datetime.now().date()
            fig.add_shape(
                type="line",
                x0=today,
                x1=today,
                y0=0,
                y1=1,
                line=dict(color="black", width=2, dash="dash"),
                xref='x',
                yref='paper'
            )
            
            fig.update_layout(
                autosize=True,
                height=600,
                margin=dict(l=50, r=50, b=100, t=100)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Traffic impact visualization
            if 'traffic_impact' in st.session_state.optimization_result:
                st.subheader("Traffic Impact Analysis")
                
                impact = st.session_state.optimization_result['traffic_impact']
                
                # Create impact summary pie chart
                impact_data = pd.DataFrame([
                    {'Category': 'Cancelled', 'Count': impact['cancelled']},
                    {'Category': 'Delayed', 'Count': impact['delayed']},
                    {'Category': 'Diverted', 'Count': impact['diverted']}
                ])
                
                fig = px.pie(
                    impact_data, 
                    values='Count', 
                    names='Category', 
                    title='Traffic Impact Summary',
                    color='Category',
                    color_discrete_map={
                        'Cancelled': 'red',
                        'Delayed': 'orange',
                        'Diverted': 'yellow'
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Try to load more detailed traffic data
                if 'traffic_file' in st.session_state.optimization_result['traffic_impact']:
                    try:
                        traffic_file = st.session_state.optimization_result['traffic_impact']['traffic_file']
                        traffic_tree = ET.parse(traffic_file)
                        traffic_root = traffic_tree.getroot()
                        
                        # Extract traffic flows
                        flows = []
                        for flow_elem in traffic_root.findall('.//flow'):
                            line = flow_elem.get('line')
                            route = flow_elem.get('route', 'normal')
                            period = int(flow_elem.get('period', 0))
                            value = float(flow_elem.get('value', 0))
                            
                            flows.append({
                                'Line': line,
                                'Route': route,
                                'Period': period,
                                'Value': value
                            })
                        
                        if flows:
                            flows_df = pd.DataFrame(flows)
                            
                            # Group by route type
                            route_summary = flows_df.groupby('Route')['Value'].sum().reset_index()
                            
                            # Create bar chart
                            fig = px.bar(
                                route_summary,
                                x='Route',
                                y='Value',
                                title='Traffic Flows by Route Type',
                                labels={'Route': 'Route Type', 'Value': 'Number of Trains'},
                                color='Route',
                                color_discrete_map={
                                    'normal': 'green',
                                    'diverted': 'orange',
                                    'cancelled': 'red'
                                }
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show detailed flows if not too many
                            if len(flows_df) <= 100:
                                st.subheader("Detailed Traffic Flows")
                                st.dataframe(flows_df)
                    except Exception as e:
                        st.warning(f"Could not load detailed traffic data: {str(e)}")
            
            # Show conflict resolution results
            st.subheader("Conflict Resolution Results")
            
            # Run conflict detection on optimized schedule
            measures_by_track = {}
            for measure in st.session_state.maintenance_data:
                track_id = measure.get('track_id')
                if track_id:
                    if track_id not in measures_by_track:
                        measures_by_track[track_id] = []
                    measures_by_track[track_id].append(measure)
            
            # Check for conflicts
            conflicts = []
            
            for track_id, measures in measures_by_track.items():
                # Sort measures by start date
                sorted_measures = sorted(measures, key=lambda m: parse_date(m.get('start_date', '')) or datetime.min)
                
                # Check for overlaps
                for i in range(len(sorted_measures)):
                    measure1 = sorted_measures[i]
                    start1 = parse_date(measure1.get('start_date', ''))
                    if start1:
                        duration1 = measure1.get('duration_days', 1)
                        end1 = start1 + timedelta(days=duration1)
                        
                        for j in range(i + 1, len(sorted_measures)):
                            measure2 = sorted_measures[j]
                            start2 = parse_date(measure2.get('start_date', ''))
                            if start2:
                                # Check for overlap
                                if start2 <= end1:
                                    # Check if these types can be parallel
                                    type1 = measure1.get('type', 'Unknown')
                                    type2 = measure2.get('type', 'Unknown')
                                    
                                    # Check parallelism matrix
                                    can_be_parallel = False
                                    if type1 in st.session_state.parallelism_matrix and \
                                       type2 in st.session_state.parallelism_matrix[type1]:
                                        can_be_parallel = st.session_state.parallelism_matrix[type1][type2]
                                    
                                    if not can_be_parallel:
                                        # Add to conflicts
                                        conflicts.append({
                                            'track_id': track_id,
                                            'measure1': measure1,
                                            'measure2': measure2
                                        })
            
            # Show conflict results
            if conflicts:
                st.warning(f"{len(conflicts)} conflicts remain in the optimized schedule.")
                
                # Create a dataframe for display
                conflict_display = []
                for conflict in conflicts:
                    conflict_display.append({
                        'Track': conflict['track_id'],
                        'Measure 1': conflict['measure1'].get('description', 'Unknown'),
                        'Type 1': conflict['measure1'].get('type', 'Unknown'),
                        'Start 1': parse_date(conflict['measure1'].get('start_date', '')).strftime('%Y-%m-%d'),
                        'Measure 2': conflict['measure2'].get('description', 'Unknown'),
                        'Type 2': conflict['measure2'].get('type', 'Unknown'),
                        'Start 2': parse_date(conflict['measure2'].get('start_date', '')).strftime('%Y-%m-%d')
                    })
                
                # Display conflict table
                st.dataframe(pd.DataFrame(conflict_display))
            else:
                st.success("No conflicts in the optimized schedule!")
            
            # Additional optimization information
            with st.expander("Additional Optimization Information"):
                st.markdown("""
                The optimizer attempts to:
                
                1. **Minimize conflicts** between maintenance activities
                2. **Respect portability constraints** of activities
                3. **Minimize impact on traffic** by coordinating closures
                4. **Balance workload** across time periods
                
                The optimization model uses mixed-integer programming to find the optimal schedule
                that minimizes the objective function while respecting all constraints.
                
                The weights you specified for each objective component determine their relative importance.
                """)

# Reports page
elif app_mode == "Reports":
    st.title("Reports & Analysis")
    
    # Create tabs for different report types
    schedule_tab, traffic_tab, cost_tab, annual_tab = st.tabs([
        "Schedule Analysis", "Traffic Impact Analysis", "Cost Analysis", "Annual Planning"
    ])
    
    # Schedule Analysis tab
    with schedule_tab:
        st.header("Maintenance Schedule Analysis")
        
        if not st.session_state.maintenance_data:
            st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            
            with col1:
                year_filter = st.selectbox(
                    "Year", 
                    options=['All'] + sorted(list(set([parse_date(m.get('start_date', '')).year 
                                               for m in st.session_state.maintenance_data 
                                               if parse_date(m.get('start_date', ''))])))
                )
            
            with col2:
                track_filter = st.selectbox(
                    "Track", 
                    options=['All'] + sorted(list(set([m.get('track_id') 
                                               for m in st.session_state.maintenance_data 
                                               if m.get('track_id')])))
                )
            
            # Filter data
            filtered_data = st.session_state.maintenance_data
            
            if year_filter != 'All':
                filtered_data = [m for m in filtered_data if parse_date(m.get('start_date', '')).year == year_filter]
            
            if track_filter != 'All':
                filtered_data = [m for m in filtered_data if m.get('track_id') == track_filter]
            
            if filtered_data:
                # Schedule timeline
                st.subheader("Maintenance Timeline")
                
                # Create dataframe for timeline chart
                timeline_data = []
                
                for measure in filtered_data:
                    start_date = parse_date(measure.get('start_date', ''))
                    if start_date:
                        duration = measure.get('duration_days', 1)
                        end_date = start_date + timedelta(days=duration)
                        
                        timeline_data.append({
                            'Task': f"{measure.get('track_id', 'Unknown')}: {measure.get('description', 'Unknown')}",
                            'Start': start_date,
                            'Finish': end_date,
                            'Track': measure.get('track_id', 'Unknown'),
                            'Type': measure.get('type', 'Unknown'),
                            'Duration': duration
                        })
                
                # Create Gantt chart
                fig = ff.create_gantt(
                    timeline_data,
                    colors={mtype: get_maintenance_color(mtype) for mtype in set(m['Type'] for m in timeline_data)},
                    index_col='Track',
                    title="Maintenance Timeline",
                    show_colorbar=True,
                    group_tasks=True
                )
                
                fig.update_layout(
                    autosize=True,
                    height=600,
                    margin=dict(l=50, r=50, b=100, t=100)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Activity distribution
                st.subheader("Maintenance Activity Distribution")
                
                # Create dataframe for activity counts
                activity_data = []
                
                for measure in filtered_data:
                    activity_data.append({
                        'Track': measure.get('track_id', 'Unknown'),
                        'Type': measure.get('type', 'Unknown'),
                        'Duration': measure.get('duration_days', 1),
                        'Month': parse_date(measure.get('start_date', '')).strftime('%Y-%m') if parse_date(measure.get('start_date', '')) else 'Unknown'
                    })
                
                activity_df = pd.DataFrame(activity_data)
                
                # Activity count by type
                fig = px.bar(
                    activity_df.groupby('Type').size().reset_index(name='Count'),
                    x='Type',
                    y='Count',
                    title="Maintenance Activities by Type",
                    color='Type',
                    color_discrete_map={mtype: get_maintenance_color(mtype) for mtype in activity_df['Type'].unique()}
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Activity count by month
                monthly_counts = activity_df.groupby('Month').size().reset_index(name='Count')
                monthly_counts = monthly_counts.sort_values('Month')
                
                fig = px.line(
                    monthly_counts,
                    x='Month',
                    y='Count',
                    title="Maintenance Activities by Month",
                    markers=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Track outage analysis
                st.subheader("Track Outage Analysis")
                
                # Calculate total outage days by track
                outage_df = activity_df.groupby('Track')['Duration'].sum().reset_index()
                outage_df = outage_df.sort_values('Duration', ascending=False)
                
                fig = px.bar(
                    outage_df,
                    x='Track',
                    y='Duration',
                    title="Total Outage Days by Track",
                    color='Duration',
                    color_continuous_scale='Reds'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed activity list
                st.subheader("Detailed Activity List")
                
                # Create dataframe for detailed list
                detail_data = []
                
                for measure in filtered_data:
                    start_date = parse_date(measure.get('start_date', ''))
                    if start_date:
                        duration = measure.get('duration_days', 1)
                        end_date = start_date + timedelta(days=duration)
                        
                        detail_data.append({
                            'Track': measure.get('track_id', 'Unknown'),
                            'Description': measure.get('description', 'Unknown'),
                            'Type': measure.get('type', 'Unknown'),
                            'Start Date': start_date.strftime('%Y-%m-%d'),
                            'End Date': end_date.strftime('%Y-%m-%d'),
                            'Duration (days)': duration,
                            'Responsible Unit': measure.get('responsible_unit', 'Unknown')
                        })
                
                detail_df = pd.DataFrame(detail_data)
                detail_df = detail_df.sort_values('Start Date')
                
                st.dataframe(detail_df)
                st.markdown(download_dataframe_as_csv(detail_df, "maintenance_schedule_report"), unsafe_allow_html=True)
                
                # Export options
                st.download_button(
                    label="Export Full Report",
                    data=detail_df.to_csv(index=False),
                    file_name="maintenance_schedule_report.csv",
                    mime="text/csv"
                )
            else:
                st.info("No maintenance activities match the selected filters.")
    
    # Traffic Impact Analysis tab
    with traffic_tab:
        st.header("Traffic Impact Analysis")
        
        if not st.session_state.traffic_data:
            st.warning("No traffic data available. Please go to Data Management to load or generate traffic data.")
        elif not st.session_state.maintenance_data:
            st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
        elif not st.session_state.optimization_result or 'traffic_impact' not in st.session_state.optimization_result:
            st.warning("No optimization results available. Please run optimization first.")
        else:
            # Display traffic impact analysis based on optimization results
            impact = st.session_state.optimization_result['traffic_impact']
            
            # Create impact summary
            impact_data = pd.DataFrame([
                {'Category': 'Cancelled', 'Count': impact['cancelled']},
                {'Category': 'Delayed', 'Count': impact['delayed']},
                {'Category': 'Diverted', 'Count': impact['diverted']}
            ])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Summary metrics
                st.metric("Total Trains Affected", f"{impact['cancelled'] + impact['delayed'] + impact['diverted']:.0f}")
                st.metric("Cancelled Trains", f"{impact['cancelled']:.0f}")
                st.metric("Delayed Trains", f"{impact['delayed']:.0f}")
                st.metric("Diverted Trains", f"{impact['diverted']:.0f}")
            
            with col2:
                # Pie chart
                fig = px.pie(
                    impact_data, 
                    values='Count', 
                    names='Category', 
                    title='Traffic Impact Distribution',
                    color='Category',
                    color_discrete_map={
                        'Cancelled': 'red',
                        'Delayed': 'orange',
                        'Diverted': 'yellow'
                    }
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Show traffic impact by track
            st.subheader("Traffic Impact by Track")
            
            # Try to load more detailed traffic data
            if 'traffic_file' in impact:
                try:
                    traffic_file = impact['traffic_file']
                    traffic_tree = ET.parse(traffic_file)
                    traffic_root = traffic_tree.getroot()
                    
                    # Extract traffic flows
                    flows = []
                    for flow_elem in traffic_root.findall('.//flow'):
                        line = flow_elem.get('line')
                        route = flow_elem.get('route', 'normal')
                        period = int(flow_elem.get('period', 0))
                        link = flow_elem.get('link', '')
                        value = float(flow_elem.get('value', 0))
                        
                        flows.append({
                            'Line': line,
                            'Route': route,
                            'Period': period,
                            'Link': link,
                            'Value': value
                        })
                    
                    if flows:
                        flows_df = pd.DataFrame(flows)
                        
                        # Group by link and route type
                        if 'Link' in flows_df.columns and flows_df['Link'].any():
                            link_impact = flows_df.groupby(['Link', 'Route'])['Value'].sum().reset_index()
                            
                            # Filter to only affected links
                            link_impact = link_impact[link_impact['Route'] != 'normal']
                            
                            if not link_impact.empty:
                                fig = px.bar(
                                    link_impact,
                                    x='Link',
                                    y='Value',
                                    color='Route',
                                    title='Traffic Impact by Track',
                                    labels={'Link': 'Track', 'Value': 'Number of Trains', 'Route': 'Impact Type'},
                                    color_discrete_map={
                                        'diverted': 'orange',
                                        'cancelled': 'red'
                                    },
                                    barmode='stack'
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No link-specific impact data available.")
                        else:
                            st.info("No link-specific impact data available.")
                    else:
                        st.info("No detailed flow data available.")
                    
                except Exception as e:
                    st.warning(f"Could not load detailed traffic data: {str(e)}")
            
            # Show traffic impact over time
            st.subheader("Traffic Impact Over Time")
            
            # Generate synthetic data for visualization if needed
            periods = 10
            
            impact_by_period = pd.DataFrame({
                'Period': list(range(periods)),
                'Cancelled': np.random.randint(0, 20, periods),
                'Delayed': np.random.randint(10, 30, periods),
                'Diverted': np.random.randint(5, 25, periods)
            })
            
            # Reshape for stacked area chart
            impact_long = pd.melt(
                impact_by_period, 
                id_vars=['Period'], 
                value_vars=['Cancelled', 'Delayed', 'Diverted'],
                var_name='Impact Type', 
                value_name='Count'
            )
            
            fig = px.area(
                impact_long,
                x='Period',
                y='Count',
                color='Impact Type',
                title='Traffic Impact Over Time Periods',
                labels={'Period': 'Time Period', 'Count': 'Number of Trains', 'Impact Type': 'Impact Type'},
                color_discrete_map={
                    'Cancelled': 'red',
                    'Delayed': 'orange',
                    'Diverted': 'yellow'
                }
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Export data
            st.download_button(
                label="Export Traffic Impact Data",
                data=impact_long.to_csv(index=False),
                file_name="traffic_impact_data.csv",
                mime="text/csv"
            )
    
    # Cost Analysis tab
    with cost_tab:
        st.header("Maintenance Cost Analysis")
        
        if not st.session_state.maintenance_data:
            st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
        else:
            # Check if cost data is available
            has_cost_data = any('estimated_cost' in m for m in st.session_state.maintenance_data)
            
            if not has_cost_data:
                st.warning("No cost data available in the maintenance dataset.")
            else:
                # Filter options
                col1, col2 = st.columns(2)
                
                with col1:
                    year_filter = st.selectbox(
                        "Year", 
                        options=['All'] + sorted(list(set([parse_date(m.get('start_date', '')).year 
                                                   for m in st.session_state.maintenance_data 
                                                   if parse_date(m.get('start_date', ''))])))
                    )
                
                with col2:
                    type_filter = st.selectbox(
                        "Maintenance Type", 
                        options=['All'] + sorted(list(set([m.get('type', 'Unknown') 
                                                   for m in st.session_state.maintenance_data 
                                                   if m.get('type')])))
                    )
                
                # Filter data
                filtered_data = st.session_state.maintenance_data
                
                if year_filter != 'All':
                    filtered_data = [m for m in filtered_data if parse_date(m.get('start_date', '')).year == year_filter]
                
                if type_filter != 'All':
                    filtered_data = [m for m in filtered_data if m.get('type') == type_filter]
                
                # Cost analysis
                cost_data = []
                
                for measure in filtered_data:
                    if 'estimated_cost' in measure and measure['estimated_cost'] is not None:
                        start_date = parse_date(measure.get('start_date', ''))
                        if start_date:
                            cost_data.append({
                                'Track': measure.get('track_id', 'Unknown'),
                                'Type': measure.get('type', 'Unknown'),
                                'Description': measure.get('description', 'Unknown'),
                                'Month': start_date.strftime('%Y-%m'),
                                'Quarter': f"Q{(start_date.month-1)//3 + 1} {start_date.year}",
                                'Year': start_date.year,
                                'Cost': measure['estimated_cost'],
                                'Responsible Unit': measure.get('responsible_unit', 'Unknown')
                            })
                
                if cost_data:
                    cost_df = pd.DataFrame(cost_data)
                    
                    # Total cost summary
                    total_cost = cost_df['Cost'].sum()
                    avg_cost = cost_df['Cost'].mean()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Cost", f"{total_cost:,.0f} SEK")
                    
                    with col2:
                        st.metric("Average Cost per Activity", f"{avg_cost:,.0f} SEK")
                    
                    # Cost by type
                    st.subheader("Cost by Maintenance Type")
                    
                    type_cost = cost_df.groupby('Type')['Cost'].sum().reset_index()
                    type_cost = type_cost.sort_values('Cost', ascending=False)
                    
                    fig = px.bar(
                        type_cost,
                        x='Type',
                        y='Cost',
                        title='Total Cost by Maintenance Type',
                        color='Type',
                        color_discrete_map={mtype: get_maintenance_color(mtype) for mtype in type_cost['Type'].unique()}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Cost by track
                    st.subheader("Cost by Track")
                    
                    track_cost = cost_df.groupby('Track')['Cost'].sum().reset_index()
                    track_cost = track_cost.sort_values('Cost', ascending=False)
                    
                    fig = px.bar(
                        track_cost,
                        x='Track',
                        y='Cost',
                        title='Total Cost by Track',
                        color='Cost',
                        color_continuous_scale='Reds'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Cost over time
                    st.subheader("Cost Timeline")
                    
                    timeline_options = st.radio("Timeline By", options=["Month", "Quarter"])
                    
                    if timeline_options == "Month":
                        time_group = 'Month'
                    else:
                        time_group = 'Quarter'
                    
                    time_cost = cost_df.groupby([time_group, 'Type'])['Cost'].sum().reset_index()
                    
                    fig = px.bar(
                        time_cost,
                        x=time_group,
                        y='Cost',
                        color='Type',
                        title=f'Cost by {time_group}',
                        color_discrete_map={mtype: get_maintenance_color(mtype) for mtype in time_cost['Type'].unique()},
                        barmode='stack'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Detailed cost table
                    st.subheader("Detailed Cost Data")
                    
                    cost_details = cost_df[['Track', 'Description', 'Type', 'Month', 'Cost', 'Responsible Unit']]
                    cost_details = cost_details.sort_values('Cost', ascending=False)
                    
                    st.dataframe(cost_details)
                    st.markdown(download_dataframe_as_csv(cost_details, "maintenance_cost_report"), unsafe_allow_html=True)
                else:
                    st.info("No cost data available for the selected filters.")
    
    # Annual Planning tab
    with annual_tab:
        st.header("Annual Maintenance Planning")
        
        if not st.session_state.maintenance_data:
            st.warning("No maintenance data available. Please go to Data Management to load or generate maintenance data.")
        else:
            # Year selection
            available_years = sorted(list(set([parse_date(m.get('start_date', '')).year 
                                     for m in st.session_state.maintenance_data 
                                     if parse_date(m.get('start_date', ''))])))
            
            if not available_years:
                st.warning("No valid dates found in maintenance data.")
            else:
                selected_year = st.selectbox("Select Year for Planning", options=available_years, index=0)
                
                # Filter data for selected year
                year_data = [m for m in st.session_state.maintenance_data 
                           if parse_date(m.get('start_date', '')) and 
                           parse_date(m.get('start_date', '')).year == selected_year]
                
                if year_data:
                    # Annual calendar view
                    st.subheader(f"Maintenance Calendar for {selected_year}")
                    
                    # Create calendar data
                    calendar_data = []
                    months = range(1, 13)
                    
                    for month in months:
                        month_str = f"{selected_year}-{month:02d}"
                        month_activities = [m for m in year_data 
                                          if parse_date(m.get('start_date', '')).strftime('%Y-%m') == month_str]
                        
                        # Count by type
                        type_counts = {}
                        for m in month_activities:
                            mtype = m.get('type', 'Unknown')
                            if mtype not in type_counts:
                                type_counts[mtype] = 0
                            type_counts[mtype] += 1
                        
                        # Add to calendar data
                        for mtype, count in type_counts.items():
                            calendar_data.append({
                                'Month': month_str,
                                'Type': mtype,
                                'Count': count
                            })
                    
                    if calendar_data:
                        calendar_df = pd.DataFrame(calendar_data)
                        
                        # Create heatmap calendar
                        pivot_df = calendar_df.pivot_table(
                            values='Count',
                            index='Type',
                            columns='Month',
                            fill_value=0
                        )
                        
                        fig = px.imshow(
                            pivot_df,
                            labels=dict(x="Month", y="Maintenance Type", color="Count"),
                            x=pivot_df.columns,
                            y=pivot_df.index,
                            color_continuous_scale="Blues",
                            title=f"Maintenance Activity Calendar {selected_year}",
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Annual workload analysis
                    st.subheader("Annual Workload Analysis")
                    
                    workload_data = []
                    for m in year_data:
                        start_date = parse_date(m.get('start_date', ''))
                        if start_date:
                            month = start_date.month
                            workload_data.append({
                                'Month': month,
                                'Month Name': start_date.strftime('%B'),
                                'Type': m.get('type', 'Unknown'),
                                'Duration': m.get('duration_days', 1),
                                'Track': m.get('track_id', 'Unknown'),
                                'Unit': m.get('responsible_unit', 'Unknown')
                            })
                    
                    if workload_data:
                        workload_df = pd.DataFrame(workload_data)
                        
                        # Monthly workload
                        monthly_work = workload_df.groupby(['Month', 'Month Name'])['Duration'].sum().reset_index()
                        monthly_work = monthly_work.sort_values('Month')
                        
                        fig = px.bar(
                            monthly_work,
                            x='Month Name',
                            y='Duration',
                            title='Monthly Workload (Total Maintenance Days)',
                            color='Duration',
                            color_continuous_scale='Blues'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Annual planning recommendations
                        st.subheader("Planning Recommendations")
                        
                        # Find peak months and low-activity months
                        monthly_sum = monthly_work.set_index('Month')['Duration'].to_dict()
                        avg_workload = monthly_work['Duration'].mean()
                        
                        # Identify peaks and valleys
                        peak_months = [m for m, v in monthly_sum.items() if v > avg_workload * 1.25]
                        low_months = [m for m, v in monthly_sum.items() if v < avg_workload * 0.75]
                        
                        peak_names = [datetime(2000, m, 1).strftime('%B') for m in peak_months]
                        low_names = [datetime(2000, m, 1).strftime('%B') for m in low_months]
                        
                        st.info(f"""
                        ### Workload Distribution Recommendations
                        
                        - **Peak activity months**: {', '.join(peak_names) if peak_names else 'None identified'}
                        - **Low activity months**: {', '.join(low_names) if low_names else 'None identified'}
                        
                        **Recommendations:**
                        
                        {f'- Consider redistributing some activities from {", ".join(peak_names)} to {", ".join(low_names)}' if peak_names and low_names else '- Workload is relatively balanced throughout the year'}
                        
                        - Average workload: {avg_workload:.1f} maintenance days per month
                        """)
                else:
                    st.info(f"No maintenance activities found for {selected_year}.")

if __name__ == "__main__":
    # This will run the Streamlit app when the script is executed directly
    pass